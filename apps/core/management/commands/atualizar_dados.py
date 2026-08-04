from argparse import ArgumentParser

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from services.scripts.pipeline import AtualizacaoConfig, PipelineAtualizacao

# Ordem do pipeline (§6.4: cargas → variações → cache). Quem conhece a ordem é o Django,
# porque é ele quem sabe que uma etapa é um management command.
ETAPAS: tuple[str, ...] = (
    "extrair_segmentos_logradouros",
    "extrair_nomes_logradouros",
    "extrair_enderecos_fiscais",
    "augment_logradouro_types",
    # Última: o pipeline aborta na primeira falha, e nenhuma etapa consome o parquet do ITBI.
    "extrair_guias_itbi",
)


class Command(BaseCommand):
    help = "Executa o pipeline completo de atualização dos parquets de data/, na ordem correta."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--automatico",
            action="store_true",
            help="uso interno do daemon: marca a execução como automática nos metadados.",
        )

    def handle(self, *args: object, **options: object) -> None:
        automatico = bool(options["automatico"])

        # Verbose é do contrato, não opção do usuário: rodando sem plateia, log mudo é log inútil.
        def executar(etapa: str) -> None:
            call_command(etapa, verbose=True, automatico=automatico)

        resultado = PipelineAtualizacao(executar)(AtualizacaoConfig(etapas=ETAPAS))

        for etapa in resultado.executadas:
            self.stdout.write(self.style.SUCCESS(f"[ok] {etapa}"))

        if resultado.falhou_em is not None:
            raise CommandError(f"pipeline abortou em {resultado.falhou_em}: {resultado.erro}")

        self.stdout.write(self.style.SUCCESS(f"Concluído. {len(ETAPAS)} etapas executadas."))
