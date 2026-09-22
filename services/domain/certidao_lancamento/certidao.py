from pydantic import BaseModel, ConfigDict
from services.domain.documento_oficial import (
    Bloco,
    ConteudoDocumento,
    DocumentoRenderizado,
    ImagemRaster,
    MarcacaoConfig,
    Paragrafo,
    QuadroSeloConfig,
    RenderizarDocumentoInput,
    RenderizarDocumentoOficial,
    SeloConfig,
    SeloDeFecho,
    Subtitulo,
    Tema,
    Titulo,
)
from services.domain.documento_oficial.marcacoes_concretas.fazenda_dimap_selado_com_nota import (
    marcacao_fazenda_dimap_selado_com_nota,
)
from services.domain.documento_selado import (
    SeloImpresso,
    SeloImpressoInput,
    montar_selo_impresso,
)
from services.domain.documento_selado.datas import por_extenso
from services.domain.lote_geocod.models import LoteAttributes

from .models import CertidaoLancamentoInput, PedidoCertidao

TITULO = "Certidão de Existência de Lançamento"
DESPACHO = "Solicitação deferida."
FUNDAMENTO = (
    "Com base nas informações consultadas de forma automatizada junto à base de dados oficial do "
    "Município de São Paulo, declara-se que o imóvel acima identificado possui lançamento do Imposto "
    "Predial e Territorial Urbano (IPTU) pelo contribuinte número {sql}."
)
LARGURA_PLANTA_MM = 150.0


class MontarCertidaoLancamentoInput(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    certidao: CertidaoLancamentoInput
    selo: SeloImpresso
    quadro: QuadroSeloConfig


class MontarCertidaoLancamento:
    def __call__(self, pedido: MontarCertidaoLancamentoInput) -> ConteudoDocumento:
        return self.pipeline(pedido)

    def pipeline(self, pedido: MontarCertidaoLancamentoInput) -> ConteudoDocumento:
        return ConteudoDocumento(
            titulo=TITULO,
            nome_arquivo=f"certidao_lancamento_{pedido.certidao.envelope.codigo}.pdf",
            blocos=self._blocos(pedido),
        )

    def _blocos(self, pedido: MontarCertidaoLancamentoInput) -> tuple[Bloco, ...]:
        certidao = pedido.certidao
        return (
            Titulo(texto=TITULO),
            Subtitulo(texto="Requerimento"),
            Paragrafo(texto=self._requerimento(certidao.pedido)),
            Subtitulo(texto="Identificação do Imóvel"),
            Paragrafo(texto=self._identificacao(certidao.imovel)),
            Subtitulo(texto="Despacho"),
            Paragrafo(texto=DESPACHO),
            Paragrafo(texto=FUNDAMENTO.format(sql=certidao.imovel.sql)),
            Subtitulo(texto="Localização do Imóvel"),
            ImagemRaster(conteudo=certidao.planta.png, largura_mm=LARGURA_PLANTA_MM),
            Paragrafo(texto=f"São Paulo, {por_extenso(certidao.envelope.emitido_em)}."),
            SeloDeFecho(selo=pedido.selo, quadro=pedido.quadro),
        )

    def _identificacao(self, imovel: LoteAttributes) -> str:
        codlog_txt = (
            f" (codlog: {imovel.codlog[:5]}-{imovel.codlog[5:]})" if imovel.codlog else ""
        )
        texto = (
            f"O imóvel objeto desta certidão está localizado no endereço {imovel.nome_logradouro}{codlog_txt}, "
            f"número {imovel.numero_porta}"
        )
        return f"{texto}, complemento {imovel.complemento}." if imovel.complemento else f"{texto}."

    def _requerimento(self, pedido: PedidoCertidao) -> str:
        return f"Interessado: {pedido.interessado}. Processo SEI nº {pedido.processo}."


class CertidaoLancamento:
    """O tipo: conteúdo + papel selado com nota de rodapé + tema. Quem emite só preenche o DTO."""

    def __init__(self, tema: Tema, config: MarcacaoConfig, selo_config: SeloConfig) -> None:
        self._montar = MontarCertidaoLancamento()
        self._tema = tema
        self._config = config
        self._selo_config = selo_config
        self._renderizar = RenderizarDocumentoOficial(tema)

    def pipeline(self, pedido: CertidaoLancamentoInput) -> DocumentoRenderizado:
        selo = montar_selo_impresso(
            SeloImpressoInput(
                envelope=pedido.envelope,
                base_url=pedido.base_url,
            )
        )
        conteudo = self._montar(
            MontarCertidaoLancamentoInput(
                certidao=pedido,
                selo=selo,
                quadro=self._selo_config.fecho,
            )
        )
        marcacao = marcacao_fazenda_dimap_selado_com_nota(
            self._config,
            self._tema,
            selo,
            self._selo_config.compacto,
            nota=self._nota(pedido),
        )
        return self._renderizar(RenderizarDocumentoInput(conteudo=conteudo, marcacao=marcacao))

    def _nota(self, pedido: CertidaoLancamentoInput) -> tuple[str, ...]:
        momento = pedido.consultado_em
        return (
            "Certidão emitida de forma automática",
            f"Dados cadastrais consultados em {momento:%d/%m/%Y} - {momento:%H:%M} no GeoSampa",
        )
