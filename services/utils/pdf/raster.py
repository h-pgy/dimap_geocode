from io import BytesIO

from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Flowable, Image


def imagem_raster(conteudo: bytes, largura_mm: float) -> Flowable:
    leitor = ImageReader(BytesIO(conteudo))
    largura_px, altura_px = leitor.getSize()
    return Image(
        BytesIO(conteudo),
        width=largura_mm * mm,
        height=largura_mm * mm * altura_px / largura_px,
    )
