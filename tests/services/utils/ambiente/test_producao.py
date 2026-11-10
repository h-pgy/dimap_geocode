import pytest
from pydantic import SecretStr

from services.utils.ambiente import AmbienteProducaoInput, checar_ambiente_producao

SEGREDO_FORTE = "a1B2c3D4e5" * 6
SENHA_BANCO_FORTE = "S3nh4-F0rte-do-Banco"


def _ambiente_producao(**overrides: object) -> AmbienteProducaoInput:
    seguro: dict[str, object] = {
        "debug": False,
        "secret_key": SecretStr(SEGREDO_FORTE),
        "assinatura_segredo": SecretStr(SEGREDO_FORTE[::-1]),
        "postgres_password": SecretStr(SENHA_BANCO_FORTE),
        "allowed_hosts": ["geocoder.exemplo.gov.br"],
        "csrf_trusted_origins": ["https://geocoder.exemplo.gov.br"],
        "email_envio_habilitado": True,
        "enforce_prefeitura_email": True,
    }
    return AmbienteProducaoInput.model_validate(seguro | overrides)


def _variaveis_violadas(ambiente: AmbienteProducaoInput) -> list[str]:
    return [violacao.variavel for violacao in checar_ambiente_producao(ambiente).violacoes]


# ---------------------------------------------------------------------------
# Ambiente seguro
# ---------------------------------------------------------------------------


def test_ambiente_seguro_nao_tem_violacao() -> None:
    assert _variaveis_violadas(_ambiente_producao()) == []


# ---------------------------------------------------------------------------
# Configurações perigosas
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "variavel"),
    [
        ({"debug": True}, "DJANGO_DEBUG"),
        ({"secret_key": SecretStr("dev-insecure-secret-key-change-me")}, "DJANGO_SECRET_KEY"),
        (
            {"assinatura_segredo": SecretStr("dev-insecure-assinatura-secret-troque-me")},
            "ASSINATURA_SEGREDO",
        ),
        ({"postgres_password": SecretStr("dimap")}, "POSTGRES_PASSWORD"),
        ({"allowed_hosts": ["*"]}, "DJANGO_ALLOWED_HOSTS"),
        ({"csrf_trusted_origins": ["https://*.ngrok-free.app"]}, "DJANGO_CSRF_TRUSTED_ORIGINS"),
        ({"csrf_trusted_origins": ["http://geocoder.exemplo.gov.br"]}, "DJANGO_CSRF_TRUSTED_ORIGINS"),
        ({"email_envio_habilitado": False}, "EMAIL_ENVIO_HABILITADO"),
        ({"enforce_prefeitura_email": False}, "ENFORCE_PREFEITURA_EMAIL"),
    ],
)
def test_cada_configuracao_perigosa_vira_violacao_da_sua_variavel(
    overrides: dict[str, object],
    variavel: str,
) -> None:
    assert _variaveis_violadas(_ambiente_producao(**overrides)) == [variavel]


def test_segredo_longo_e_repetitivo_e_fraco() -> None:
    ambiente = _ambiente_producao(secret_key=SecretStr("a" * 60))

    assert _variaveis_violadas(ambiente) == ["DJANGO_SECRET_KEY"]


def test_defaults_de_dev_sao_recusados_de_uma_vez() -> None:
    ambiente = _ambiente_producao(
        debug=True,
        secret_key=SecretStr("dev-insecure-secret-key-change-me"),
        assinatura_segredo=SecretStr("dev-insecure-assinatura-secret-troque-me"),
        postgres_password=SecretStr("dimap"),
        allowed_hosts=["*"],
        csrf_trusted_origins=["https://*.ngrok-free.app", "https://*.ngrok.app"],
        email_envio_habilitado=False,
    )

    assert sorted(_variaveis_violadas(ambiente)) == [
        "ASSINATURA_SEGREDO",
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "DJANGO_DEBUG",
        "DJANGO_SECRET_KEY",
        "EMAIL_ENVIO_HABILITADO",
        "POSTGRES_PASSWORD",
    ]
