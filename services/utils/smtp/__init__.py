from .config import SmtpSettingsLike, build_smtp_config, build_smtp_retry_policy
from .enviador import EnviadorSmtp
from .exceptions import SmtpAutenticacaoError, SmtpEnvioError
from .models import MensagemEmail, ResultadoEnvio, SmtpConfig, SmtpRetryPolicy

__all__ = [
    "EnviadorSmtp",
    "SmtpAutenticacaoError",
    "SmtpEnvioError",
    "MensagemEmail",
    "ResultadoEnvio",
    "SmtpConfig",
    "SmtpRetryPolicy",
    "SmtpSettingsLike",
    "build_smtp_config",
    "build_smtp_retry_policy",
]
