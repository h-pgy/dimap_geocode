"""
O envio de e-mail que qualquer ato administrativo compõe (SPEC autenticacao/003 e 004): antes,
privado do cadastro de servidor — a mesma conversa com o SMTP serve à recuperação de senha e ao
reenvio da senha de uso único sem duplicar a guarda de `EMAIL_ENVIO_HABILITADO`.
"""

from django.conf import settings

from services.domain.email import EmailAcessoInput, montar_email_acesso, montar_mensagem
from services.utils.smtp import (
    EnviadorSmtp,
    MensagemEmail,
    SmtpEnvioError,
    build_smtp_config,
    build_smtp_retry_policy,
)


def entregar_email(mensagem: MensagemEmail) -> bool:
    """True quando a mensagem foi de fato entregue ao SMTP; False quando o envio está desligado por
    configuração — que não é falha. Destinatário recusado e servidor fora do ar são o mesmo desfecho
    para quem chamou: a mensagem não chegou, e vira exceção."""
    if not settings.EMAIL_ENVIO_HABILITADO:
        print(
            f"[SMTP desligado] para={mensagem.destinatarios} assunto={mensagem.assunto}"
        )
        return False
    enviador = EnviadorSmtp(
        build_smtp_config(settings), build_smtp_retry_policy(settings)
    )
    resultado = enviador(mensagem)
    if resultado.destinatarios_recusados:
        raise SmtpEnvioError(f"Destinatário recusado: {mensagem.destinatarios}.")
    return True


def entregar_email_de_acesso(pedido: EmailAcessoInput) -> bool:
    """True quando a mensagem foi de fato entregue ao SMTP; False quando o envio está desligado por
    configuração."""
    conteudo = montar_email_acesso(pedido)
    return entregar_email(
        montar_mensagem(conteudo, destinatarios=(pedido.destinatario,))
    )
