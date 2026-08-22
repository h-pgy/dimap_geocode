from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command
from pydantic import ValidationError
from pytest_django.fixtures import SettingsWrapper

from apps.users.management.commands import enviar_email_teste as comando
from services.utils.smtp import MensagemEmail, ResultadoEnvio


class EnviadorFake:
    """Substitui o `EnviadorSmtp`: guarda a mensagem e devolve o desfecho combinado."""

    def __init__(self, resultado: ResultadoEnvio) -> None:
        self.resultado = resultado
        self.mensagens: list[MensagemEmail] = []

    def __call__(self, mensagem: MensagemEmail) -> ResultadoEnvio:
        self.mensagens.append(mensagem)
        return self.resultado


def _resultado(**overrides: Any) -> ResultadoEnvio:
    defaults: dict[str, Any] = {
        "entregue_ao_servidor": True,
        "destinatarios_recusados": (),
    }
    return ResultadoEnvio(**(defaults | overrides))


def _configurar(settings: SettingsWrapper) -> None:
    settings.ALLOWED_HOSTS = ["geocoder.dimap.local"]
    settings.EMAIL_SMTP_USUARIO = "dimap.geocoder@example.com"


def _rodar(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
    resultado: ResultadoEnvio,
    destinatario: str = "ana@example.com",
) -> tuple[str, EnviadorFake]:
    _configurar(settings)
    enviador = EnviadorFake(resultado)
    monkeypatch.setattr(comando, "EnviadorSmtp", lambda *args: enviador)
    saida = StringIO()
    call_command("enviar_email_teste", destinatario, stdout=saida)
    return saida.getvalue(), enviador


# ---------------------------------------------------------------------------
# Validação do argumento, antes de qualquer conexão
# ---------------------------------------------------------------------------


def test_comando_recusa_endereco_invalido(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    _configurar(settings)
    instanciados: list[object] = []
    monkeypatch.setattr(
        comando, "EnviadorSmtp", lambda *args: instanciados.append(args)
    )

    with pytest.raises(ValidationError):
        call_command("enviar_email_teste", "endereco-sem-arroba")

    assert instanciados == []


# ---------------------------------------------------------------------------
# O desfecho do envio no stdout
# ---------------------------------------------------------------------------


def test_comando_relata_o_desfecho_do_envio(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    entregue, enviador = _rodar(monkeypatch, settings, _resultado())
    assert enviador.mensagens[0].destinatarios == ("ana@example.com",)
    assert "Entregue" in entregue
    assert "ana@example.com" in entregue

    recusado, _ = _rodar(
        monkeypatch,
        settings,
        _resultado(
            entregue_ao_servidor=False, destinatarios_recusados=("ana@example.com",)
        ),
    )
    assert "Recusado" in recusado

    desligado, _ = _rodar(monkeypatch, settings, _resultado(entregue_ao_servidor=False))
    assert "desligado" in desligado.lower()
    assert "Entregue" not in desligado
