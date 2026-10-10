from io import BytesIO
from typing import cast

from pypdf import PdfReader
from pypdf.generic import DictionaryObject, IndirectObject
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.pdfgen.canvas import Canvas

from services.utils.pdf import VetorNomeado, desenhar_forma


def _desenho() -> Drawing:
    desenho = Drawing(20, 10)
    desenho.add(Rect(0, 0, 20, 10, fillColor="#336633"))
    return desenho


def _pdf(vetor: VetorNomeado, posicoes_por_pagina: tuple[int, ...]) -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer)
    for quantidade in posicoes_por_pagina:
        for indice in range(quantidade):
            desenhar_forma(canvas, vetor, 10.0 * indice, 10.0)
        canvas.showPage()
    canvas.save()
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# O mesmo vetor, em posições e páginas diferentes, é UM Form referenciado
# ---------------------------------------------------------------------------


def test_mesmo_vetor_em_posicoes_diferentes_referencia_uma_forma_so() -> None:
    vetor = VetorNomeado(desenho=_desenho(), nome="simbolo")
    pdf_uma_posicao = _pdf(vetor, (1,))
    pdf_duas_posicoes_uma_pagina = _pdf(vetor, (2,))
    pdf_duas_paginas = _pdf(vetor, (1, 1))

    for pdf in (pdf_duas_posicoes_uma_pagina, pdf_duas_paginas):
        leitor = PdfReader(BytesIO(pdf))
        referencias = set()
        for pagina in leitor.pages:
            recursos = cast(DictionaryObject, pagina["/Resources"])
            xobjects = cast(DictionaryObject, recursos["/XObject"])
            forma_nome = next(nome for nome in xobjects if nome.endswith("simbolo"))
            forma = cast(IndirectObject, xobjects.raw_get(forma_nome))
            assert forma["/Subtype"] == "/Form"
            referencias.add((forma.idnum, forma.generation))
            # O símbolo é traço, não bitmap: a página não declara XObject de imagem.
            assert all(objeto["/Subtype"] != "/Image" for objeto in xobjects.values())
        # UM form escrito, referenciado em toda posição/página — não um por ocorrência.
        assert len(referencias) == 1

    # Referenciar de novo custa pouco (translate + doForm); reescrever o form dobraria o arquivo.
    assert len(pdf_duas_posicoes_uma_pagina) < len(pdf_uma_posicao) * 1.5
