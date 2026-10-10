from pydantic import BaseModel, ConfigDict

from services.domain.documento_oficial import (
    Bloco,
    ConteudoDocumento,
    DocumentoRenderizado,
    MarcacaoConfig,
    Paragrafo,
    QuadroSeloConfig,
    RenderizarDocumentoInput,
    RenderizarDocumentoOficial,
    SeloConfig,
    SeloDeFecho,
    Tabela,
    Tema,
    Titulo,
    marcacao_fazenda_dimap_selado,
)
from services.domain.documento_selado import (
    SeloImpresso,
    SeloImpressoInput,
    montar_selo_impresso,
)
from services.domain.listagem_gestao import LinhaExecucao
from services.utils.pdf import ColunaFixa, ColunaFluida

from .models import CertidaoAtosInput, RecorteDeclarado

TITULO = "Certidão de Atos Praticados"
FE_PUBLICA = (
    "A presente certidão é emitida com base nos registros do sistema, tendo fé pública "
    "e validade em todo o território nacional."
)


class MontarCertidaoInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    certidao: CertidaoAtosInput
    selo: SeloImpresso
    quadro: QuadroSeloConfig


class MontarCertidaoAtos:
    """Callable: o pedido → o conteúdo. Único lugar em que esta certidão é redigida."""

    def __call__(self, pedido: MontarCertidaoInput) -> ConteudoDocumento:
        return self.pipeline(pedido)

    def pipeline(self, pedido: MontarCertidaoInput) -> ConteudoDocumento:
        return ConteudoDocumento(
            titulo=TITULO,
            nome_arquivo=f"certidao_atos_{pedido.certidao.envelope.codigo}.pdf",
            blocos=self._blocos(pedido),
        )

    def _blocos(self, pedido: MontarCertidaoInput) -> tuple[Bloco, ...]:
        # A certidão negativa NÃO é outro documento: é o mesmo, com o corpo dizendo que nada houve.
        # Dois tipos de documento divergiriam no timbre, no fecho e no selo com o primeiro ajuste.
        corpo: Bloco = self._tabela(pedido) if pedido.certidao.atos else self._negativa()
        return (
            Titulo(texto=TITULO),
            Paragrafo(texto=self._abertura(pedido)),
            Paragrafo(texto=self._criterios(pedido.certidao.recorte)),
            corpo,
            Paragrafo(texto=FE_PUBLICA),
            SeloDeFecho(selo=pedido.selo, quadro=pedido.quadro),
        )

    def _abertura(self, pedido: MontarCertidaoInput) -> str:
        autor = pedido.certidao.envelope.autor
        alvo = pedido.certidao.envelope.alvo
        return (
            f"Certifico, para os devidos fins e a pedido da parte interessada, que constam nos registros "
            f"deste sistema os atos administrativos praticados por {autor.nome}, RF {alvo.identificador}."
        )

    def _negativa(self) -> Paragrafo:
        return Paragrafo(
            texto="NÃO CONSTA registro de ato administrativo praticado pelo servidor no período e critérios especificados."
        )

    def _criterios(self, recorte: RecorteDeclarado) -> str:
        # Sem esta frase, "nenhum ato" e "nenhum ato DESTE tipo" saem indistinguíveis no papel.
        tipos = ", ".join(recorte.tipos) if recorte.tipos else "todos os tipos de ato"
        return (
            f"Período de {recorte.inicio:%d/%m/%Y} a {recorte.fim:%d/%m/%Y}. Tipos considerados: {tipos}."
        )

    def _tabela(self, pedido: MontarCertidaoInput) -> Tabela:
        return Tabela(
            colunas=(
                ColunaFixa(largura_mm=28.0),
                ColunaFluida(),
                ColunaFixa(largura_mm=32.0),
                ColunaFixa(largura_mm=22.0),
            ),
            cabecalho=("Data e hora", "Ato praticado", "Sobre o quê", "Unidade"),
            linhas=tuple(self._celulas(ato) for ato in pedido.certidao.atos),
        )

    def _celulas(self, ato: LinhaExecucao) -> tuple[str, ...]:
        # Cargo e unidade saem da LINHA, não do cadastro: é a cópia que a SPEC autorizacao/004 fez
        # no dia do ato, e é ela que faz a certidão continuar verdadeira depois de uma transferência.
        praticado = f"{ato.acao} — {ato.operacao}" if ato.operacao else ato.acao
        return (ato.momento, praticado, ato.alvo, ato.unidade)


class CertidaoAtos:
    """Callable: o tipo amarra o que a certidão diz, o papel SELADO em que ela sai e o tema. Quem
    emite só preenche o DTO."""

    def __init__(self, tema: Tema, config: MarcacaoConfig, selo_config: SeloConfig) -> None:
        self._montar = MontarCertidaoAtos()
        self._tema = tema
        self._config = config
        self._selo_config = selo_config
        self._renderizar = RenderizarDocumentoOficial(tema)

    def __call__(self, pedido: CertidaoAtosInput) -> DocumentoRenderizado:
        return self.pipeline(pedido)

    def pipeline(self, pedido: CertidaoAtosInput) -> DocumentoRenderizado:
        # O selo entra pelo `__call__`, nunca pelo construtor: "sempre selada" é política do tipo,
        # mas autor, código e instante são de CADA emissão.
        selo = montar_selo_impresso(
            SeloImpressoInput(envelope=pedido.envelope, base_url=pedido.base_url)
        )
        return self._renderizar(
            RenderizarDocumentoInput(
                conteudo=self._montar(
                    MontarCertidaoInput(
                        certidao=pedido,
                        selo=selo,
                        quadro=self._selo_config.fecho,
                    )
                ),
                marcacao=marcacao_fazenda_dimap_selado(
                    self._config,
                    self._tema,
                    selo,
                    self._selo_config.compacto,
                ),
            )
        )
