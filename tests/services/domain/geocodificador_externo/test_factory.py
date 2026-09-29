from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from services.domain.geocodificador_externo import (
    PoliticaGeocodificacao,
    Precisao,
    Provedor,
    ProvedorDesconhecidoError,
    build_geocodificador_externo,
    build_politica,
)


def _settings(**definidos: object) -> SimpleNamespace:
    calados: dict[str, object] = {
        "GOOGLE_GEOCODING_TOKEN": SecretStr("chave"),
        "GEOCODIFICACAO_EXTERNA_PROVEDOR": None,
        "GEOCODIFICACAO_EXTERNA_IDIOMA": None,
        "GEOCODIFICACAO_EXTERNA_PAIS": None,
        "GEOCODIFICACAO_EXTERNA_UF": None,
        "GEOCODIFICACAO_EXTERNA_MUNICIPIO": None,
        "GEOCODIFICACAO_EXTERNA_PRECISAO_MINIMA": None,
    }
    return SimpleNamespace(**(calados | definidos))


# ---------------------------------------------------------------------------
# Política vinda do ambiente
# ---------------------------------------------------------------------------


def test_politica_do_ambiente_so_sobrepoe_o_definido() -> None:
    politica = build_politica(_settings(GEOCODIFICACAO_EXTERNA_PRECISAO_MINIMA="imovel"))

    assert politica == PoliticaGeocodificacao(precisao_minima=Precisao.IMOVEL)


# ---------------------------------------------------------------------------
# Escolha do provedor
# ---------------------------------------------------------------------------


def test_factory_escolhe_o_provedor_pelo_ambiente() -> None:
    padrao = build_geocodificador_externo(_settings())
    declarado = build_geocodificador_externo(_settings(GEOCODIFICACAO_EXTERNA_PROVEDOR="google"))

    assert padrao is not None
    assert padrao.provedor is Provedor.GOOGLE
    assert declarado is not None
    assert declarado.provedor is Provedor.GOOGLE
    with pytest.raises(ProvedorDesconhecidoError, match="google"):
        build_geocodificador_externo(_settings(GEOCODIFICACAO_EXTERNA_PROVEDOR="azure"))
