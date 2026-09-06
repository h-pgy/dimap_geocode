from django.core.management.base import BaseCommand

from apps.competencias.registro import REGISTRO
from apps.competencias.sync import sincronizar_acoes


class Command(BaseCommand):
    help = "Projeta o catálogo de ações em código na tabela `Acao`."

    def handle(self, *args: object, **options: object) -> None:
        contagem = sincronizar_acoes(REGISTRO)
        self.stdout.write(self.style.SUCCESS(f"Catálogo sincronizado: {contagem}"))
