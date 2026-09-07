from pathlib import Path

from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import mm
from svglib.svglib import svg2rlg


class CarregarVetor:
    """Callable: caminho de SVG → Drawing do reportlab, na largura pedida. Vetor de ponta a ponta:
    nada é rasterizado."""

    def __call__(self, caminho: Path, largura_mm: float) -> Drawing:
        desenho = svg2rlg(str(caminho))
        if desenho is None:
            raise ValueError(f"SVG inválido ou ilegível: {caminho}")
        fator = (largura_mm * mm) / desenho.width
        desenho.width *= fator
        desenho.height *= fator
        desenho.scale(fator, fator)
        return desenho


carregar_vetor = CarregarVetor()
