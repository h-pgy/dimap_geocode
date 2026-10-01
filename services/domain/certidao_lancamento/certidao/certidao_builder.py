from pydantic import BaseModel, ConfigDict
from services.domain.documento_oficial import (
    Bloco,
    ConteudoDocumento,
    ImagemRaster,
    Paragrafo,
    QuadroSeloConfig,
    SeloDeFecho,
    Subtitulo,
    Titulo,
)
from services.domain.documento_selado import SeloImpresso
from services.domain.documento_selado.datas import por_extenso
from services.domain.lote_geocod.models import LoteAttributes
from services.domain.planta_localizacao.models import PlantaLocalizacao

from ..models import (
    CertidaoLancamentoInput,
    PedidoCertidao,
    SentidoDespacho,
    TipoDespacho,
)
from .constants import (
    ABERTURA_DO_DESPACHO,
    BASE_DESPACHO,
    CORPO_DO_DESPACHO,
    LARGURA_PLANTA_MM,
    RESSALVA_PADRAO,
    TITULO,
    VALIDADE,
)


def corpo_do_despacho(tipo: TipoDespacho, sql: str | None) -> str:
    # O PDF e a prévia do modal leem o mesmo texto.
    return CORPO_DO_DESPACHO[tipo].format(sql=sql)


def abertura_do_despacho(sentido: SentidoDespacho) -> str:
    return f"{ABERTURA_DO_DESPACHO[sentido]} {BASE_DESPACHO}"


def ressalva_padrao() -> str:
    return RESSALVA_PADRAO


class MontarCertidaoLancamentoInput(BaseModel):
    model_config = ConfigDict(frozen=True)

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
            Subtitulo(texto="Dados relacionados à declaração"),
            *self._dados_relacionados(certidao),
            Subtitulo(texto="Despacho"),
            *self._despacho(certidao.pedido, certidao.imovel),
            *self._localizacao(certidao.planta),
            Paragrafo(texto=f"São Paulo, {por_extenso(certidao.envelope.emitido_em)}."),
            SeloDeFecho(selo=pedido.selo, quadro=pedido.quadro),
        )

    def _dados_relacionados(
        self,
        certidao: CertidaoLancamentoInput,
    ) -> tuple[Paragrafo, ...]:
        pedido = certidao.pedido
        documento = f" (CPF/CNPJ: {pedido.cpf_cnpj})" if pedido.cpf_cnpj else ""
        return (
            Paragrafo(
                texto=f"Identificação do imóvel: {self._identificacao(certidao.imovel)}"
            ),
            Paragrafo(texto=f"Nome do interessado: {pedido.interessado}{documento}"),
            Paragrafo(texto=f"Processo SEI nº: {pedido.processo}"),
            Paragrafo(
                texto=f"Data da declaração: {certidao.envelope.emitido_em:%d/%m/%Y}"
            ),
        )

    def _despacho(
        self,
        pedido: PedidoCertidao,
        imovel: LoteAttributes,
    ) -> tuple[Paragrafo, ...]:
        tipo = pedido.tipo_despacho
        corpo = corpo_do_despacho(tipo, imovel.sql)
        paragrafos = [Paragrafo(texto=f"{abertura_do_despacho(tipo.sentido)} {corpo}")]
        if pedido.incluir_ressalva:
            paragrafos.append(Paragrafo(texto=RESSALVA_PADRAO))
        if pedido.observacoes:
            paragrafos.append(Paragrafo(texto=pedido.observacoes))
        paragrafos.append(Paragrafo(texto=VALIDADE))
        return tuple(paragrafos)

    def _localizacao(self, planta: PlantaLocalizacao | None) -> tuple[Bloco, ...]:
        # Subtítulo solto sobre nada seria pior que a ausência da seção.
        if planta is None:
            return ()
        return (
            Subtitulo(texto="Localização do Imóvel"),
            ImagemRaster(conteudo=planta.png, largura_mm=LARGURA_PLANTA_MM),
        )

    def _identificacao(self, imovel: LoteAttributes) -> str:
        codlog_txt = (
            f" (codlog: {imovel.codlog[:5]}-{imovel.codlog[5:]})"
            if imovel.codlog
            else ""
        )
        texto = f"{imovel.nome_logradouro}{codlog_txt}, número {imovel.numero_porta}"
        return (
            f"{texto}, complemento {imovel.complemento}."
            if imovel.complemento
            else f"{texto}."
        )
