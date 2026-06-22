from django.core.management.base import BaseCommand

from services.scripts.augment_tipos_logradouro import AugmentStats, run


class Command(BaseCommand):
    help = (
        "Expande o dicionário de tipos de logradouro com variações por "
        "erros de digitação (vizinhança QWERTY ABNT2) e salva em parquet."
    )

    def handle(self, *args: object, **options: object) -> None:
        stats: AugmentStats = run()

        for tipo in stats.tipos_nao_mapeados:
            self.stdout.write(
                self.style.WARNING(
                    f"AVISO: tipo '{tipo}' presente em nomes_logradouros.parquet "
                    f"mas ausente no dicionário de mapeamento."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído. "
                f"Entradas originais: {stats.n_original} | "
                f"Variações geradas: {stats.n_variacoes} | "
                f"Total no parquet: {stats.n_total}"
            )
        )
