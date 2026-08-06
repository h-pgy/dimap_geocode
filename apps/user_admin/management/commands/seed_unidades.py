from argparse import ArgumentParser

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.user_admin.seeds import carregar_seed_unidades


class Command(BaseCommand):
    help = "Carrega tipos de unidade e unidades a partir de data/seed/unidades.json."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="valida a carga completa sem persistir nada.",
        )

    def handle(self, *args: object, **options: object) -> None:
        dry_run = bool(options["dry_run"])
        try:
            resultado = carregar_seed_unidades(dry_run=dry_run)
        # ObjectDoesNotExist cobre sigla de pai e tipo ausentes; ValidationError cobre o clean().
        except (ObjectDoesNotExist, ValidationError) as exc:
            raise CommandError(f"carga abortada: {exc}") from exc
        prefixo = "dry-run ok" if dry_run else "carga concluída"
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefixo}: {resultado.tipos} tipos e {resultado.unidades} unidades."
            )
        )
