from typing import Any

import pytest
from pydantic import ValidationError

from services.domain.email import EmailAcessoInput, Otp, Tabela


def _tabela(**overrides: Any) -> Tabela:
    defaults: dict[str, Any] = {
        "cabecalho": ("Campo", "Valor"),
        "linhas": (("Ambiente", "producao"), ("Momento", "21/08/2026 14:30:05")),
    }
    return Tabela(**(defaults | overrides))


def _otp(**overrides: Any) -> Otp:
    defaults: dict[str, Any] = {"rotulo": "Senha temporária", "valor": "k7Qm-2af9"}
    return Otp(**(defaults | overrides))


def _pedido_acesso(**overrides: Any) -> EmailAcessoInput:
    defaults: dict[str, Any] = {
        "nome": "Ana Beatriz",
        "rf": "123.456-7",
        "destinatario": "ana@example.com",
        "senha_temporaria": "k7Qm-2af9",
        "url_acesso": "https://geocoder.dimap.local/entrar",
    }
    return EmailAcessoInput(**(defaults | overrides))


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


# ---------------------------------------------------------------------------
# Otp: o código não passa da largura fixa da caixa
# ---------------------------------------------------------------------------


def test_otp_recusa_codigo_alem_da_largura() -> None:
    with pytest.raises(ValidationError):
        _otp(valor="a" * 11)

    assert _otp(valor="a" * 10).valor == "a" * 10


# ---------------------------------------------------------------------------
# EmailAcessoInput: a senha não escapa por repr
# ---------------------------------------------------------------------------


def test_senha_nao_aparece_no_repr_do_pedido() -> None:
    pedido = _pedido_acesso(senha_temporaria="k7Qm-2af9")

    assert "k7Qm-2af9" not in repr(pedido)
    assert "k7Qm-2af9" not in str(pedido)
