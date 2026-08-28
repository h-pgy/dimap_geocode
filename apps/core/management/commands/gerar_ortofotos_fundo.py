from argparse import ArgumentParser

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from services.integrations.wms import WmsConnectionConfig, WmsError
from services.scripts.ortofotos_fundo import GeradorOrtofotosFundo
from services.scripts.ortofotos_fundo.contrato import OrtofotoConfig


class Command(BaseCommand):
    help = "Gera as ortofotos de fundo da área administrativa que ainda não estão em disco."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--forcar", action="store_true", help="rebusca mesmo o que já existe.")

    def handle(self, *args: object, **options: object) -> None:
        # Todo o parsing de settings acontece aqui: o script recebe um DTO pronto.
        config = OrtofotoConfig(
            pontos=settings.MAP_FUNDO_PONTOS,
            conexao=WmsConnectionConfig(
                vector_url=settings.WMS_URL,
                raster_url=settings.WMS_RASTER_URL,
                version=settings.WMS_VERSION,
                request_timeout_seconds=settings.WMS_REQUEST_TIMEOUT_SECONDS,
            ),
            destino=settings.MAP_FUNDO_DIR,
            camada=settings.WMS_LAYER_ORTOFOTO,
            metros_por_pixel=settings.MAP_FUNDO_METROS_POR_PIXEL,
            largura_px=settings.MAP_FUNDO_LARGURA_PX,
            altura_px=settings.MAP_FUNDO_ALTURA_PX,
            crs_entrada=settings.MAP_OUTPUT_CRS,
            crs_saida=settings.MAP_INTERPOLATION_CRS,
            forcar=bool(options["forcar"]),
        )
        try:
            resultado = GeradorOrtofotosFundo()(config)
        except WmsError as exc:  # inclui WmsTimeoutError
            raise CommandError(f"geração abortada: {exc}") from exc

        for chave in resultado.geradas:
            self.stdout.write(self.style.SUCCESS(f"[gerada] {chave}"))
        self.stdout.write(f"{len(resultado.puladas)} já em disco.")
