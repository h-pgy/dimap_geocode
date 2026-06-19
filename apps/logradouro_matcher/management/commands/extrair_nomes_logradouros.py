from argparse import ArgumentParser
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from services.integrations.wfs import WfsConnectionConfig, WfsRetryPolicy
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
        retry_policy = WfsRetryPolicy(
            request_timeout_seconds=settings.WFS_REQUEST_TIMEOUT_SECONDS,
            max_retries=settings.WFS_MAX_RETRIES,
            retry_wait_min_seconds=settings.WFS_RETRY_WAIT_MIN_SECONDS,
            retry_wait_max_seconds=settings.WFS_RETRY_WAIT_MAX_SECONDS,
        )
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
