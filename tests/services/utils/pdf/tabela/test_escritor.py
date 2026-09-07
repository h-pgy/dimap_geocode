from io import BytesIO

import pytest
from pydantic import ValidationError
from pypdf import PdfReader
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Flowable

from services.utils.pdf.documento import DocumentoPdfInput, gerar_pdf
from services.utils.pdf.documento_marcado import MarcacaoDocumento
from services.utils.pdf.marcacao import Marcacao
from services.utils.pdf.models import Alinhamento, ColunaFixa, ColunaFluida
from services.utils.pdf.tabela import EstiloTabela, TabelaInput, tabela_pdf

ESTILO_PARAGRAFO = getSampleStyleSheet()["Normal"]


def _coluna_fixa(largura_mm: float = 20.0, alinhamento: Alinhamento = Alinhamento.ESQUERDA) -> ColunaFixa:
    return ColunaFixa(largura_mm=largura_mm, alinhamento=alinhamento)


def _coluna_fluida(peso: float = 1.0, alinhamento: Alinhamento = Alinhamento.ESQUERDA) -> ColunaFluida:
    return ColunaFluida(peso=peso, alinhamento=alinhamento)


def _estilo_tabela() -> EstiloTabela:
    return EstiloTabela(celula=ESTILO_PARAGRAFO, cabecalho=ESTILO_PARAGRAFO)


def _documento_com(corpo: tuple[Flowable, ...]) -> bytes:
    marcacao = MarcacaoDocumento(principal=Marcacao(marcas=(), margem_lateral_mm=20.0, respiro_mm=5.0))
    return gerar_pdf(DocumentoPdfInput(titulo="Tabela de teste", corpo=corpo, marcacao=marcacao))


# ---------------------------------------------------------------------------
# Contrato de entrada: linha e cabeçalho precisam bater com as colunas
# ---------------------------------------------------------------------------


def test_tabela_recusa_linha_com_celulas_a_mais_ou_a_menos() -> None:
    colunas = (_coluna_fixa(20.0), _coluna_fluida())

    with pytest.raises(ValidationError):
        TabelaInput(colunas=colunas, linhas=(("a", "b"), ("faltando",)), estilo=_estilo_tabela())
    with pytest.raises(ValidationError):
        TabelaInput(colunas=colunas, linhas=(("a", "b", "sobrando"),), estilo=_estilo_tabela())
    with pytest.raises(ValidationError):
        TabelaInput(colunas=colunas, linhas=(("a", "b"),), cabecalho=("só um",), estilo=_estilo_tabela())

    # As mesmas colunas, com linha e cabeçalho corretos, constroem sem erro.
    TabelaInput(colunas=colunas, linhas=(("a", "b"),), cabecalho=("um", "dois"), estilo=_estilo_tabela())


# ---------------------------------------------------------------------------
# Coluna fixa conserva o milímetro; fluida reparte o restante pelo peso
# ---------------------------------------------------------------------------


def test_coluna_fluida_reparte_o_que_sobra_da_largura() -> None:
    pedido = TabelaInput(
        colunas=(_coluna_fixa(largura_mm=40.0), _coluna_fluida(peso=1.0), _coluna_fluida(peso=3.0)),
        linhas=(("x", "y", "z"),),
        estilo=_estilo_tabela(),
    )
    moldura_mm = 160.0

    flowable = tabela_pdf(pedido)
    flowable.wrap(moldura_mm * mm, 1000 * mm)
    larguras_mm = [largura / mm for largura in flowable._colWidths]

    resto_mm = moldura_mm - 40.0
    assert larguras_mm[0] == pytest.approx(40.0)
    assert larguras_mm[1] == pytest.approx(resto_mm * 1 / 4)
    assert larguras_mm[2] == pytest.approx(resto_mm * 3 / 4)
    # As fluidas repartem TUDO que sobra da fixa — nada de largura útil fica sem coluna.
    assert sum(larguras_mm) == pytest.approx(moldura_mm)


# ---------------------------------------------------------------------------
# Quebra de página: o cabeçalho reaparece em todas
# ---------------------------------------------------------------------------


def test_tabela_longa_quebra_e_repete_o_cabecalho() -> None:
    pedido = TabelaInput(
        colunas=(_coluna_fixa(40.0), _coluna_fluida()),
        cabecalho=("Item", "Descrição"),
        linhas=tuple((f"Linha {n}", "Texto de corpo da tabela") for n in range(150)),
        estilo=_estilo_tabela(),
    )

    pdf = _documento_com((tabela_pdf(pedido),))

    paginas = PdfReader(BytesIO(pdf)).pages
    assert len(paginas) >= 3
    for pagina in paginas:
        assert "Item" in pagina.extract_text()


# ---------------------------------------------------------------------------
# Célula de texto longo: quebra sem cortar, e sem interpretar marcação
# ---------------------------------------------------------------------------


def test_celula_longa_quebra_dentro_da_celula() -> None:
    texto_longo = ("Texto de teste que precisa ocupar bastante espaço horizontal. " * 5) + "FIMDOTEXTO"
    texto_com_marcacao = "Valor & <b>não</b> negrito"
    pedido = TabelaInput(
        colunas=(_coluna_fixa(30.0), _coluna_fluida()),
        linhas=(
            ("curta", "ok"),
            ("longa", texto_longo),
            ("marcado", texto_com_marcacao),
        ),
        estilo=_estilo_tabela(),
    )

    flowable = tabela_pdf(pedido)
    flowable.wrap(150 * mm, 1000 * mm)
    # A célula de texto longo cresce bem além de uma linha de texto curto — prova que ela quebrou
    # dentro da própria célula em vez de estourar a coluna.
    assert flowable._rowHeights[1] > flowable._rowHeights[0] * 2

    pdf = _documento_com((flowable,))
    texto_extraido = " ".join(PdfReader(BytesIO(pdf)).pages[0].extract_text().split())

    # O texto sai inteiro, sem cortar: o marcador do fim da célula longa está presente.
    assert "FIMDOTEXTO" in texto_extraido
    # `&` e `<b>` saem como texto no papel, não como marcação do reportlab.
    assert "Valor &" in texto_extraido
    assert "<b>não</b> negrito" in texto_extraido
