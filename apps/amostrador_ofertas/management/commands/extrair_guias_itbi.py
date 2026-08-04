from argparse import ArgumentParser

from django.core.management.base import BaseCommand
from django.template.defaultfilters import pluralize

from services.scripts.itbi import EscopoCarga, ItbiConfig, ItbiResult, run

# Acima disto o relatório listaria vinte e um anos numa linha só, e a linha deixaria de ser lida.
LIMITE_ANOS_LISTADOS: int = 5


# Sem `settings`: URL do portal e retry são constantes do próprio script, e constante do script
# é default no `Config` (SPEC 006).
class Command(BaseCommand):
    help = "Baixa as planilhas de guias de ITBI pagas do portal da Fazenda e consolida em data/."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--verbose", action="store_true")
        parser.add_argument(
            "--automatico",
            action="store_true",
            help="uso interno do daemon: marca a execução como automática nos metadados.",
        )
        parser.add_argument(
            "--completo",
            action="store_true",
            help="rebaixa e reparseia TODOS os anos publicados; sem a flag, só o mais recente.",
        )

    def handle(self, *args: object, **options: object) -> None:
        escopo = EscopoCarga.COMPLETO if options["completo"] else EscopoCarga.RECENTE
        result = run(
            ItbiConfig(escopo=escopo),
            verbose=bool(options["verbose"]),
            manual=not options["automatico"],
        )
        self._relatar(result)
        self._detalhar(result)
        self._avisar(result)
        self.stdout.write(self.style.SUCCESS(f"Concluído. Arquivo final em {result.output_path}"))

    def _relatar(self, result: ItbiResult) -> None:
        """Uma linha por etapa, na ordem em que rodaram: é o que diz onde a carga passou."""
        publicados = result.coleta.anos_publicados
        encontrados = pluralize(len(publicados))
        self.stdout.write(
            f"Portal: {len(publicados)} arquivo{encontrados} encontrado{encontrados}"
            f" ({self._anos(publicados)})."
        )

        alvo = result.coleta.anos_alvo
        self.stdout.write(
            f"Escopo {result.escopo.value}: {len(alvo)} ano{pluralize(len(alvo))} para atualizar"
            f" ({self._anos(alvo)})."
        )

        baixados = result.coleta.anos_baixados
        self.stdout.write(
            f"Coleta: {len(baixados)} de {len(alvo)} baixado{pluralize(len(baixados))}."
        )

        parseados = result.parse.anos_parseados
        # O denominador do parse é o que ele achou em disco, não o que a coleta baixou: as duas
        # etapas leem inputs diferentes, e a soma com as falhas é o que ele de fato tentou.
        tentados = len(parseados) + len(result.parse.falhas_por_ano)
        self.stdout.write(
            f"Parse: {len(parseados)} de {tentados} parseado{pluralize(len(parseados))}."
        )

        no_parquet = result.consolidacao.anos_no_parquet
        self.stdout.write(
            f"Consolidação: {len(no_parquet)} ano{pluralize(len(no_parquet))} no parquet,"
            f" {self._milhar(result.consolidacao.total_records)} registros."
        )

    def _detalhar(self, result: ItbiResult) -> None:
        """A contagem por ano só existe com --verbose: sem isto, o script apura e ninguém vê."""
        if result.linhas_por_ano is None:
            return
        for ano, linhas in sorted(result.linhas_por_ano.items()):
            self.stdout.write(f"  {ano}: {self._milhar(linhas)} registros")

    def _avisar(self, result: ItbiResult) -> None:
        """Sucesso parcial é sucesso: sem isto, o log do daemon não denuncia ano que envelheceu,
        ano que o portal publica e a base não tem, nem etapa que caiu num ano só."""
        if result.anos_desatualizados:
            self.stdout.write(self.style.WARNING(f"desatualizados: {result.anos_desatualizados}"))
        if result.anos_ausentes:
            self.stdout.write(self.style.WARNING(f"ausentes: {result.anos_ausentes}"))
        for ano, erro in sorted(result.coleta.falhas_por_ano.items()):
            self.stdout.write(self.style.WARNING(f"coleta falhou em {ano}: {erro}"))
        for ano, erro in sorted(result.parse.falhas_por_ano.items()):
            self.stdout.write(self.style.WARNING(f"parse falhou em {ano}: {erro}"))

    def _anos(self, anos: list[int]) -> str:
        if not anos:
            return "nenhum"
        if len(anos) <= LIMITE_ANOS_LISTADOS:
            return ", ".join(str(ano) for ano in anos)
        return f"de {anos[0]} a {anos[-1]}"

    def _milhar(self, valor: int) -> str:
        return f"{valor:,}".replace(",", ".")
