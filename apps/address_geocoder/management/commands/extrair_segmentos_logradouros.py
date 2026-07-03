from argparse import ArgumentParser

from django.conf import settings
from django.core.management.base import BaseCommand

from services.integrations.wfs import build_connection_config, build_retry_policy
from services.scripts.segmentos_logradouros import SegmentosLogradourosRequest, run


class Command(BaseCommand):
    help = "Extrai identificadores e intervalos de numeração de segmentos viários do WFS para data/segmentos_logradouros.parquet."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        config = build_connection_config(settings)
        retry_policy = build_retry_policy(settings)
        request = SegmentosLogradourosRequest(
            layer_name=settings.WFS_LAYER_LOGRADOUROS,
        )
        result = run(config, request, retry_policy=retry_policy, verbose=bool(options["verbose"]))
        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído. {result.total_segments} segmentos salvos em {result.output_path}"
            )
        )
