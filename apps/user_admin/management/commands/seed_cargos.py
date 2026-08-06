from argparse import ArgumentParser

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.user_admin.seeds import carregar_seed_cargos


class Command(BaseCommand):
    help = "Carrega cargos base e em comissão a partir de data/seed/cargos.json."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="valida a carga completa sem persistir nada.",
        )

    def handle(self, *args: object, **options: object) -> None:
        dry_run = bool(options["dry_run"])
        try:
            resultado = carregar_seed_cargos(dry_run=dry_run)
        except ValidationError as exc:
            raise CommandError(f"carga abortada: {exc}") from exc
        prefixo = "dry-run ok" if dry_run else "carga concluída"
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefixo}: {resultado.cargo_base} cargos base e "
                f"{resultado.cargo_comissao} cargos em comissão."
            )
        )
