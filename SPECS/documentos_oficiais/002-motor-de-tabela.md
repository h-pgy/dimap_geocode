---
spec: documentos_oficiais/002
versao: v2
atualizado_em: 2026-09-07
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
  - v2: implementado — services/utils/pdf/tabela/ (regras, estilo, escritor) e models/tabela.py,
    seguindo os testes do §8; o peso da coluna fluida sai normalizado pela soma das fluidas do
    pedido, e não como percentual bruto do snippet (§7, Caveats)
---

# SPEC documentos_oficiais/002 — Motor de tabela: coluna que só vira medida na página

## 1 · User story
**Requisito não-funcional** — o motor de PDF passa a saber montar tabela paginada, com o visual
declarado como composição de regras independentes, sem que quem chama fale largura em pontos nem
descubra na impressão que uma célula saiu cortada.

## 2 · Condições de pronto
- [ ] A tabela é montada declarando **colunas, cabeçalho e linhas de texto** — nunca largura em pontos:
      a coluna é **fixa em milímetros** ou **fluida por peso**, e a fluida reparte o que sobra da
      largura útil, que só a página conhece.
- [ ] Tabela mais longa que a página **quebra e repete o cabeçalho**, e **célula com texto longo quebra
      dentro da própria célula** em vez de estourar a coluna ou sair cortada.
- [ ] O visual é **composição de regras independentes** — fundo do cabeçalho, zebra, grade, respiro:
      acrescentar uma regra não toca nas outras nem no conteúdo.
- [ ] **Linha com número de células diferente do de colunas é recusada na construção**, e tabela **sem
      cabeçalho** é caso de primeira classe, não um cabeçalho vazio.
- [ ] Texto de célula sai **como texto no papel**, e não como marcação do reportlab.

## 3 · Domínio

A tabela é vocabulário de **página**, e não de domínio: ela sabe repartir largura, quebrar entre páginas
e repetir cabeçalho — e nada sobre o que as células dizem. Quem sabe disso é o domínio que a compõe
(SPEC [documentos_oficiais/003](003-documento-oficial-timbrado.md)). Ela mora ao lado do motor de PDF,
na SPEC [documentos_oficiais/001](001-motor-de-pdf.md), e herda dele o milímetro como unidade.

A largura da coluna é declarada como **tipo**, não como número resolvido: `ColunaFixa` vale o milímetro
que pede, e `ColunaFluida` só vira medida na página, porque a largura útil do corpo é o que a marcação
deixou — e isso não existe no momento em que a tabela é declarada.

O `Alinhamento` entra no `models/texto.py` do motor: alinhar é assunto de como uma linha se escreve, e
a coluna apenas o usa. Os models da tabela ganham módulo próprio no mesmo pacote.

**`services/utils/pdf/models/texto.py`** — acrescenta o alinhamento ao que já existe.
```python
class Alinhamento(StrEnum):
    ESQUERDA = "esquerda"
    CENTRO = "centro"
    DIREITA = "direita"
```

**`services/utils/pdf/models/tabela.py`**
```python
from .texto import Alinhamento


class Coluna(BaseModel):
    """O que toda coluna tem é alinhamento; é a largura que separa os dois subtipos."""

    model_config = ConfigDict(frozen=True)

    alinhamento: Alinhamento = Alinhamento.ESQUERDA


class ColunaFixa(Coluna):
    """Largura que não depende da página: código, data, valor."""

    largura_mm: float


class ColunaFluida(Coluna):
    """Peso sobre o que sobra depois das fixas. Quanto é isso, só a página sabe."""

    peso: float = 1.0


class Grade(BaseModel):
    """A tabela em números — é tudo que uma regra precisa para mirar as células certas."""

    model_config = ConfigDict(frozen=True)

    colunas: int
    linhas_cabecalho: int
    linhas_corpo: int


# O comando de `TableStyle`: ("BACKGROUND", (coluna, linha), (coluna, linha), valor).
type ComandoTabela = tuple[object, ...]
```

**`services/utils/pdf/models/__init__.py`** — passa a reexportar também o vocabulário da tabela.
```python
from .pagina import A3, A4, Faixa, FormatoPagina, Margens, Orientacao, Posicao, TamanhoPagina
from .tabela import Coluna, ColunaFixa, ColunaFluida, ComandoTabela, Grade
from .texto import Alinhamento, EstiloTexto
```

## 4 · Fora de escopo
- **Flowable dentro de célula** — imagem, lista ou tabela aninhada. A célula é texto; entra quando
  houver documento que precise.
