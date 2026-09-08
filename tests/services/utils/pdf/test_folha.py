import re
from io import BytesIO

import pytest
from pypdf import PdfReader
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from services.utils.pdf.folha import Folha
from services.utils.pdf.models import A4, EstiloTraco, Orientacao

PADRAO_RETANGULO = re.compile(rb"([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) re S")
PADRAO_COR_TRACO = re.compile(rb"([\d.]+) ([\d.]+) ([\d.]+) RG")
PADRAO_ESPESSURA = re.compile(rb"([\d.]+) w")


def _pintar(estilo: EstiloTraco) -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer)
    tamanho = A4.orientar(Orientacao.RETRATO)
    folha = Folha(canvas, tamanho, pagina=1, total=1)

    folha.retangulo(10.0, 20.0, 50.0, 30.0, estilo)

    canvas.showPage()
    canvas.save()
    fluxo = PdfReader(BytesIO(buffer.getvalue())).pages[0].get_contents()
    assert fluxo is not None
    return fluxo.get_data()


# ---------------------------------------------------------------------------
# O contorno traça no eixo do topo, com a cor, a espessura e sem preenchimento
# ---------------------------------------------------------------------------


def test_retangulo_traca_no_eixo_do_topo_com_espessura_declarada() -> None:
    estilo = EstiloTraco(cor=HexColor("#336633"), espessura_mm=0.5)
    tamanho = A4.orientar(Orientacao.RETRATO)

    conteudo = _pintar(estilo)

    retangulo = PADRAO_RETANGULO.search(conteudo)
    assert retangulo is not None
    x_pt, y_pt, largura_pt, altura_pt = (float(valor) for valor in retangulo.groups())
    # y_mm é o TOPO: o reportlab recebe o canto inferior, altura*mm abaixo do que a inversão dá.
    assert x_pt == pytest.approx(10.0 * mm, abs=0.01)
    assert y_pt == pytest.approx((tamanho.altura_mm - 20.0 - 30.0) * mm, abs=0.01)
    assert largura_pt == pytest.approx(50.0 * mm, abs=0.01)
    assert altura_pt == pytest.approx(30.0 * mm, abs=0.01)

    cor = PADRAO_COR_TRACO.search(conteudo)
    assert cor is not None
    r, g, b = (float(valor) for valor in cor.groups())
    assert (r, g, b) == pytest.approx((0x33 / 255, 0x66 / 255, 0x33 / 255), abs=0.01)

    espessura = PADRAO_ESPESSURA.search(conteudo)
    assert espessura is not None
    assert float(espessura.group(1)) == pytest.approx(0.5 * mm, abs=0.01)

    # O operador é `S` — contorna sem preencher; `PADRAO_RETANGULO` já exige exatamente isso.
