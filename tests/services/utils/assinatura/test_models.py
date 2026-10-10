import pytest
from pydantic import SecretStr, ValidationError

from services.utils.assinatura import SelarInput


# ---------------------------------------------------------------------------
# Chave reservada do mecanismo não vem nos dados
# ---------------------------------------------------------------------------


def test_dados_com_chave_reservada_sao_recusados() -> None:
    with pytest.raises(ValidationError):
        SelarInput(
            pdf=b"%PDF-1.4",
            dados={"tag": "o que o chamador acha que e a tag"},
            segredo=SecretStr("segredo-de-teste"),
            id_chave="v1",
        )
