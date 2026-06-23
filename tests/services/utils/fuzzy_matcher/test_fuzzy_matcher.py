import pytest

from services.utils.fuzzy_matcher import fuzzy_match


# ---------------------------------------------------------------------------
# Levenshtein — impacto da normalização e rastreabilidade
# ---------------------------------------------------------------------------


def test_levenshtein_ordena_av_paulista_em_primeiro() -> None:
    result = fuzzy_match("Avenida Paulista", ["AV PAULISTA", "RUA DIREITA"])
    assert result.best_match is not None
    assert result.best_match.original_string == "AV PAULISTA"


def test_levenshtein_rastreabilidade_query() -> None:
    result = fuzzy_match("Avenida Paulista", ["AV PAULISTA", "RUA DIREITA"])
    assert result.original_query == "Avenida Paulista"
    assert result.cleaned_query == "AVENIDA PAULISTA"


def test_levenshtein_rastreabilidade_item() -> None:
    result = fuzzy_match("Avenida Paulista", ["AV PAULISTA", "RUA DIREITA"])
    best = result.best_match
    assert best is not None
    assert best.original_string == "AV PAULISTA"
    assert best.cleaned_string == "AV PAULISTA"


# ---------------------------------------------------------------------------
# Jaro-Winkler — ordenação e rastreabilidade
# ---------------------------------------------------------------------------


def test_jaro_winkler_ordena_rua_direita_em_primeiro() -> None:
    result = fuzzy_match("Rua Direita", ["RUA DIREITA", "RUA ESQUERDA"], algorithm="jaro_winkler")
    assert result.best_match is not None
    assert result.best_match.original_string == "RUA DIREITA"


def test_jaro_winkler_rastreabilidade_query() -> None:
    result = fuzzy_match("Rua Direita", ["RUA DIREITA", "RUA ESQUERDA"], algorithm="jaro_winkler")
    assert result.original_query == "Rua Direita"
    assert result.cleaned_query == "RUA DIREITA"


def test_jaro_winkler_rastreabilidade_item() -> None:
    result = fuzzy_match("Rua Direita", ["RUA DIREITA", "RUA ESQUERDA"], algorithm="jaro_winkler")
    second = result.matches[1]
    assert second.original_string == "RUA ESQUERDA"
    assert second.cleaned_string == "RUA ESQUERDA"


# ---------------------------------------------------------------------------
# Exceções de algoritmo
# ---------------------------------------------------------------------------


def test_algoritmo_invalido_levanta_value_error() -> None:
    with pytest.raises(ValueError):
        fuzzy_match("x", ["y"], algorithm="invalid_algo")


def test_algoritmo_nao_implementado_levanta_not_implemented_error() -> None:
    with pytest.raises(NotImplementedError):
        fuzzy_match("x", ["y"], algorithm="hamming")
