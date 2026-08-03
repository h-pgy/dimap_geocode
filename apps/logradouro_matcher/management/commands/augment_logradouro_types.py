from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from services.scripts.augment_tipos_logradouro import AugmentConfig, AugmentStats, run


class Command(BaseCommand):
    help = (
        "Expande o dicionário de tipos de logradouro com variações por "
        "erros de digitação (vizinhança QWERTY ABNT2) e salva em parquet."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        config = AugmentConfig()
        stats: AugmentStats = run(config, verbose=bool(options["verbose"]))

        for tipo in stats.tipos_nao_mapeados:
            self.stdout.write(
                self.style.WARNING(
                    f"AVISO: tipo '{tipo}' presente em nomes_logradouros.parquet "
                    f"mas ausente no dicionário de mapeamento."
                )
            )

        if stats.variacoes_por_tipo is not None:
            for tipo, contagem in sorted(stats.variacoes_por_tipo.items()):
                self.stdout.write(f"  {tipo}: {contagem} variações")

        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído. "
                f"Entradas originais: {stats.n_original} | "
                f"Variações geradas: {stats.n_variacoes} | "
                f"Total no parquet: {stats.n_total}"
            )
        )
