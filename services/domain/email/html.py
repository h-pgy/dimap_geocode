from collections.abc import Callable, Mapping
from html import escape
from typing import Any

from .escritores import ESCRITORES
from .models import BlocoEmail, ConteudoEmail
from .tema import TEMA_EMAIL


class RenderizadorEmailHtml:
    """Callable: ConteudoEmail → o HTML inteiro do e-mail."""

    def __init__(self, escritores: Mapping[str, Callable[[Any], str]] | None = None) -> None:
        self._escritores = dict(escritores or ESCRITORES)

    def __call__(self, conteudo: ConteudoEmail) -> str:
        return self.pipeline(conteudo)

    def pipeline(self, conteudo: ConteudoEmail) -> str:
        corpo = "".join(self._escrever(bloco) for bloco in conteudo.blocos)
        return self._envelopar(corpo, conteudo.rodape)

    def _escrever(self, bloco: BlocoEmail) -> str:
        # Bloco sem escritor levanta KeyError na montagem — onde há teste e stack trace —,
        # e não como buraco silencioso na caixa de quem recebe.
        return self._escritores[bloco.tipo](bloco)  # type: ignore[attr-defined]

    def _envelopar(self, corpo: str, rodape: str) -> str:
        # Largura e alinhamento como ATRIBUTO de tabela, não CSS: é o que sobrevive em qualquer
        # cliente. Aninhamento de tabela no lugar de flex, pelo mesmo motivo.
        return (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="{TEMA_EMAIL["fundo"]}"><tr><td align="center">'
            f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
            f'style="{TEMA_EMAIL["placa"]}">'
            f'<tr><td style="{TEMA_EMAIL["faixa"]}">{self._marca()}</td></tr>'
            f'<tr><td style="{TEMA_EMAIL["corpo"]}">{corpo}</td></tr>'
            f'<tr><td style="{TEMA_EMAIL["rodape"]}">{escape(rodape)}</td></tr>'
            "</table></td></tr></table>"
        )

    def _marca(self) -> str:
        # Tabela de duas células, e não inline-block: alinhamento vertical confiável no Outlook.
        return (
            '<table role="presentation" cellpadding="0" cellspacing="0"><tr>'
            f'<td width="32" style="{TEMA_EMAIL["marca_selo"]}">D</td>'
            f'<td style="{TEMA_EMAIL["marca_nome"]}">DIMAP GeoCoder</td>'
            "</tr></table>"
        )


# Instância única: o renderizador não guarda estado, e o registro de escritores é o default.
renderizar_html = RenderizadorEmailHtml()
