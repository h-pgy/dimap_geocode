from argparse import ArgumentParser
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from services.integrations.wfs import WfsConnectionConfig
from services.scripts.logradouros import NomesLogradourosRequest, run


class Command(BaseCommand):
    help = "Extrai codlog/tipo/nome únicos de logradouros do WFS e salva em data/nomes_logradouros.parquet."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        config = WfsConnectionConfig(
            domain=settings.WFS_DOMAIN,
            endpoint=settings.WFS_ENDPOINT,
            namespace=settings.WFS_NAMESPACE,
            service=settings.WFS_SERVICE,
            version=settings.WFS_VERSION,
        )
        request = NomesLogradourosRequest(
            layer_name=settings.WFS_LAYER_LOGRADOUROS,
            data_folder=Path(settings.BASE_DIR) / "data",
        )
        result = run(config, request, verbose=bool(options["verbose"]))
        self.stdout.write(
            self.style.SUCCESS(
                f"{result.total_unique} logradouros únicos salvos em {result.output_path}"
            )
        )
