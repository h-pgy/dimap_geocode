from io import StringIO
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from pydantic import SecretStr

SEGREDO_DJANGO_DEV = "dev-insecure-secret-key-change-me"
SEGREDO_ASSINATURA_DEV = "dev-insecure-assinatura-secret-troque-me"
SENHA_BANCO_DEV = "dimap"

AMBIENTE_INSEGURO: dict[str, object] = {
    "DEBUG": True,
    "SECRET_KEY": SEGREDO_DJANGO_DEV,
    "ASSINATURA_SEGREDO": SecretStr(SEGREDO_ASSINATURA_DEV),
    "ALLOWED_HOSTS": ["*"],
    "CSRF_TRUSTED_ORIGINS": ["https://*.ngrok-free.app"],
    "EMAIL_ENVIO_HABILITADO": False,
    "ENFORCE_PREFEITURA_EMAIL": False,
}


def _checar(prod: bool) -> str:
    saida = StringIO()
    with (
        override_settings(PROD=prod, **AMBIENTE_INSEGURO),
        patch.dict(settings.DATABASES["default"], {"PASSWORD": SENHA_BANCO_DEV}),
    ):
        call_command("checar_ambiente_producao", stdout=saida)
    return saida.getvalue()


# ---------------------------------------------------------------------------
# PROD desligado
# ---------------------------------------------------------------------------


def test_comando_com_prod_desligado_nao_checa() -> None:
    assert "pulada" in _checar(prod=False)


# ---------------------------------------------------------------------------
# PROD ligado
# ---------------------------------------------------------------------------


def test_comando_com_prod_ligado_e_ambiente_inseguro_aborta_listando_tudo() -> None:
    with pytest.raises(CommandError) as erro:
        _checar(prod=True)

    mensagem = str(erro.value)
    for variavel in (
        "DJANGO_DEBUG",
        "DJANGO_SECRET_KEY",
        "ASSINATURA_SEGREDO",
        "POSTGRES_PASSWORD",
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "EMAIL_ENVIO_HABILITADO",
        "ENFORCE_PREFEITURA_EMAIL",
    ):
        assert f"- {variavel}:" in mensagem


def test_erro_do_comando_nao_exibe_valor_de_segredo() -> None:
    with pytest.raises(CommandError) as erro:
        _checar(prod=True)

    mensagem = str(erro.value)
    assert SEGREDO_DJANGO_DEV not in mensagem
    assert SEGREDO_ASSINATURA_DEV not in mensagem
    assert SENHA_BANCO_DEV not in mensagem
