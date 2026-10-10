from django.conf import settings
from django.utils import timezone
from pydantic import AwareDatetime, BaseModel, ConfigDict, SecretStr

from apps.competencias.emissao_certidao import autor_do_ato
from apps.documentos.acervo import guardar_documento
from apps.documentos.models import DocumentoEmitido
from apps.lotes_mais_proximos.contexto import camada_lotes
from apps.user_admin.models import Perfil
from services.domain.certidao_lancamento import (
    CertidaoLancamento,
    CertidaoLancamentoInput,
    ConjuntoDesenhado,
    LoteUnico,
    PedidoCertidao,
)
from services.domain.documento_oficial import (
    SeloConfig,
    build_marcacao_config,
    build_tema_config,
    montar_tema,
)
from services.domain.documento_selado import (
    AlvoDoAto,
    EnvelopeAto,
    gerar_codigo,
    montar_envelope,
)
from services.domain.geometry import PolygonGeometry, reprojetar
from services.domain.lote_geocod import (
    LoteFeature,
    LotePorIdentificador,
    LotePorIdentificadorInput,
)
from services.domain.lotes_mais_proximos import (
    BuscarLotesDoDesenho,
    ConjuntoDeLotes,
    ReleituraDoConjuntoInput,
    RelerConjunto,
)
from services.domain.planta_localizacao import (
    CamadaPlanta,
    EstiloGeometria,
    GerarPlantaLocalizacao,
    PlantaConfig,
    PlantaLocalizacao,
    PlantaLocalizacaoInput,
)
from services.integrations.wfs import build_fetcher
from services.integrations.wms import WmsError, build_wms_fetcher
from services.utils.assinatura import SelarInput, selar_documento
from services.utils.erros_formulario import RecusaDeFormulario
from .acoes_declaradas import ACAO_EMITIR_CERTIDAO_LANCAMENTO

WFS_LAYER_LOTE_CIDADAO: str = settings.WFS_LAYER_LOTE_CIDADAO
WMS_LAYER_ORTOFOTO: str = settings.WMS_LAYER_ORTOFOTO
MAP_INTERPOLATION_CRS: int = settings.MAP_INTERPOLATION_CRS
MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
LOTES_DESENHO_AREA_MAXIMA_M2: float = settings.LOTES_DESENHO_AREA_MAXIMA_M2
ASSINATURA_SEGREDO: SecretStr = settings.ASSINATURA_SEGREDO
ASSINATURA_ID_CHAVE: str = settings.ASSINATURA_ID_CHAVE

MOTIVO_SEM_ORTOFOTO = (
    "Não foi possível obter a imagem de localização do imóvel agora. "
    "Tente novamente em instantes."
)


class LoteLido(BaseModel):
    """O lote como o GeoSampa respondeu na hora: geometria no CRS métrico (a planta a usa) e o instante."""

    feature: LoteFeature
    consultado_em: AwareDatetime

    @property
    def pode_certificar(self) -> bool:
        attrs = self.feature.attributes
        return bool(attrs.possui_lancamento and not attrs.is_condominio)


def ler_lote(id_poligono: str) -> LoteLido | None:
    if not id_poligono:
        return None
    buscar_lote = LotePorIdentificador(build_fetcher(settings))
    feature = buscar_lote(
        LotePorIdentificadorInput(
            id_poligono=id_poligono,
            layer_name=WFS_LAYER_LOTE_CIDADAO,
            output_crs=MAP_INTERPOLATION_CRS,
        )
    )
    if feature is None:
        return None
    return LoteLido(feature=feature, consultado_em=timezone.localtime())


class ConjuntoLido(BaseModel):
    """O conjunto como o GeoSampa respondeu na emissão, e o instante: é ele que o rodapé declara."""

    conjunto: ConjuntoDeLotes
    consultado_em: AwareDatetime


class ConjuntoAlteradoError(Exception):
    """O conjunto relido na emissão não é a lista que o modal mostrou."""

    def __init__(self, entraram: frozenset[str], sairam: frozenset[str]) -> None:
        self.entraram = entraram
        self.sairam = sairam
        super().__init__("O conjunto mudou depois que o modal abriu.")


