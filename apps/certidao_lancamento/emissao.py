from django.conf import settings
from django.utils import timezone
from pydantic import AwareDatetime, BaseModel, ConfigDict, SecretStr

from apps.competencias.emissao_certidao import autor_do_ato
from apps.documentos.acervo import guardar_documento
from apps.documentos.models import DocumentoEmitido
from apps.user_admin.models import Perfil
from services.domain.certidao_lancamento.certidao import CertidaoLancamento
from services.domain.certidao_lancamento.models import (
    CertidaoLancamentoInput,
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
from services.domain.lote_geocod import (
    LoteFeature,
    LotePorIdentificador,
    LotePorIdentificadorInput,
)
from services.domain.planta_localizacao import (
    CamadaPlanta,
    EstiloGeometria,
    GerarPlantaLocalizacao,
    PlantaConfig,
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
    feature = LotePorIdentificador(build_fetcher(settings))(
        LotePorIdentificadorInput(
            id_poligono=id_poligono,
            layer_name=WFS_LAYER_LOTE_CIDADAO,
            output_crs=MAP_INTERPOLATION_CRS,
        )
    )
    if feature is None:
        return None
    return LoteLido(feature=feature, consultado_em=timezone.localtime())


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


def _tipo_certidao() -> CertidaoLancamento:
    tema = montar_tema(build_tema_config(settings))
    config = build_marcacao_config(settings)
    selo_config = SeloConfig()
    return CertidaoLancamento(tema=tema, config=config, selo_config=selo_config)


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
        campos_publicos=("contribuinte", "processo"),
        extras={"contribuinte": imovel.sql, "processo": pedido.processo},
    )
    try:
        planta = GerarPlantaLocalizacao(build_wms_fetcher(settings))(
            PlantaLocalizacaoInput(
                camadas=(
                    CamadaPlanta(
                        geometrias=(lote.feature.geometry,),
                        estilo=EstiloGeometria.DESTAQUE,
                    ),
                ),
                config=planta_config(),
            )
        )
    except WmsError:
        # A view não conhece WMS; ela lê o desfecho, como nas demais telas de formulário.
        return DesfechoEmissao(recusa=RecusaDeFormulario(gerais=(MOTIVO_SEM_ORTOFOTO,)))
    renderizado = _tipo_certidao()(
        CertidaoLancamentoInput(
            envelope=envelope,
            pedido=pedido,
            imovel=imovel,
            planta=planta,
            consultado_em=lote.consultado_em,
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
