from typing import Any

import pytest
from pydantic import ValidationError

from services.domain.email import Tabela


def _tabela(**overrides: Any) -> Tabela:
    defaults: dict[str, Any] = {
        "cabecalho": ("Campo", "Valor"),
        "linhas": (("Ambiente", "producao"), ("Momento", "21/08/2026 14:30:05")),
    }
    return Tabela(**(defaults | overrides))


# ---------------------------------------------------------------------------
# Forma da tabela: toda linha tem a largura das colunas
# ---------------------------------------------------------------------------


def test_tabela_recusa_linha_de_largura_diferente() -> None:
    with pytest.raises(ValidationError):
        _tabela(linhas=(("Ambiente", "producao"), ("Momento",)))

    with pytest.raises(ValidationError):
        _tabela(linhas=(("Ambiente", "producao", "sobra"),))

    # Sem cabeçalho, quem fixa a largura é a primeira linha.
    with pytest.raises(ValidationError):
        _tabela(cabecalho=(), linhas=(("Ambiente", "producao"), ("Momento",)))

    assert _tabela(cabecalho=(), linhas=(("Ambiente",), ("Momento",))).linhas[1] == (
        "Momento",
    )
