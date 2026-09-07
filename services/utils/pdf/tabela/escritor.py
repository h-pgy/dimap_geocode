from html import escape

from pydantic import BaseModel, ConfigDict, model_validator
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Paragraph, Table

from ..models import Alinhamento, Coluna, ColunaFixa, ColunaFluida, Grade
from .estilo import EstiloTabela

ALINHAMENTO_PARAGRAFO = {
    Alinhamento.ESQUERDA: TA_LEFT,
    Alinhamento.CENTRO: TA_CENTER,
    Alinhamento.DIREITA: TA_RIGHT,
}


class TabelaInput(BaseModel):
    # `EstiloTabela` carrega `ParagraphStyle` do reportlab — ver Caveats.
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    colunas: tuple[Coluna, ...]
    linhas: tuple[tuple[str, ...], ...]
    estilo: EstiloTabela
    # `None` é a tabela sem cabeçalho, não um cabeçalho vazio: presença é dado, não bandeira.
    cabecalho: tuple[str, ...] | None = None

    @model_validator(mode="after")
    def _celulas_batem_com_as_colunas(self) -> "TabelaInput":
        # Célula sobrando o reportlab descarta calado; faltando, ele desloca a linha inteira e o
        # documento sai com o valor sob o rótulo errado.
        esperado = len(self.colunas)
        divergentes = [i for i, linha in enumerate(self.linhas) if len(linha) != esperado]
        if divergentes:
            raise ValueError(f"Linhas com número de células diferente de {esperado}: {divergentes}")
        if self.cabecalho is not None and len(self.cabecalho) != esperado:
            raise ValueError(f"Cabeçalho com {len(self.cabecalho)} células para {esperado} colunas")
        return self


class TabelaPdf:
    """Callable: colunas, cabeçalho e linhas de texto → o flowable. Ponto e coordenada morrem aqui,
    como na `Folha`."""

    def __call__(self, pedido: TabelaInput) -> Flowable:
        return self.pipeline(pedido)

    def pipeline(self, pedido: TabelaInput) -> Flowable:
        grade = self._grade(pedido)
        return Table(
            self._dados(pedido),
            colWidths=self._larguras(pedido.colunas),
            style=pedido.estilo(grade),
            # O que faz o cabeçalho reaparecer depois da quebra: sem isto, a tabela continua na
            # página seguinte com as colunas sem nome.
            repeatRows=grade.linhas_cabecalho,
        )

    def _dados(self, pedido: TabelaInput) -> list[list[Paragraph]]:
        corpo = [
            self._linha(linha, pedido.colunas, pedido.estilo.celula) for linha in pedido.linhas
        ]
        if pedido.cabecalho is None:
            return corpo
        return [self._linha(pedido.cabecalho, pedido.colunas, pedido.estilo.cabecalho), *corpo]

    def _linha(
        self,
        celulas: tuple[str, ...],
        colunas: tuple[Coluna, ...],
        estilo: ParagraphStyle,
    ) -> list[Paragraph]:
        return [
            self._celula(texto, coluna, estilo)
            for texto, coluna in zip(celulas, colunas, strict=True)
        ]

    def _celula(self, texto: str, coluna: Coluna, estilo: ParagraphStyle) -> Paragraph:
        # Célula como `str` não quebra linha no reportlab: estoura a coluna e sai cortada. Como
        # `Paragraph` ela quebra — e passa a interpretar marcação, o que o escape impede.
        alinhado = estilo.clone(estilo.name, alignment=ALINHAMENTO_PARAGRAFO[coluna.alinhamento])
        return Paragraph(escape(texto), alinhado)

    def _larguras(self, colunas: tuple[Coluna, ...]) -> list[float | str]:
        # O peso normaliza contra a soma das fluidas do PEDIDO, não contra 100 fixo: o reportlab só
        # reparte o restante inteiro quando os percentuais somam exatamente 100 — ver Caveats.
        peso_total = sum(coluna.peso for coluna in colunas if isinstance(coluna, ColunaFluida))
        return [self._largura(coluna, peso_total) for coluna in colunas]

    def _largura(self, coluna: Coluna, peso_total_fluido: float) -> float | str:
        match coluna:
            case ColunaFixa():
                return coluna.largura_mm * mm
            case ColunaFluida():
                return f"{coluna.peso / peso_total_fluido * 100}%"
        raise TypeError(f"Coluna sem largura declarada: {type(coluna).__name__}")

    def _grade(self, pedido: TabelaInput) -> Grade:
        return Grade(
            colunas=len(pedido.colunas),
            linhas_cabecalho=0 if pedido.cabecalho is None else 1,
            linhas_corpo=len(pedido.linhas),
        )


tabela_pdf = TabelaPdf()
