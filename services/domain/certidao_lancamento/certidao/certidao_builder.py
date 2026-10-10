from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict
from services.domain.documento_oficial import (
    Bloco,
    ConteudoDocumento,
    ImagemRaster,
    Paragrafo,
    QuadroSeloConfig,
    SeloDeFecho,
    Subtitulo,
    Tabela,
    Titulo,
)
from services.domain.documento_selado import SeloImpresso
from services.domain.documento_selado.datas import por_extenso
from services.domain.lote_geocod.models import LoteAttributes
from services.domain.planta_localizacao.models import PlantaLocalizacao
from services.utils.pdf import ColunaFixa, ColunaFluida

from ..models import (
    CertidaoLancamentoInput,
    ConjuntoDesenhado,
    LoteUnico,
    PedidoCertidao,
    SentidoDespacho,
    TipoDespacho,
)
from .constants import (
    ABERTURA_DO_DESPACHO,
    BASE_DESPACHO,
    CORPO_DO_DESPACHO,
    CORPO_DO_DESPACHO_CONJUNTO,
    LARGURA_COLUNA_COMPLEMENTO_MM,
    LARGURA_COLUNA_CONTRIBUINTE_MM,
    LARGURA_PLANTA_MM,
    RESSALVA_PADRAO,
    SEM_COMPLEMENTO,
    TITULO,
    VALIDADE,
)


def corpo_do_despacho(tipo: TipoDespacho, sql: str | None) -> str:
    # O PDF e a prévia do modal leem o mesmo texto.
    return CORPO_DO_DESPACHO[tipo].format(sql=sql)


def rol_de_contribuintes(sqls: Sequence[str]) -> str:
    # "A", "A e B", "A, B e C": a enumeração do português, não a vírgula solta.
    if len(sqls) == 1:
        return sqls[0]
    return f"{', '.join(sqls[:-1])} e {sqls[-1]}"


def corpo_do_despacho_conjunto(tipo: TipoDespacho, sqls: Sequence[str]) -> str:
    return CORPO_DO_DESPACHO_CONJUNTO[tipo].format(rol=rol_de_contribuintes(sqls))


def formatar_area(area_m2: float) -> str:
    # Milhar com ponto e sem decimais, como a gaveta mostra a área do desenho.
    return f"{area_m2:,.0f}".replace(",", ".")


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
            *self._identificacao(certidao.objeto),
            Subtitulo(texto="Despacho"),
            *self._despacho(certidao.pedido, certidao.objeto),
            *self._localizacao(certidao.planta, certidao.objeto),
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
            *self._imovel_identificado(certidao.objeto),
            Paragrafo(texto=f"Nome do interessado: {pedido.interessado}{documento}"),
            Paragrafo(texto=f"Processo SEI nº: {pedido.processo}"),
            Paragrafo(
                texto=f"Data da declaração: {certidao.envelope.emitido_em:%d/%m/%Y}"
            ),
        )

    def _imovel_identificado(
        self,
        objeto: LoteUnico | ConjuntoDesenhado,
    ) -> tuple[Paragrafo, ...]:
        match objeto:
            case LoteUnico(imovel=imovel):
                return (
                    Paragrafo(texto=f"Identificação do imóvel: {self._endereco(imovel)}"),
                )
            case ConjuntoDesenhado():
                # O conjunto não cabe numa linha: a identificação dele é a tabela.
                return ()

    def _identificacao(self, objeto: LoteUnico | ConjuntoDesenhado) -> tuple[Bloco, ...]:
        match objeto:
            case LoteUnico():
                return ()
            case ConjuntoDesenhado(lotes=lotes, area_desenho_m2=area):
                return (
                    # Sem citar a planta: sem o mapa no pedido ela não existe.
                    Paragrafo(
                        texto=(
                            "Os imóveis objeto desta declaração compõem a área desenhada, com "
                            f"{formatar_area(area)} m², e são os relacionados abaixo."
                        )
                    ),
                    Tabela(
                        colunas=(
                            ColunaFixa(largura_mm=LARGURA_COLUNA_CONTRIBUINTE_MM),
                            ColunaFluida(),
                            ColunaFixa(largura_mm=LARGURA_COLUNA_COMPLEMENTO_MM),
                        ),
                        cabecalho=("Contribuinte", "Endereço", "Complemento"),
                        linhas=tuple(
                            (lote.sql or "", lote.endereco, lote.complemento or SEM_COMPLEMENTO)
                            for lote in lotes
                        ),
                    ),
                )

    def _corpo_do_despacho(
        self,
        tipo: TipoDespacho,
        objeto: LoteUnico | ConjuntoDesenhado,
    ) -> str:
        match objeto:
            case LoteUnico(imovel=imovel):
                return corpo_do_despacho(tipo, imovel.sql)
            case ConjuntoDesenhado(lotes=lotes):
                return corpo_do_despacho_conjunto(tipo, tuple(lote.sql or "" for lote in lotes))

    def _despacho(
        self,
        pedido: PedidoCertidao,
        objeto: LoteUnico | ConjuntoDesenhado,
    ) -> tuple[Paragrafo, ...]:
        tipo = pedido.tipo_despacho
        corpo = self._corpo_do_despacho(tipo, objeto)
        paragrafos = [Paragrafo(texto=f"{abertura_do_despacho(tipo.sentido)} {corpo}")]
        if pedido.incluir_ressalva:
            paragrafos.append(Paragrafo(texto=RESSALVA_PADRAO))
        if pedido.observacoes:
            paragrafos.append(Paragrafo(texto=pedido.observacoes))
        paragrafos.append(Paragrafo(texto=VALIDADE))
        return tuple(paragrafos)

    def _localizacao(
        self,
        planta: PlantaLocalizacao | None,
        objeto: LoteUnico | ConjuntoDesenhado,
    ) -> tuple[Bloco, ...]:
        # Subtítulo solto sobre nada seria pior que a ausência da seção.
        if planta is None:
            return ()
        return (
            Subtitulo(texto=self._titulo_da_localizacao(objeto)),
            ImagemRaster(conteudo=planta.png, largura_mm=LARGURA_PLANTA_MM),
        )

    def _titulo_da_localizacao(self, objeto: LoteUnico | ConjuntoDesenhado) -> str:
        match objeto:
            case LoteUnico():
                return "Localização do Imóvel"
            case ConjuntoDesenhado():
                return "Localização dos Imóveis"

    def _endereco(self, imovel: LoteAttributes) -> str:
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
