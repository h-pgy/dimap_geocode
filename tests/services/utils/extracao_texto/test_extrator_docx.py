from io import BytesIO

from docx import Document

from services.utils.extracao_texto.extrator_docx import ExtratorDocx

PARAGRAFO = "Este documento orienta a emissão da certidão de lançamento do IPTU."
CELULA = "Valor venal de referência"


def _docx() -> bytes:
    documento = Document()
    documento.add_paragraph(PARAGRAFO)
    tabela = documento.add_table(rows=1, cols=2)
    tabela.cell(0, 0).text = CELULA
    tabela.cell(0, 1).text = "R$ 100.000,00"
    saida = BytesIO()
    documento.save(saida)
    return saida.getvalue()


def test_docx_rende_texto_de_paragrafos_e_tabelas() -> None:
    texto = ExtratorDocx()(_docx())

    assert PARAGRAFO in texto.conteudo
    assert CELULA in texto.conteudo
