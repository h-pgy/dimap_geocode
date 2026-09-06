import pytest
from pydantic import ValidationError

from services.utils.smtp import MensagemEmail


def _mensagem(**overrides: object) -> MensagemEmail:
    defaults: dict[str, object] = {
        "destinatarios": ("destinatario@example.com",),
        "assunto": "assunto de teste",
        "corpo_texto": "corpo em texto puro",
    }
    return MensagemEmail(**(defaults | overrides))


# ---------------------------------------------------------------------------
# Fronteira do corpo HTML: validação na construção da mensagem
# ---------------------------------------------------------------------------


def test_html_malformado_recusa_a_mensagem() -> None:
    with pytest.raises(ValidationError) as tag_nao_fechada:
        _mensagem(corpo_html="<p>parágrafo sem fechamento")
    assert "<p>" in str(tag_nao_fechada.value)

    with pytest.raises(ValidationError) as fechamento_sem_abertura:
        _mensagem(corpo_html="<p>texto</p></div>")
    assert "div" in str(fechamento_sem_abertura.value)

    with pytest.raises(ValidationError) as fechamento_fora_de_ordem:
        _mensagem(corpo_html="<b><i>texto</b></i>")
    # a mensagem carrega a tag do erro e a linha em que a tag violada foi aberta.
    assert "<b>" in str(fechamento_fora_de_ordem.value)
    assert "linha 1" in str(fechamento_fora_de_ordem.value)