- **Tabela como bloco do documento oficial** — o tipo de bloco, o escritor e os tokens de tabela do
  tema: SPEC `documentos_oficiais/003`.
- **Ordenar, agrupar, somar ou formatar valor** — a tabela recebe texto pronto; quem decide o que a
  linha diz é o domínio que a monta.
- Coluna que se repete em página larga, célula mesclada e quebra de coluna — sem dono ainda.

## 5 · Peças de referência a compor
- `@SPECS/documentos_oficiais/001-motor-de-pdf.md` → o pacote de models, o milímetro como unidade e a
  moldura que a marcação deixa.
- Skills: `ontologia`, `escrever-testes`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`services/utils/pdf/tabela/`** — a tabela em três peças, na mesma divisão da marcação: as regras, o
estilo que as compõe e o escritor que monta o flowable. O que varia entre documentos é a tupla de
regras, nunca o escritor.

**`services/utils/pdf/tabela/regras.py`** — cada regra pinta um traço e não conhece as outras. A
`RegraTabela` é ABC pelo mesmo motivo da `Marca`: define interface e nada mais (CLAUDE.md §7.1).
```python
from reportlab.lib.colors import Color
from reportlab.lib.units import mm

from ..models import ComandoTabela, Grade


class RegraTabela(ABC):
    """Um traço visual da tabela: recebe a grade e devolve os comandos dele."""

    @abstractmethod
    def __call__(self, grade: Grade) -> tuple[ComandoTabela, ...]: ...


class FundoDoCabecalho(RegraTabela):
    def __init__(self, cor: Color) -> None:
        self._cor = cor

    def __call__(self, grade: Grade) -> tuple[ComandoTabela, ...]:
        # Tabela sem cabeçalho existe (par rótulo/valor), e pintar a linha 0 nela apagaria um dado.
        if grade.linhas_cabecalho == 0:
            return ()
        return (("BACKGROUND", (0, 0), (-1, grade.linhas_cabecalho - 1), self._cor),)


class ZebraDoCorpo(RegraTabela):
    """Alternância só no corpo: o cabeçalho tem o fundo dele e ficaria fora de fase se entrasse."""

    def __init__(self, cor: Color, cor_alternada: Color) -> None:
        self._cores = [cor, cor_alternada]

    def __call__(self, grade: Grade) -> tuple[ComandoTabela, ...]:
        return (("ROWBACKGROUNDS", (0, grade.linhas_cabecalho), (-1, -1), self._cores),)


class GradeDeLinhas(RegraTabela):
    def __init__(self, cor: Color, espessura_pt: float) -> None:
        self._cor = cor
        self._espessura_pt = espessura_pt

    def __call__(self, grade: Grade) -> tuple[ComandoTabela, ...]:
        return (("GRID", (0, 0), (-1, -1), self._espessura_pt, self._cor),)


class Respiro(RegraTabela):
    """O ar dentro da célula — em milímetros, como todo o resto do módulo."""

    def __init__(self, horizontal_mm: float, vertical_mm: float) -> None:
        self._horizontal_mm = horizontal_mm
        self._vertical_mm = vertical_mm

    def __call__(self, grade: Grade) -> tuple[ComandoTabela, ...]:
        return (
            ("LEFTPADDING", (0, 0), (-1, -1), self._horizontal_mm * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), self._horizontal_mm * mm),
            ("TOPPADDING", (0, 0), (-1, -1), self._vertical_mm * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), self._vertical_mm * mm),
        )
```

**`services/utils/pdf/tabela/estilo.py`** — a composição, gêmea da `Marcacao`: regra nova entra na tupla
e em lugar nenhum mais.
```python
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import TableStyle

from ..models import Grade
from .regras import RegraTabela


class EstiloTabela:
    """Callable: as regras declaradas viram um `TableStyle` só. A tipografia vem de quem chama (o
    tema do §002), nunca daqui."""

    def __init__(
        self,
        celula: ParagraphStyle,
        cabecalho: ParagraphStyle,
        regras: tuple[RegraTabela, ...] = (),
    ) -> None:
        self.celula = celula
        self.cabecalho = cabecalho
        self._regras = regras

    def __call__(self, grade: Grade) -> TableStyle:
        return TableStyle([comando for regra in self._regras for comando in regra(grade)])
```

