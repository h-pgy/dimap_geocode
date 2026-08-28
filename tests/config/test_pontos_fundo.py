"""Testes de config/pontos_fundo.py (SPEC design/010): a validação de fronteira do catálogo de
pontos que enquadram cada ortofoto de fundo — coordenada fora do município e catálogo vazio.
"""

import pytest
from pydantic import ValidationError

from config.pontos_fundo import CatalogoPontosFundo, PontoFundo


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _ponto(**overrides: object) -> dict[str, object]:
    defaults: dict[str, object] = {
        "descricao": "Praça da Sé — Centro",
        "lat": -23.5505,
        "lng": -46.6333,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Validação de fronteira
# ---------------------------------------------------------------------------


def test_ponto_fora_do_municipio_e_recusado() -> None:
    with pytest.raises(ValidationError):
        PontoFundo(**_ponto(descricao="Rio de Janeiro", lat=-22.9068, lng=-43.1729))


def test_catalogo_vazio_e_recusado() -> None:
    with pytest.raises(ValidationError):
        CatalogoPontosFundo.model_validate({})
