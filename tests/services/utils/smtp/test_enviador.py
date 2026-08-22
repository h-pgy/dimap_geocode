import smtplib

import pytest
from unittest.mock import MagicMock, Mock

from services.utils.smtp import (
    EnviadorSmtp,
    MensagemEmail,
    SmtpAutenticacaoError,
    SmtpConfig,
    SmtpEnvioError,
    SmtpRetryPolicy,
)


def _config(**overrides: object) -> SmtpConfig:
    defaults: dict[str, object] = {
        "host": "smtp.gmail.com",
        "porta": 587,
        "usuario": "dimap.geocoder@gmail.com",
        "senha": "app-senha-secreta",
        "remetente_nome": "DIMAP GeoCoder",
        "envio_habilitado": True,
    }
    return SmtpConfig(**(defaults | overrides))


def _policy(**overrides: object) -> SmtpRetryPolicy:
    # Espera zero: o que se testa é quantas vezes repete, não quanto tempo dorme.
    defaults: dict[str, object] = {
        "max_retries": 2,
        "retry_wait_min_seconds": 0.0,
        "retry_wait_max_seconds": 0.0,
    }
    return SmtpRetryPolicy(**(defaults | overrides))


def _mensagem(**overrides: object) -> MensagemEmail:
    defaults: dict[str, object] = {
        "destinatarios": ("destinatario@example.com",),
        "assunto": "assunto de teste",
        "corpo_texto": "corpo em texto puro",
    }
    return MensagemEmail(**(defaults | overrides))


def _cliente_ok(recusados: dict[str, tuple[int, bytes]] | None = None) -> MagicMock:
    # Dublê de transporte: o `smtplib.SMTP` é ponto de composição do enviador (§7.1), então o
    # teste injeta a factory dele em vez de espionar o módulo por dentro.
    cliente = MagicMock()
    cliente.__enter__.return_value = cliente
    cliente.send_message.return_value = dict(recusados or {})
    return cliente


def _fabrica(*comportamentos: object) -> Mock:
    # Cada chamada consome um item da sequência: exceção levanta, MagicMock é devolvido.
    fabrica = Mock()
    fabrica.side_effect = list(comportamentos)
    return fabrica


# ---------------------------------------------------------------------------
# Montagem do MIME
# ---------------------------------------------------------------------------


def test_mensagem_carrega_remetente_com_nome_de_exibicao() -> None:
    enviador = EnviadorSmtp(_config(usuario="dimap.geocoder@gmail.com"), _policy())
    mensagem = _mensagem(
        destinatarios=("ana@example.com", "beto@example.com"),
        assunto="Sua senha temporária",
    )

    mime = enviador._montar_mime(mensagem)

    assert mime["From"] == "DIMAP GeoCoder <dimap.geocoder@gmail.com>"
    assert mime["To"] == "ana@example.com, beto@example.com"
    assert mime["Subject"] == "Sua senha temporária"


def test_corpo_html_vira_alternativa_do_texto() -> None:
    enviador = EnviadorSmtp(_config(), _policy())

    mime_com_html = enviador._montar_mime(
        _mensagem(corpo_texto="versão texto", corpo_html="<p>versão html</p>")
    )
    assert mime_com_html.get_content_type() == "multipart/alternative"
    partes = list(mime_com_html.iter_parts())
    assert [parte.get_content_type() for parte in partes] == ["text/plain", "text/html"]
    assert (
        mime_com_html.get_body(preferencelist=("plain",)).get_content().strip()
        == "versão texto"
    )

    mime_sem_html = enviador._montar_mime(_mensagem(corpo_texto="só texto"))
    assert mime_sem_html.get_content_type() == "text/plain"
    assert not mime_sem_html.is_multipart()


# ---------------------------------------------------------------------------
# Autenticação e entrega
# ---------------------------------------------------------------------------


def test_envio_autentica_antes_de_entregar() -> None:
    cliente = _cliente_ok()
    enviador = EnviadorSmtp(_config(), _policy(), cliente_factory=_fabrica(cliente))

    resultado = enviador(_mensagem())

    assert resultado.entregue_ao_servidor is True
    assert [chamada[0] for chamada in cliente.method_calls] == [
        "starttls",
        "login",
        "send_message",
    ]


def test_falha_de_autenticacao_nao_e_repetida() -> None:
    cliente = _cliente_ok()
    cliente.login.side_effect = smtplib.SMTPAuthenticationError(
        535, b"credenciais invalidas"
    )
    fabrica = _fabrica(cliente)
    enviador = EnviadorSmtp(_config(), _policy(), cliente_factory=fabrica)

    with pytest.raises(SmtpAutenticacaoError):
        enviador(_mensagem())

    assert fabrica.call_count == 1, (
        "falha de autenticação não é transitória: não repete"
    )


# ---------------------------------------------------------------------------
# Retry diante de falha transitória
# ---------------------------------------------------------------------------


def test_falha_transitoria_e_repetida_e_entrega_na_tentativa_seguinte() -> None:
    fabrica = _fabrica(
        ConnectionRefusedError("recusa 1"),
        ConnectionRefusedError("recusa 2"),
        _cliente_ok(),
    )
    enviador = EnviadorSmtp(_config(), _policy(max_retries=2), cliente_factory=fabrica)

    resultado = enviador(_mensagem())

    assert resultado.entregue_ao_servidor is True
    assert fabrica.call_count == 3


def test_tentativas_esgotadas_viram_excecao_do_projeto() -> None:
    policy = _policy(max_retries=2)
    fabrica = Mock(side_effect=ConnectionRefusedError("conexão sempre recusada"))
    enviador = EnviadorSmtp(_config(), policy, cliente_factory=fabrica)

    with pytest.raises(SmtpEnvioError):
        enviador(_mensagem())

    assert fabrica.call_count == policy.max_retries + 1


# ---------------------------------------------------------------------------
# Resultado do servidor
# ---------------------------------------------------------------------------


def test_destinatario_recusado_aparece_no_resultado() -> None:
    cliente = _cliente_ok(
        recusados={"terceiro@example.com": (550, b"caixa inexistente")}
    )
    enviador = EnviadorSmtp(_config(), _policy(), cliente_factory=_fabrica(cliente))
    mensagem = _mensagem(
        destinatarios=(
            "primeiro@example.com",
            "segundo@example.com",
            "terceiro@example.com",
        )
    )

    resultado = enviador(mensagem)

    assert resultado.entregue_ao_servidor is True
    assert resultado.destinatarios_recusados == ("terceiro@example.com",)


def test_envio_desligado_nao_abre_conexao(capsys: pytest.CaptureFixture[str]) -> None:
    fabrica = Mock()
    enviador = EnviadorSmtp(
        _config(envio_habilitado=False), _policy(), cliente_factory=fabrica
    )
    mensagem = _mensagem(assunto="notificação com envio desligado")

    resultado = enviador(mensagem)

    fabrica.assert_not_called()
    assert resultado.entregue_ao_servidor is False
    assert resultado.destinatarios_recusados == ()
    assert "notificação com envio desligado" in capsys.readouterr().out