def reler_conjunto(conjunto: ConjuntoDeLotes) -> ConjuntoLido:
    reler = RelerConjunto(BuscarLotesDoDesenho(build_fetcher(settings)))
    relido = reler(
        ReleituraDoConjuntoInput(
            conjunto=conjunto,
            crs_mapa=MAP_OUTPUT_CRS,
            camada=camada_lotes(),
            area_maxima_m2=LOTES_DESENHO_AREA_MAXIMA_M2,
        )
    )
    return ConjuntoLido(conjunto=relido, consultado_em=timezone.localtime())


def conferir_confirmados(lido: ConjuntoLido, confirmados: frozenset[str]) -> None:
    # O modal mostrou uma lista; a certidão atesta exatamente essa lista ou não sai.
    relidos = frozenset(lote.attributes.id_poligono for lote in lido.conjunto.lotes)
    if relidos != confirmados:
        raise ConjuntoAlteradoError(entraram=relidos - confirmados, sairam=confirmados - relidos)


class GeometriasMetricas(BaseModel):
    """O desenho e os lotes no mesmo CRS métrico: servem à planta e à sugestão do despacho."""

    model_config = ConfigDict(frozen=True)

    desenho: PolygonGeometry
    lotes: tuple[PolygonGeometry, ...]


def geometrias_metricas(
    conjunto: ConjuntoDeLotes,
    crs_mapa: int,
    crs_metrico: int,
) -> GeometriasMetricas:
    desenho = conjunto.apurado.desenho.geometria
    # A consulta que monta o conjunto só aceita polígono; o tipo do `Desenho` é que é mais largo.
    if not isinstance(desenho, PolygonGeometry):
        raise TypeError("O conjunto de lotes só existe sobre um desenho de polígono.")
    # O desenho não carrega CRS: está no do mapa, que a orquestração informa.
    return GeometriasMetricas(
        desenho=reprojetar(desenho, crs_mapa, crs_metrico),
        lotes=tuple(reprojetar(lote.geometry, lote.crs, crs_metrico) for lote in conjunto.lotes),
    )


def camadas_da_planta_do_conjunto(geometrias: GeometriasMetricas) -> tuple[CamadaPlanta, ...]:
    return (
        CamadaPlanta(geometrias=geometrias.lotes, estilo=EstiloGeometria.CONTEXTO),
        CamadaPlanta(geometrias=(geometrias.desenho,), estilo=EstiloGeometria.DESTAQUE),
    )


