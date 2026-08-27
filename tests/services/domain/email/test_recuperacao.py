"""
Testes de services/domain/email/recuperacao.py (SPEC autenticacao/003): o que a mensagem de
recuperação de senha diz — o link, o uso único, o prazo e a instrução de ignorar quem não pediu.
"""

from typing import Any

from services.domain.email import (
    ASSUNTO_RECUPERACAO,
    Botao,
    EmailRecuperacaoInput,
    Paragrafo,
    montar_email_recuperacao,
)


def _pedido(**overrides: Any) -> EmailRecuperacaoInput:
    defaults: dict[str, Any] = {
        "nome": "Fulana da Silva",
        "destinatario": "fulana@prefeitura.sp.gov.br",
        "url_recuperacao": "https://geocoder.dimap.local/recuperar-senha/abc/def/",
        "validade_horas": 1,
    }
    return EmailRecuperacaoInput(**(defaults | overrides))


# ---------------------------------------------------------------------------
# O conteúdo do e-mail de recuperação diz uso único, prazo e como ignorar
# ---------------------------------------------------------------------------


def test_email_de_recuperacao_diz_uso_unico_prazo_e_como_ignorar() -> None:
    conteudo = montar_email_recuperacao(_pedido(validade_horas=2))

    assert conteudo.assunto == ASSUNTO_RECUPERACAO

    botao = next(bloco for bloco in conteudo.blocos if isinstance(bloco, Botao))
    assert str(botao.url) == "https://geocoder.dimap.local/recuperar-senha/abc/def/"

    paragrafos = " ".join(bloco.texto for bloco in conteudo.blocos if isinstance(bloco, Paragrafo))
    assert "uso único" in paragrafos
    assert "2 hora(s)" in paragrafos
    assert "ignore esta mensagem" in paragrafos
