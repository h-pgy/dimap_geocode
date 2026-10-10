from types import SimpleNamespace

from pydantic import SecretStr

from services.integrations.geocodificador_externo import google


def test_build_sem_token_nao_monta_cliente() -> None:
    assert google.build_cliente(SimpleNamespace(GOOGLE_GEOCODING_TOKEN=SecretStr(""))) is None
    assert google.build_cliente(SimpleNamespace(GOOGLE_GEOCODING_TOKEN=SecretStr("chave"))) is not None
