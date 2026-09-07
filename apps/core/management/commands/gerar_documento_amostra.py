from argparse import ArgumentParser
from pathlib import Path
from typing import cast

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from services.domain.documento_oficial import (
    DocumentoAmostraInput,
    RenderizarDocumentoInput,
    RenderizarDocumentoOficial,
    build_marcacao_config,
    build_tema_config,
    marcacao_fazenda_dimap,
    montar_documento_amostra,
    montar_tema,
)
from services.utils.io import escrever_atomico


class Command(BaseCommand):
    help = "Grava um PDF de amostra com todos os blocos e a marcação oficial da SF."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("caminho", type=Path)

    def handle(self, *args: object, **options: object) -> None:
        conteudo = montar_documento_amostra(
            DocumentoAmostraInput(ambiente=settings.ALLOWED_HOSTS[0], momento=timezone.now())
        )
        # A orquestração é o único ponto que toca `settings`, e é ela que escolhe o papel
        # timbrado; o domínio recebe tema e config prontos.
        tema = montar_tema(build_tema_config(settings))
        marcacao = marcacao_fazenda_dimap(build_marcacao_config(settings), tema)
        renderizado = RenderizarDocumentoOficial(tema)(
            RenderizarDocumentoInput(conteudo=conteudo, marcacao=marcacao)
        )

        caminho = cast(Path, options["caminho"])
        escrever_atomico(caminho, lambda tmp: tmp.write_bytes(renderizado.pdf))
        self.stdout.write(self.style.SUCCESS(f"Amostra gravada em {caminho}."))
