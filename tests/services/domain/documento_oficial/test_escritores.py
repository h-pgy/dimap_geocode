from io import BytesIO

import pytest
from pydantic import ValidationError
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Flowable, Paragraph, Table
from pypdf import PdfReader

from services.domain.documento_oficial import (
    Lista,
    Paragrafo,
    Subtitulo,
    Tabela,
    TemaConfig,
    Titulo,
    montar_escritores,
    montar_tema,
)
from services.utils.pdf import (
    ColunaFixa,
    ColunaFluida,
    DocumentoPdfInput,
    Marcacao,
    MarcacaoDocumento,
    gerar_pdf,
)

ESTILO_NORMAL = getSampleStyleSheet()["Normal"]


def _marcacao_vazia() -> MarcacaoDocumento:
    return MarcacaoDocumento(
        principal=Marcacao(marcas=(), margem_lateral_mm=20.0, respiro_mm=5.0)
    )


def _texto_pdf(*flowables: Flowable) -> str:
    pdf = gerar_pdf(
        DocumentoPdfInput(titulo="teste", corpo=flowables, marcacao=_marcacao_vazia())
    )
    return "\n".join(pagina.extract_text() for pagina in PdfReader(BytesIO(pdf)).pages)


# ---------------------------------------------------------------------------
# Cada bloco textual sai com o estilo do tema
# ---------------------------------------------------------------------------


def test_cada_bloco_sai_com_o_estilo_do_tema() -> None:
    tema = montar_tema(TemaConfig())
    escritores = montar_escritores(tema)

    titulo = escritores["titulo"](Titulo(texto="Título"))
    assert titulo.style is tema.estilos["titulo"]

    for nivel in (1, 2, 3):
        subtitulo = escritores["subtitulo"](Subtitulo(texto="Sub", nivel=nivel))
        assert subtitulo.style is tema.estilos[f"subtitulo_{nivel}"]

    paragrafo = escritores["paragrafo"](Paragrafo(texto="Corpo"))
    assert paragrafo.style is tema.estilos["paragrafo"]

    recuado = escritores["paragrafo"](Paragrafo(texto="Corpo recuado", recuado=True))
    assert recuado.style is tema.estilos["paragrafo_recuado"]


# ---------------------------------------------------------------------------
# Lista: numera pela posição, e cada lista recomeça do 1
# ---------------------------------------------------------------------------


def test_lista_numera_pela_posicao_e_recomeca() -> None:
    tema = montar_tema(TemaConfig())
    escritores = montar_escritores(tema)

    ordenada = escritores["lista"](Lista(ordenada=True, itens=("Primeiro item", "Segundo item")))
    nao_ordenada = escritores["lista"](Lista(ordenada=False, itens=("Alfa", "Beta")))
    outra_ordenada = escritores["lista"](Lista(ordenada=True, itens=("Recomeça", "De novo")))

    texto = _texto_pdf(ordenada, nao_ordenada, outra_ordenada)

    assert "Primeiro item" in texto
    assert "Segundo item" in texto
    assert "Alfa" in texto
    assert "Beta" in texto
    assert "Recomeça" in texto
    assert "De novo" in texto
    # a segunda lista ordenada recomeça do 1: se ela continuasse a contagem da primeira,
    # o documento traria um marcador "3" que não existe em nenhum outro texto do teste.
    assert "3" not in texto


# ---------------------------------------------------------------------------
# Bloco de tabela: chega ao motor com colunas, cabeçalho, linhas e o estilo do tema
# ---------------------------------------------------------------------------


def test_bloco_tabela_vira_a_tabela_do_motor_com_o_estilo_do_tema() -> None:
    tema = montar_tema(TemaConfig())
    escritores = montar_escritores(tema)
    bloco = Tabela(
        colunas=(ColunaFixa(largura_mm=30.0), ColunaFluida(peso=2.0)),
        cabecalho=("Campo", "Valor"),
        linhas=(("Ambiente", "producao"), ("Momento", "21/08/2026")),
    )

    tabela = escritores["tabela"](bloco)

    assert isinstance(tabela, Table)
    cabecalho_renderizado = tabela._cellvalues[0][0]
    assert isinstance(cabecalho_renderizado, Paragraph)
    assert cabecalho_renderizado.text == "Campo"
    assert cabecalho_renderizado.style.fontName == tema.estilo_tabela.cabecalho.fontName

    celula_renderizada = tabela._cellvalues[1][0]
    assert isinstance(celula_renderizada, Paragraph)
    assert celula_renderizada.style.fontName == tema.estilo_tabela.celula.fontName

    divergente = Tabela(colunas=(ColunaFixa(largura_mm=30.0),), linhas=(("a", "b"),))
    with pytest.raises(ValidationError):
        escritores["tabela"](divergente)


# ---------------------------------------------------------------------------
# Escape: texto interpolado nunca vira marcação do reportlab
# ---------------------------------------------------------------------------


def test_texto_de_bloco_eh_escapado() -> None:
    tema = montar_tema(TemaConfig())
    escritores = montar_escritores(tema)
    texto_perigoso = "A & B <b>marcação</b>"

    paragrafo = escritores["paragrafo"](Paragrafo(texto=texto_perigoso))
    tabela = escritores["tabela"](
        Tabela(colunas=(ColunaFluida(),), linhas=((texto_perigoso,),))
    )

    texto = _texto_pdf(paragrafo, tabela)

    # A tag chega como CARACTERES literais — se tivesse virado marcação do reportlab, o
    # "<b>" não apareceria no texto extraído, e "marcação" sairia como negrito silencioso.
    assert "<b>marcação</b>" in texto
    assert "A & B" in texto
    # Escapado uma vez só: escapar de novo na célula da tabela deixaria essas sequências
    # visíveis no papel em vez dos caracteres originais.
    assert "&amp;" not in texto
    assert "&lt;" not in texto
