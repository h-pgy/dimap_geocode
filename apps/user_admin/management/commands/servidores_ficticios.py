from argparse import ArgumentParser

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.user_admin.ficticios import (
    FAIXA_RF_FICTICIA,
    criar_servidores_ficticios,
    remover_servidores_ficticios,
)

DEBUG: bool = settings.DEBUG

ERRO_FORA_DE_DEBUG = "servidor fictício é andaime de desenvolvimento: recusado com DEBUG desligado."


class Command(BaseCommand):
    help = (
        "Cria (idempotente) ou remove os servidores fictícios da faixa de RF reservada "
        f"{FAIXA_RF_FICTICIA[0]}-{FAIXA_RF_FICTICIA[-1]}, para exercitar a listagem."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--remover",
            action="store_true",
            help="apaga a faixa de RF reservada, e só ela.",
        )

    def handle(self, *args: object, **options: object) -> None:
        # A recusa é do comando, não do módulo: é aqui que o ambiente entra na conversa.
        if not DEBUG:
            raise CommandError(ERRO_FORA_DE_DEBUG)
        if bool(options["remover"]):
            self._remover()
            return
        self._criar()

    def _criar(self) -> None:
        try:
            resultado = criar_servidores_ficticios()
        # Sem as seeds não há unidade, cargo nem tipo de impedimento em que distribuí-los.
        except (ObjectDoesNotExist, ValidationError) as exc:
            raise CommandError(f"carga abortada: {exc}") from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"{resultado.criados} servidores fictícios no banco: "
                f"{resultado.impedidos} impedidos, {resultado.com_comissao} em comissão."
            )
        )

    def _remover(self) -> None:
        resultado = remover_servidores_ficticios()
        self.stdout.write(
            self.style.SUCCESS(f"{resultado.removidos} servidores fictícios removidos.")
        )