**`services/utils/pdf/tabela/escritor.py`** — o que vira flowable. O input mora aqui, e não nos models,
porque carrega o `EstiloTabela`: pô-lo lá faria os models dependerem do estilo que os consome.
```python
from html import escape

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
            colWidths=[self._largura(coluna) for coluna in pedido.colunas],
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

    def _largura(self, coluna: Coluna) -> float | str:
        # A fluida sai como peso percentual, que o reportlab só resolve contra a largura da moldura,
        # na página. É o que permite declarar a coluna sem conhecer a marcação.
        match coluna:
            case ColunaFixa():
                return coluna.largura_mm * mm
            case ColunaFluida():
                return f"{coluna.peso}%"
        raise TypeError(f"Coluna sem largura declarada: {type(coluna).__name__}")

    def _grade(self, pedido: TabelaInput) -> Grade:
        return Grade(
            colunas=len(pedido.colunas),
            linhas_cabecalho=0 if pedido.cabecalho is None else 1,
            linhas_corpo=len(pedido.linhas),
        )


tabela_pdf = TabelaPdf()
```

**`services/utils/pdf/tabela/__init__.py`** — só reexporta (CLAUDE.md §7.2).
```python
from .escritor import TabelaInput, TabelaPdf, tabela_pdf
from .estilo import EstiloTabela
from .regras import FundoDoCabecalho, GradeDeLinhas, RegraTabela, Respiro, ZebraDoCorpo

__all__ = [
    "EstiloTabela",
    "FundoDoCabecalho",
    "GradeDeLinhas",
    "RegraTabela",
    "Respiro",
    "TabelaInput",
    "TabelaPdf",
    "ZebraDoCorpo",
    "tabela_pdf",
]
```

**`pyproject.toml`** — sem dependência nova: `Table`, `TableStyle` e `Paragraph` são do reportlab que
a SPEC 001 já traz, e o `pypdf` de teste também.

## 7 · Caveats
O peso da `ColunaFluida` não vira `f"{peso}%"` direto, como o snippet de `_largura` sugeria: o
reportlab só reparte o restante inteiro quando os percentuais de uma linha somam exatamente 100 —
testado empiricamente contra a biblioteca antes de escrever o teste. Com o peso padrão (1.0) em
duas colunas fluidas, a soma bruta (2) deixa quase toda a largura sem coluna nenhuma. Por isso
`_larguras` normaliza cada peso pela soma das fluidas do **mesmo pedido** antes de formatar o
percentual — o peso passa a se comportar como peso relativo (equivalente a `flex-grow`), e o padrão
de 1.0 para várias fluidas reparte o restante em partes iguais. O custo é que `_largura` deixa de
ser pura por coluna: precisa do total de peso do conjunto, calculado uma vez em `_larguras`.

A célula da tabela é sempre `Paragraph`, nunca `str`, e o texto é escapado ali. String crua não quebra
linha no reportlab: estoura a coluna e sai cortada sem aviso. O custo é que a célula não aceita
marcação nenhuma — negrito numa palavra pede regra ou bloco novo — e que cada célula carrega um
`ParagraphStyle` clonado pelo alinhamento da coluna.

A coluna fluida vira peso percentual do reportlab, resolvido contra **o que sobra** depois das fixas, e
só na página. É o que permite declarar a tabela sem conhecer a moldura, que a marcação define. O custo
é que colunas fixas somando mais que a largura útil não são recusadas em lugar nenhum: a tabela
transborda a moldura em silêncio.

O cabeçalho reaparece na quebra por `repeatRows`, e o `Paragraph` quebra o texto dentro da célula — mas
**uma linha mais alta que a página inteira continua sem ter como quebrar**: o reportlab a empurra para
a página seguinte e ela transborda. É limite conhecido do flowable, não coberto por teste.

## 8 · Testes (TDD)
- `test_tabela_recusa_linha_com_celulas_a_mais_ou_a_menos` — linha com número de células diferente do
  de colunas levanta na construção do input, e cabeçalho divergente também.
- `test_coluna_fluida_reparte_o_que_sobra_da_largura` — numa moldura conhecida, a coluna fixa conserva
  os milímetros declarados e as fluidas dividem o restante na proporção dos pesos.
- `test_estilo_soma_os_comandos_das_regras` — o `TableStyle` traz exatamente os comandos das regras
  declaradas; acrescentar uma regra não altera os comandos das demais, e a tabela sem cabeçalho não
  recebe comando de cabeçalho.
- `test_tabela_longa_quebra_e_repete_o_cabecalho` — tabela que ocupa três páginas gera três páginas, e
  o texto do cabeçalho aparece em todas.
- `test_celula_longa_quebra_dentro_da_celula` — célula de texto longo aumenta a altura da linha e sai
  inteira no texto extraído, sem cortar; `&` e `<b>` saem como texto, não como marcação.
