from argparse import ArgumentParser

from django.conf import settings
from django.core.management.base import BaseCommand

from services.integrations.wfs import build_connection_config, build_retry_policy
from services.scripts.enderecos_fiscais import EnderecosFiscaisRequest, run


class Command(BaseCommand):
    help = "Extrai endereços de porta do cadastro de lotes do WFS para data/enderecos_fiscais.parquet."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        config = build_connection_config(settings)
        retry_policy = build_retry_policy(settings)
        request = EnderecosFiscaisRequest(
            layer_name=settings.WFS_LAYER_LOTE_CIDADAO,
        )
        result = run(config, request, retry_policy=retry_policy, verbose=bool(options["verbose"]))
        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído. {result.total_records} registros salvos em {result.output_path}"
            )
        )