class DesfechoEmissao(BaseModel):
    """Ou o documento, ou a recusa — o mesmo contrato de `DesfechoUnidade` e `DesfechoCargo`."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    documento: DocumentoEmitido | None = None
    recusa: RecusaDeFormulario = RecusaDeFormulario()


def planta_config() -> PlantaConfig:
    return PlantaConfig(
        camada_ortofoto=WMS_LAYER_ORTOFOTO,
        crs=MAP_INTERPOLATION_CRS,
    )


def _gerar_planta(camadas: tuple[CamadaPlanta, ...]) -> PlantaLocalizacao:
    gerar_planta = GerarPlantaLocalizacao(build_wms_fetcher(settings))
    return gerar_planta(PlantaLocalizacaoInput(camadas=camadas, config=planta_config()))


def camadas_da_planta_do_lote(lote: LoteLido) -> tuple[CamadaPlanta, ...]:
    return (
        CamadaPlanta(
            geometrias=(lote.feature.geometry,),
            estilo=EstiloGeometria.DESTAQUE,
        ),
    )


def _tipo_certidao() -> CertidaoLancamento:
    tema = montar_tema(build_tema_config(settings))
    config = build_marcacao_config(settings)
    selo_config = SeloConfig()
    return CertidaoLancamento(tema=tema, config=config, selo_config=selo_config)


def _emitir(
    envelope: EnvelopeAto,
    pedido: PedidoCertidao,
    objeto: LoteUnico | ConjuntoDesenhado,
    camadas: tuple[CamadaPlanta, ...],
    consultado_em: AwareDatetime,
    base_url: str,
) -> DesfechoEmissao:
    planta = None
    # Sem o mapa no pedido a ortofoto nem é consultada, e o WMS fora do ar não recusa o ato.
    if pedido.incluir_planta:
        try:
            planta = _gerar_planta(camadas)
        except WmsError:
            # A view não conhece WMS; ela lê o desfecho, como nas demais telas de formulário.
            return DesfechoEmissao(recusa=RecusaDeFormulario(gerais=(MOTIVO_SEM_ORTOFOTO,)))
    renderizar_certidao = _tipo_certidao()
    renderizado = renderizar_certidao(
        CertidaoLancamentoInput(
            envelope=envelope,
            pedido=pedido,
            objeto=objeto,
            planta=planta,
            consultado_em=consultado_em,
            base_url=base_url,
        )
    )
    selado = selar_documento(
        SelarInput(
            pdf=renderizado.pdf,
            dados=montar_envelope(envelope),
            campos_publicos=envelope.campos_publicos,
            segredo=ASSINATURA_SEGREDO,
            id_chave=ASSINATURA_ID_CHAVE,
        )
    )
    return DesfechoEmissao(documento=guardar_documento(selado, envelope, execucao=None))


def emitir_certidao_lancamento(
    autor: Perfil,
    pedido: PedidoCertidao,
    lote: LoteLido,
    base_url: str,
) -> DesfechoEmissao:
    imovel = lote.feature.attributes
    envelope = EnvelopeAto(
        codigo=gerar_codigo(),
        acao=ACAO_EMITIR_CERTIDAO_LANCAMENTO.acao.slug,
        operacao="emitir",
        autor=autor_do_ato(autor),
        alvo=AlvoDoAto(tipo="lote", identificador=imovel.sql or ""),
        emitido_em=timezone.localtime(),
        # O interessado e o CPF/CNPJ são dados de pessoa: ficam só no PDF, fora da ficha pública.
        campos_publicos=("contribuinte", "processo", "despacho"),
        extras={
            "contribuinte": imovel.sql,
            "processo": pedido.processo,
            "despacho": pedido.tipo_despacho.rotulo,
        },
    )
    return _emitir(
        envelope=envelope,
        pedido=pedido,
        objeto=LoteUnico(imovel=imovel),
        camadas=camadas_da_planta_do_lote(lote),
        consultado_em=lote.consultado_em,
        base_url=base_url,
    )


def emitir_certidao_do_conjunto(
    autor: Perfil,
    pedido: PedidoCertidao,
    lido: ConjuntoLido,
    base_url: str,
) -> DesfechoEmissao:
    conjunto = lido.conjunto
    imoveis = tuple(lote.attributes for lote in conjunto.lotes)
    envelope = EnvelopeAto(
        codigo=gerar_codigo(),
        acao=ACAO_EMITIR_CERTIDAO_LANCAMENTO.acao.slug,
        operacao="emitir_conjunto",
        autor=autor_do_ato(autor),
        alvo=AlvoDoAto(tipo="conjunto_lotes", identificador=f"{len(imoveis)} lotes"),
        emitido_em=timezone.localtime(),
        campos_publicos=("contribuintes", "processo", "despacho"),
        extras={
            "contribuintes": ", ".join(imovel.sql or "" for imovel in imoveis),
            "processo": pedido.processo,
            "despacho": pedido.tipo_despacho.rotulo,
        },
    )
    geometrias = geometrias_metricas(conjunto, MAP_OUTPUT_CRS, MAP_INTERPOLATION_CRS)
    return _emitir(
        envelope=envelope,
        pedido=pedido,
        objeto=ConjuntoDesenhado(lotes=imoveis, area_desenho_m2=conjunto.apurado.area_m2),
        camadas=camadas_da_planta_do_conjunto(geometrias),
        consultado_em=lido.consultado_em,
        base_url=base_url,
    )
