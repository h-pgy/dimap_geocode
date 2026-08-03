from datetime import datetime
from time import sleep
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from services.utils.tempo import segundos_ate_proximo


class Command(BaseCommand):
    help = (
        "Roda indefinidamente: dorme até DTIME_ATUALIZACAO_ARQUIVOS e dispara "
        "o pipeline de atualização dos dados de data/."
    )

    def handle(self, *args: object, **options: object) -> None:
        horario = settings.DTIME_ATUALIZACAO_ARQUIVOS
        fuso = ZoneInfo(settings.TIME_ZONE)

        while True:
            espera = segundos_ate_proximo(horario, datetime.now(fuso))
            self.stdout.write(f"[daemon] próxima atualização em {espera / 3600:.1f}h")
            sleep(espera)

            try:
                call_command("atualizar_dados", automatico=True)
            except Exception as exc:
                # Falha do pipeline não derruba o daemon: reporta e segue agendado.
                self.stderr.write(f"[daemon] atualização falhou: {exc}")
