from collections.abc import Callable

from services.utils.smtp import MensagemEmail

from .html import renderizar_html
from .models import ConteudoEmail
from .texto_puro import renderizar_texto_puro


class MontarMensagem:
    """Callable: ConteudoEmail → MensagemEmail, pronta para o EnviadorSmtp da SPEC 001."""

    def __init__(
        self,
        # Injetáveis para o teste trocar um renderizador; o default é a instância do módulo.
        html: Callable[[ConteudoEmail], str] | None = None,
        texto: Callable[[ConteudoEmail], str] | None = None,
    ) -> None:
        self._html = html or renderizar_html
        self._texto = texto or renderizar_texto_puro

    def __call__(self, conteudo: ConteudoEmail, destinatarios: tuple[str, ...]) -> MensagemEmail:
        return MensagemEmail(
            destinatarios=destinatarios,
            assunto=conteudo.assunto,
            corpo_texto=self._texto(conteudo),
            # O ValidadorHtml da SPEC 001 roda no field_validator de MensagemEmail: escritor
            # que produza marcação torta é pego aqui, não na caixa de quem recebe.
            corpo_html=self._html(conteudo),
        )


montar_mensagem = MontarMensagem()
