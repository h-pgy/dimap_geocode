import pytest

from config.settings import _Settings, _parse_lista_env


# ---------------------------------------------------------------------------
# Parse resiliente de variáveis de ambiente tipo lista
# ---------------------------------------------------------------------------


def test_parse_lista_virgula_com_espacos() -> None:
    resultado = _parse_lista_env("localhost, 127.0.0.1, dimap.sp.gov.br")
    assert resultado == ["localhost", "127.0.0.1", "dimap.sp.gov.br"]


def test_parse_lista_separada_por_espaco() -> None:
    resultado = _parse_lista_env("localhost 127.0.0.1 0.0.0.0")
    assert resultado == ["localhost", "127.0.0.1", "0.0.0.0"]


def test_parse_lista_ponto_e_virgula_e_quebra_de_linha() -> None:
    resultado = _parse_lista_env("localhost; 127.0.0.1\n0.0.0.0")
    assert resultado == ["localhost", "127.0.0.1", "0.0.0.0"]


def test_parse_lista_formato_json() -> None:
    resultado = _parse_lista_env('["localhost", "127.0.0.1"]')
    assert resultado == ["localhost", "127.0.0.1"]


def test_parse_lista_formato_python_com_aspas_simples() -> None:
    resultado = _parse_lista_env("['localhost', '127.0.0.1']")
    assert resultado == ["localhost", "127.0.0.1"]


def test_parse_lista_limpa_aspas_residuais() -> None:
    resultado = _parse_lista_env('"localhost", "127.0.0.1"')
    assert resultado == ["localhost", "127.0.0.1"]


def test_parse_lista_descarta_itens_vazios() -> None:
    resultado = _parse_lista_env(",  , localhost, ")
    assert resultado == ["localhost"]


def test_parse_lista_aceita_lista_nativa() -> None:
    resultado = _parse_lista_env(["localhost", " 127.0.0.1 "])
    assert resultado == ["localhost", "127.0.0.1"]


# ---------------------------------------------------------------------------
# Integração com _Settings (Pydantic / Variáveis de Ambiente)
# ---------------------------------------------------------------------------


def test_settings_allowed_hosts_com_espaco(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "localhost 127.0.0.1")
    settings = _Settings()
    assert settings.allowed_hosts == ["localhost", "127.0.0.1"]


def test_settings_csrf_trusted_origins_com_virgula_e_espaco(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "https://a.sp.gov.br, https://b.sp.gov.br",
    )
    settings = _Settings()
    assert settings.csrf_trusted_origins == [
        "https://a.sp.gov.br",
        "https://b.sp.gov.br",
    ]
