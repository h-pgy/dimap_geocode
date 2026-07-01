from argparse import ArgumentParser
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from services.integrations.wfs import build_connection_config, build_retry_policy
from services.scripts.logradouros import NomesLogradourosRequest, run


class Command(BaseCommand):
    help = "Extrai codlog/tipo/nome únicos de logradouros do WFS e salva em data/nomes_logradouros.parquet."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        config = build_connection_config(settings)
        retry_policy = build_retry_policy(settings)
        request = NomesLogradourosRequest(
            layer_name=settings.WFS_LAYER_LOGRADOUROS,
            data_folder=Path(settings.BASE_DIR) / "data",
        )
        result = run(config, request, retry_policy=retry_policy, verbose=bool(options["verbose"]))
        self.stdout.write(
            self.style.SUCCESS(
                f"{result.total_unique} logradouros únicos salvos em {result.output_path}"
            )
        )
