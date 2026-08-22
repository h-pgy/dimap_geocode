from argparse import ArgumentParser

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from services.domain.email import EmailTesteInput, montar_email_teste, montar_mensagem
from services.utils.smtp import EnviadorSmtp, ResultadoEnvio, build_smtp_config, build_smtp_retry_policy


class Command(BaseCommand):
    help = "Envia um e-mail de teste para o endereço informado, provando a configuração de SMTP."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("destinatario", type=str)

    def handle(self, *args: object, **options: object) -> None:
        # EmailStr valida aqui: endereço torto morre antes de qualquer conexão.
        pedido = EmailTesteInput(
            destinatario=str(options["destinatario"]),
            ambiente=settings.ALLOWED_HOSTS[0],
            momento=timezone.now(),
        )
        conteudo = montar_email_teste(pedido)
        mensagem = montar_mensagem(conteudo, destinatarios=(pedido.destinatario,))
        enviador = EnviadorSmtp(build_smtp_config(settings), build_smtp_retry_policy(settings))
        resultado = enviador(mensagem)
        self.stdout.write(self._desfecho(resultado, pedido.destinatario))

    def _desfecho(self, resultado: ResultadoEnvio, destinatario: str) -> str:
        # A ORDEM importa: recusa total devolve entregue_ao_servidor=False COM a lista de
        # recusados. Perguntar por "entregue" primeiro faria uma recusa ser relatada como
        # "envio desligado" — o desfecho mais enganoso possível para quem está testando.
        if resultado.destinatarios_recusados:
            recusados = ", ".join(resultado.destinatarios_recusados)
            return self.style.ERROR(f"Recusado pelo servidor: {recusados}")
        if not resultado.entregue_ao_servidor:
            return self.style.WARNING(
                "Envio desligado (EMAIL_ENVIO_HABILITADO=0): a mensagem foi montada e impressa, "
                f"mas nada foi enviado a {destinatario}."
            )
        return self.style.SUCCESS(f"Entregue ao servidor SMTP para {destinatario}.")
