from django.conf import settings
from django.core.management.base import BaseCommand

from services.integrations.wfs import WfsConnectionConfig
from services.scripts.segmentos_logradouros import SegmentosLogradourosRequest, run


class Command(BaseCommand):
    help = "Extrai identificadores e intervalos de numeração de segmentos viários do WFS para data/segmentos_logradouros.parquet."

    def add_arguments(self, parser: object) -> None:
        parser.add_argument("--verbose", action="store_true")  # type: ignore[union-attr]

    def handle(self, *args: object, **options: object) -> None:
        config = WfsConnectionConfig(
            domain=settings.WFS_DOMAIN,
            endpoint=settings.WFS_ENDPOINT,
            namespace=settings.WFS_NAMESPACE,
            service=settings.WFS_SERVICE,
            version=settings.WFS_VERSION,
        )
        request = SegmentosLogradourosRequest(
            layer_name=settings.WFS_LAYER_LOGRADOUROS,
        )
        result = run(config, request, verbose=bool(options["verbose"]))
        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído. {result.total_segments} segmentos salvos em {result.output_path}"
            )
        )
