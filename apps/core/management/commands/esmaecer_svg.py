from argparse import ArgumentParser
from pathlib import Path
from typing import cast

from django.core.management.base import BaseCommand

from services.utils.pdf.utils import EsmaecerSvgInput, esmaecer_svg


class Command(BaseCommand):
    help = "Clareia um SVG no lugar, para uso como marca d'água."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("caminho", type=Path)
        parser.add_argument("--forca", type=float, default=0.93)

    def handle(self, *args: object, **options: object) -> None:
        resultado = esmaecer_svg(
            EsmaecerSvgInput(
                caminho=cast(Path, options["caminho"]),
                forca=cast(float, options["forca"]),
            )
        )
        self.stdout.write(
            self.style.SUCCESS(f"{resultado.cores_clareadas} cores clareadas em {resultado.caminho}.")
        )
