import random
import smtplib
import ssl
import time
from collections.abc import Callable
from email.headerregistry import Address
from email.message import EmailMessage

from .exceptions import SmtpAutenticacaoError, SmtpEnvioError
from .models import MensagemEmail, ResultadoEnvio, SmtpConfig, SmtpRetryPolicy

# Falha de rede: a conexão nem chegou a servir. Repetir é a resposta certa.
FALHAS_TRANSITORIAS = (
    smtplib.SMTPConnectError,
    smtplib.SMTPServerDisconnected,
    smtplib.SMTPHeloError,
    OSError,  # timeout de socket e recusa de conexão entram por aqui
)


class EnviadorSmtp:
    """Callable: recebe uma mensagem, devolve o que o servidor respondeu sobre ela."""

    def __init__(
        self,
        config: SmtpConfig,
        policy: SmtpRetryPolicy,
        *,
        # Injetável para o teste trocar o cliente real por um fake — sem rede na suíte.
        cliente_factory: Callable[[], smtplib.SMTP] | None = None,
    ) -> None:
        self._config = config
        self._policy = policy
        self._cliente_factory = cliente_factory or self._abrir_cliente

    def __call__(self, mensagem: MensagemEmail) -> ResultadoEnvio:
        return self.pipeline(mensagem)

    def pipeline(self, mensagem: MensagemEmail) -> ResultadoEnvio:
        mime = self._montar_mime(mensagem)
        if not self._config.envio_habilitado:
            print(f"[SMTP desligado] para={mensagem.destinatarios} assunto={mensagem.assunto}")
            return ResultadoEnvio(entregue_ao_servidor=False)
        return self._entregar(mime)

    def _montar_mime(self, mensagem: MensagemEmail) -> EmailMessage:
        mime = EmailMessage()
        # Address monta o "Nome <conta@dominio>" com o escape correto — nada de f-string.
        mime["From"] = Address(
            display_name=self._config.remetente_nome,
            addr_spec=str(self._config.usuario),
        )
        mime["To"] = ", ".join(mensagem.destinatarios)
        mime["Subject"] = mensagem.assunto
        mime.set_content(mensagem.corpo_texto)
        if mensagem.corpo_html is not None:
            # add_alternative mantém o texto como primeira parte: cliente sem HTML lê ele.
            mime.add_alternative(mensagem.corpo_html, subtype="html")
        return mime

    def _entregar(self, mime: EmailMessage) -> ResultadoEnvio:
        for tentativa in range(self._policy.max_retries + 1):  # range FINITO → sem loop infinito
            resultado = self._tentar(mime, tentativa)
            if resultado is not None:
                return resultado
        raise AssertionError("laço de retry terminou sem retornar nem levantar")

    def _tentar(self, mime: EmailMessage, tentativa: int) -> ResultadoEnvio | None:
        """O resultado, ou None quando ainda há tentativa; esgotado, levanta."""
        try:
            # Conexão NOVA a cada tentativa, e não uma guardada no __init__: as falhas que a
            # política repete (SMTPConnectError, SMTPServerDisconnected) deixam o cliente morto,
            # e o Gmail derruba conexão ociosa antes do próximo envio.
            with self._cliente_factory() as cliente:
                cliente.starttls(context=ssl.create_default_context())
                cliente.login(self._config.usuario, self._config.senha.get_secret_value())
                # send_message devolve só os destinatários RECUSADOS; os demais foram aceitos.
                recusados = cliente.send_message(mime)
        except smtplib.SMTPAuthenticationError as exc:  # antes do genérico: 5xx que retry não conserta
            raise SmtpAutenticacaoError(f"conta {self._config.usuario} recusada") from exc
        except smtplib.SMTPRecipientsRefused as exc:
            # Todos recusados: é resposta do servidor sobre os endereços, não falha de envio.
            return ResultadoEnvio(
                entregue_ao_servidor=False,
                destinatarios_recusados=tuple(exc.recipients),
            )
        except (smtplib.SMTPException, OSError) as exc:
            if not self._e_transitoria(exc):
                raise SmtpEnvioError(f"falha definitiva em {self._config.host}: {exc!r}") from exc
            self._esperar_ou_desistir(repr(exc), tentativa, exc)
            return None
        return ResultadoEnvio(
            entregue_ao_servidor=True,
            destinatarios_recusados=tuple(recusados),
        )

    def _e_transitoria(self, exc: Exception) -> bool:
        if isinstance(exc, smtplib.SMTPResponseException):
            return 400 <= exc.smtp_code < 500  # 4xx é recusa temporária no protocolo SMTP
        return isinstance(exc, FALHAS_TRANSITORIAS)

    def _esperar_ou_desistir(self, motivo: str, tentativa: int, causa: Exception) -> None:
        total = self._policy.max_retries + 1
        if tentativa >= self._policy.max_retries:
            raise SmtpEnvioError(f"{self._config.host}: {motivo} após {total} tentativas") from causa
        time.sleep(
            random.uniform(
                self._policy.retry_wait_min_seconds,
                self._policy.retry_wait_max_seconds,
            )
        )

    def _abrir_cliente(self) -> smtplib.SMTP:
        return smtplib.SMTP(
            self._config.host,
            self._config.porta,
            timeout=self._policy.request_timeout_seconds,
        )
