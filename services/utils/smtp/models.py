from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from services.utils.html import validar_html


class SmtpRetryPolicy(BaseModel):
    """O que o consumidor declara; o laço que a obedece é do `EnviadorSmtp`."""

    model_config = ConfigDict(frozen=True)

    request_timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_wait_min_seconds: float = 1.0
    retry_wait_max_seconds: float = 5.0


class SmtpConfig(BaseModel):
    """A conta que envia. Nasce na orquestração (settings) e é injetada no enviador."""

    model_config = ConfigDict(frozen=True)

    host: str
    porta: int
    usuario: EmailStr
    # SecretStr para a senha de app não aparecer em repr, log nem traceback.
    senha: SecretStr
    # O Gmail força o From na conta autenticada; só o nome de exibição é livre.
    remetente_nome: str
    # Desligado, o enviador registra a mensagem no stdout e não abre conexão.
    envio_habilitado: bool = True


class MensagemEmail(BaseModel):
    """O que se quer entregar. Sem remetente: quem envia é a conta do `SmtpConfig`.
    `corpo_html` passa pelo validador na construção — a regra está no §6."""

    model_config = ConfigDict(frozen=True)

    destinatarios: tuple[EmailStr, ...] = Field(min_length=1)
    assunto: str
    corpo_texto: str
    # Presente, vira alternativa HTML do mesmo corpo — nunca substitui o texto.
    corpo_html: str | None = None

    @field_validator("corpo_html")
    @classmethod
    def _html_bem_formado(cls, valor: str | None) -> str | None:
        if valor is None:
            return valor
        resultado = validar_html(valor)
        if not resultado.valido:
            raise ValueError("; ".join(erro.mensagem for erro in resultado.erros))
        return valor


class ResultadoEnvio(BaseModel):
    """O que o servidor respondeu. Aceitação do SMTP não é entrega ao destinatário."""

    model_config = ConfigDict(frozen=True)

    entregue_ao_servidor: bool
    destinatarios_recusados: tuple[str, ...] = ()
