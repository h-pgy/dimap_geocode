from io import BytesIO

from reportlab.pdfgen.canvas import Canvas

from services.utils.extracao_texto import OrigemTexto, TextoExtraido
from services.utils.extracao_texto.extrator_pdf import ExtratorPdf

FRASE = "Certidao de lancamento do imposto predial e territorial urbano"


class OcrFalso:
    def __init__(self) -> None:
        self.chamadas = 0

    def __call__(self, conteudo: bytes) -> TextoExtraido:
        self.chamadas += 1
        return TextoExtraido(conteudo=FRASE, origem=OrigemTexto.OCR)

    def conferir(self, conteudo: bytes) -> OrigemTexto:
        self.chamadas += 1
        return OrigemTexto.OCR


def _pdf_digital() -> bytes:
    saida = BytesIO()
    canvas = Canvas(saida)
    canvas.drawString(72, 720, FRASE)
    canvas.save()
    return saida.getvalue()


def test_pdf_digital_usa_camada_de_texto() -> None:
    ocr = OcrFalso()
    extrator = ExtratorPdf(ocr=ocr)

    texto = extrator(_pdf_digital())

    assert texto.origem is OrigemTexto.CAMADA_DE_TEXTO
    assert FRASE in texto.conteudo
    assert ocr.chamadas == 0
