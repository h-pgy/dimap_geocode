import re
from io import BytesIO
from pathlib import Path
from typing import cast

import pytest
from pypdf import PdfReader
from pypdf.generic import DictionaryObject
from reportlab.lib.colors import black
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Flowable, PageBreak, Paragraph

from services.utils.pdf.documento import DocumentoPdfInput, gerar_pdf
from services.utils.pdf.documento_marcado import MarcacaoDocumento
from services.utils.pdf.folha import Folha
from services.utils.pdf.forma import VetorNomeado
from services.utils.pdf.marcacao import Marca, Marcacao
from services.utils.pdf.models import A4, EstiloTexto, Faixa, Orientacao, Posicao
from services.utils.pdf.vetor import carregar_vetor

ESTILO_PARAGRAFO = getSampleStyleSheet()["Normal"]

SVG_RETANGULO = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10" viewBox="0 0 20 10">
<rect x="0" y="0" width="20" height="10" fill="#336633" />
</svg>"""


class _MarcaVetor(Marca):
    """Marca de teste: pinta o SVG dado, na faixa recebida, sob o nome pedido."""

    def __init__(self, posicao: Posicao, altura_mm: float, caminho: Path, nome: str) -> None:
        self.posicao = posicao
        self.altura_mm = altura_mm
        self._caminho = caminho
        self._nome = nome

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        desenho = carregar_vetor(self._caminho, largura_mm=faixa.largura_mm or 20.0)
        folha.vetor(faixa.esquerda_mm, faixa.topo_mm, VetorNomeado(desenho=desenho, nome=self._nome))


class _MarcaNumeracao(Marca):
    """Marca de teste: escreve 'Pagina X de Y' sem acento, para bater byte a byte no PDF."""

    posicao = Posicao.INFERIOR
    altura_mm = 8.0

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        estilo = EstiloTexto(fonte="Helvetica", corpo_pt=10.0, cor=black)
        conteudo = f"Pagina {folha.pagina} de {folha.total}"
        folha.texto(faixa.esquerda_mm, faixa.topo_mm + 5.0, conteudo, estilo)


class _MarcaMuda(Marca):
    """Marca de teste: só reserva altura, não pinta nada."""

    def __init__(self, posicao: Posicao, altura_mm: float) -> None:
        self.posicao = posicao
        self.altura_mm = altura_mm

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        return None


def _svg(tmp_path: Path) -> Path:
    caminho = tmp_path / "vetor.svg"
    caminho.write_text(SVG_RETANGULO)
    return caminho


def _marcacao(
    *marcas: Marca,
    margem_lateral_mm: float = 20.0,
    margem_vertical_mm: float = 10.0,
    respiro_mm: float = 5.0,
) -> Marcacao:
    return Marcacao(
        marcas=marcas,
        margem_lateral_mm=margem_lateral_mm,
        margem_vertical_mm=margem_vertical_mm,
        respiro_mm=respiro_mm,
    )


def _paragrafo(texto: str) -> Paragraph:
    return Paragraph(texto, ESTILO_PARAGRAFO)


def _pdf(corpo: tuple[Flowable, ...], marcacao: MarcacaoDocumento) -> bytes:
    return gerar_pdf(DocumentoPdfInput(titulo="Documento de teste", corpo=corpo, marcacao=marcacao))


# ---------------------------------------------------------------------------
# Bytes, sem arquivo em disco
# ---------------------------------------------------------------------------


def test_documento_sai_como_bytes_sem_tocar_o_disco(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    pdf = _pdf((_paragrafo("Olá"),), MarcacaoDocumento(principal=_marcacao()))

    assert pdf.startswith(b"%PDF")
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Marca de fundo sob o corpo
# ---------------------------------------------------------------------------


def test_marca_de_fundo_fica_atras_do_corpo(tmp_path: Path) -> None:
    fundo = _MarcaVetor(Posicao.FUNDO, altura_mm=0.0, caminho=_svg(tmp_path), nome="fundo_teste")
    pdf = _pdf(
        (_paragrafo("Texto do corpo"),),
        MarcacaoDocumento(principal=_marcacao(fundo)),
    )

    fluxo = PdfReader(BytesIO(pdf)).pages[0].get_contents()
    assert fluxo is not None
    conteudo = fluxo.get_data()
    # O nome pedido para a marca vira sufixo do nome interno do Form no reportlab (ex.:
    # "FormXob.fundo_teste") — o que importa aqui é a ordem, não o nome exato do objeto.
    indice_fundo = conteudo.find(b"fundo_teste Do")
    indice_corpo = conteudo.find(b"(Texto do corpo)")

    assert indice_fundo != -1
    assert indice_corpo != -1
    assert indice_fundo < indice_corpo


# ---------------------------------------------------------------------------
# Conteúdo longo: quebra e a marcação se repete
# ---------------------------------------------------------------------------


def test_conteudo_longo_quebra_e_repete_a_marcacao(tmp_path: Path) -> None:
    vetor = _MarcaVetor(Posicao.SUPERIOR, altura_mm=10.0, caminho=_svg(tmp_path), nome="marca_repetida")
    corpo = (
        _paragrafo("Página 1"),
        PageBreak(),
        _paragrafo("Página 2"),
        PageBreak(),
        _paragrafo("Página 3"),
    )
    pdf = _pdf(corpo, MarcacaoDocumento(principal=_marcacao(vetor)))

    paginas = PdfReader(BytesIO(pdf)).pages
    assert len(paginas) == 3
    for pagina in paginas:
        recursos = cast(DictionaryObject, pagina["/Resources"])
        xobjects = recursos.get("/XObject", {})
        assert any(nome.endswith("marca_repetida") for nome in xobjects)


# ---------------------------------------------------------------------------
# O vetor é um Form XObject único, não replicado por página
# ---------------------------------------------------------------------------


def test_vetor_eh_escrito_uma_vez_so(tmp_path: Path) -> None:
    marcacao = MarcacaoDocumento(
        principal=_marcacao(_MarcaVetor(Posicao.SUPERIOR, altura_mm=10.0, caminho=_svg(tmp_path), nome="unico"))
    )
    tres_paginas = (_paragrafo("A"), PageBreak(), _paragrafo("B"), PageBreak(), _paragrafo("C"))
    seis_paginas = tres_paginas + (
        PageBreak(),
        _paragrafo("D"),
        PageBreak(),
        _paragrafo("E"),
        PageBreak(),
        _paragrafo("F"),
    )

    pdf_tres = _pdf(tres_paginas, marcacao)
    pdf_seis = _pdf(seis_paginas, marcacao)

    formas = re.compile(rb"/Subtype\s*/Form")
    assert len(formas.findall(pdf_tres)) == len(formas.findall(pdf_seis))
    # Dobrar as páginas não dobra o tamanho: só o texto do corpo cresce, não o vetor.
    assert len(pdf_seis) < len(pdf_tres) * 1.8


# ---------------------------------------------------------------------------
# Numeração com o total real de páginas
# ---------------------------------------------------------------------------


def test_numeracao_diz_o_total_real() -> None:
    corpo = (_paragrafo("Página 1"), PageBreak(), _paragrafo("Página 2"), PageBreak(), _paragrafo("Página 3"))
    pdf = _pdf(corpo, MarcacaoDocumento(principal=_marcacao(_MarcaNumeracao())))

    paginas = PdfReader(BytesIO(pdf)).pages
    assert len(paginas) == 3
    assert "Pagina 1 de 3" in paginas[0].extract_text()
    assert "Pagina 3 de 3" in paginas[2].extract_text()


# ---------------------------------------------------------------------------
# A moldura do corpo cabe a marcação mais alta do documento
# ---------------------------------------------------------------------------


def test_moldura_cabe_a_marcacao_mais_alta() -> None:
    baixa = _marcacao(_MarcaMuda(Posicao.SUPERIOR, altura_mm=10.0))
    alta = _marcacao(_MarcaMuda(Posicao.SUPERIOR, altura_mm=50.0))
    tamanho = A4.orientar(Orientacao.RETRATO)

    documento_com_override = MarcacaoDocumento(principal=baixa, primeira=alta)
    # "Sem override" aqui é o documento que usa a marcação mais alta em TODA página — é o que
    # `documento_com_override` reproduz na prática, já que a margem já sai fixada nesse tamanho.
    documento_sem_override = MarcacaoDocumento(principal=alta)

    assert documento_com_override.margens(tamanho).superior_mm == alta.margens(tamanho).superior_mm

    # Flowable é consumido no build (Caveats da SPEC): cada documento recebe seu próprio conjunto.
    def _corpo() -> tuple[Flowable, ...]:
        return tuple(_paragrafo(f"Linha de corpo número {n}. " * 8) for n in range(80))

    pdf_com_override = _pdf(_corpo(), documento_com_override)
    pdf_sem_override = _pdf(_corpo(), documento_sem_override)

    assert len(PdfReader(BytesIO(pdf_com_override)).pages) == len(PdfReader(BytesIO(pdf_sem_override)).pages)
