from typing import Protocol

from pydantic import SecretStr

from .models import SmtpConfig, SmtpRetryPolicy


class SmtpSettingsLike(Protocol):
    EMAIL_SMTP_HOST: str
    EMAIL_SMTP_PORTA: int
    EMAIL_SMTP_USUARIO: str
    EMAIL_SMTP_SENHA: str
    EMAIL_REMETENTE_NOME: str
    EMAIL_ENVIO_HABILITADO: bool
    EMAIL_SMTP_TIMEOUT_SECONDS: float
    EMAIL_SMTP_MAX_RETRIES: int
    EMAIL_SMTP_RETRY_WAIT_MIN_SECONDS: float
    EMAIL_SMTP_RETRY_WAIT_MAX_SECONDS: float


def build_smtp_config(source: SmtpSettingsLike) -> SmtpConfig:
    return SmtpConfig(
        host=source.EMAIL_SMTP_HOST,
        porta=source.EMAIL_SMTP_PORTA,
        usuario=source.EMAIL_SMTP_USUARIO,
        senha=SecretStr(source.EMAIL_SMTP_SENHA),
        remetente_nome=source.EMAIL_REMETENTE_NOME,
        envio_habilitado=source.EMAIL_ENVIO_HABILITADO,
    )


def build_smtp_retry_policy(source: SmtpSettingsLike) -> SmtpRetryPolicy:
    return SmtpRetryPolicy(
        request_timeout_seconds=source.EMAIL_SMTP_TIMEOUT_SECONDS,
        max_retries=source.EMAIL_SMTP_MAX_RETRIES,
        retry_wait_min_seconds=source.EMAIL_SMTP_RETRY_WAIT_MIN_SECONDS,
        retry_wait_max_seconds=source.EMAIL_SMTP_RETRY_WAIT_MAX_SECONDS,
    )
