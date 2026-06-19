from argparse import ArgumentParser

from django.conf import settings
from django.core.management.base import BaseCommand

from services.integrations.wfs import WfsConnectionConfig
from services.scripts.enderecos_fiscais import EnderecosFiscaisRequest, run


class Command(BaseCommand):
    help = "Extrai endereços de porta do cadastro de lotes do WFS para data/enderecos_fiscais.parquet."

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
        request = EnderecosFiscaisRequest(
            layer_name=settings.WFS_LAYER_LOTE_CIDADAO,
        )
        result = run(config, request, verbose=bool(options["verbose"]))
        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído. {result.total_records} registros salvos em {result.output_path}"
            )
        )
