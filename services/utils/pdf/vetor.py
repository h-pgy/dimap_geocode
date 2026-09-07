from pathlib import Path
from typing import BinaryIO

from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import mm
from svglib.svglib import svg2rlg


class CarregarVetor:
    """Callable: SVG → Drawing do reportlab, na largura pedida. Vetor de ponta a ponta: nada é
    rasterizado."""

    # ALTERADO nesta SPEC: a origem passa a ser caminho OU SVG em memória. O símbolo do QR nasce em
    # bytes; gravar um temporário só para reabri-lo seria IO a cada documento emitido e uma pasta a
    # limpar.
    def __call__(self, origem: Path | BinaryIO, largura_mm: float) -> Drawing:
        desenho = svg2rlg(str(origem) if isinstance(origem, Path) else origem)
        if desenho is None:
            raise ValueError(f"SVG inválido ou ilegível: {origem}")
        fator = (largura_mm * mm) / desenho.width
        desenho.width *= fator
        desenho.height *= fator
        desenho.scale(fator, fator)
        return desenho


carregar_vetor = CarregarVetor()
