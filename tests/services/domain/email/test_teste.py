from datetime import datetime
from typing import Any

from services.domain.email import ASSUNTO, Destaque, EmailTesteInput, montar_email_teste


def _pedido(**overrides: Any) -> EmailTesteInput:
    defaults: dict[str, Any] = {
        "destinatario": "ana@example.com",
        "ambiente": "geocoder.dimap.local",
        "momento": datetime(2026, 8, 21, 14, 30, 5),
    }
    return EmailTesteInput(**(defaults | overrides))


# ---------------------------------------------------------------------------
# O conteúdo do e-mail de teste identifica o disparo
# ---------------------------------------------------------------------------


def test_conteudo_do_email_de_teste_diz_ambiente_e_momento() -> None:
    conteudo = montar_email_teste(_pedido())

    assert conteudo.assunto == ASSUNTO
    destaques = [bloco for bloco in conteudo.blocos if isinstance(bloco, Destaque)]
    assert len(destaques) == 1
    assert "geocoder.dimap.local" in destaques[0].valor
    assert "21/08/2026 14:30:05" in destaques[0].valor
