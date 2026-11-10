from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from pydantic import SecretStr

from services.utils.ambiente import AmbienteProducaoInput, checar_ambiente_producao


class Command(BaseCommand):
    help = "Com PROD ligado, recusa o ambiente que tenha configuração perigosa para produção."

    def handle(self, *args: object, **options: object) -> None:
        if not settings.PROD:
            self.stdout.write("PROD desligado: checagem do ambiente de produção pulada.")
            return
        resultado = checar_ambiente_producao(
            AmbienteProducaoInput(
                debug=settings.DEBUG,
                secret_key=SecretStr(settings.SECRET_KEY),
                assinatura_segredo=settings.ASSINATURA_SEGREDO,
                postgres_password=SecretStr(str(settings.DATABASES["default"]["PASSWORD"])),
                allowed_hosts=settings.ALLOWED_HOSTS,
                csrf_trusted_origins=settings.CSRF_TRUSTED_ORIGINS,
                email_envio_habilitado=settings.EMAIL_ENVIO_HABILITADO,
                enforce_prefeitura_email=settings.ENFORCE_PREFEITURA_EMAIL,
            )
        )
        if resultado.violacoes:
            linhas = "\n".join(f"  - {v.variavel}: {v.motivo}" for v in resultado.violacoes)
            raise CommandError(f"ambiente de produção inseguro, deploy abortado:\n{linhas}")
        self.stdout.write(self.style.SUCCESS("Ambiente de produção conferido."))
