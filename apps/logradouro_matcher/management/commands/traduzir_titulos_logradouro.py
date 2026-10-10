from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from services.scripts.traducao_titulos_logradouro import (
    TraducaoTitulosConfig,
    TraducaoTitulosStats,
    run,
)


class Command(BaseCommand):
    help = (
        "Leva o dicionário de títulos de logradouro (sigla → extenso) ao catálogo em parquet, "
        "com o extenso normalizado."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--verbose", action="store_true")
        parser.add_argument(
            "--automatico",
            action="store_true",
            help="uso interno do daemon: marca a execução como automática nos metadados.",
        )

    def handle(self, *args: object, **options: object) -> None:
        config = TraducaoTitulosConfig()
        stats: TraducaoTitulosStats = run(
            config,
            verbose=bool(options["verbose"]),
            manual=not options["automatico"],
        )

        for sigla in stats.siglas_sem_extenso:
            self.stdout.write(
                self.style.WARNING(
                    f"AVISO: título '{sigla}' presente em nomes_logradouros.parquet "
                    f"mas ausente no dicionário de títulos."
                )
            )

        self.stdout.write(self.style.SUCCESS(f"Concluído. Títulos no parquet: {stats.n_titulos}"))
