class SmtpEnvioError(Exception):
    """Levantada quando a mensagem não pôde ser entregue ao servidor SMTP."""


class SmtpAutenticacaoError(SmtpEnvioError):
    """Levantada quando a conta/senha de app foi recusada — repetir não resolve."""
