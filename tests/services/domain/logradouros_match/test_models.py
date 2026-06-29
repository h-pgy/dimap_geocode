import pytest

from services.domain.logradouros_match import LogradouroMatchOutput, LogradouroMatchQuery, LogradouroMatchResult
from services.utils.fuzzy_matcher import FuzzyMatchResult, FuzzyMatchItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fuzzy_result(query: str = "q", best: str = "B", score: float = 95.0) -> FuzzyMatchResult:
    return FuzzyMatchResult(
        original_query=query,
        cleaned_query=query.upper(),
        algorithm_used="jaro_winkler",
        requested_limit=5,
        matches=[
            FuzzyMatchItem(original_string=best, cleaned_string=best, similarity_score=score, rank_position=1)
        ],
    )


def _make_match(codlog: str = "000001", tipo: str = "AV", nome: str = "PAULISTA") -> LogradouroMatchOutput:
    return LogradouroMatchOutput(codlog=codlog, tipo_codigo=tipo, nome_logradouro=nome)


# ---------------------------------------------------------------------------
# LogradouroMatchQuery
# ---------------------------------------------------------------------------


def test_query_guarda_texto() -> None:
    q = LogradouroMatchQuery(texto="avenida paulista")
    assert q.texto == "avenida paulista"


def test_query_limite_default_e_5() -> None:
    q = LogradouroMatchQuery(texto="x")
    assert q.limite == 5


def test_query_limite_customizavel() -> None:
    q = LogradouroMatchQuery(texto="x", limite=10)
    assert q.limite == 10


# ---------------------------------------------------------------------------
# LogradouroMatchResult — computed fields e properties
# ---------------------------------------------------------------------------


def test_resultado_multiplo_false_com_um_item() -> None:
    result = LogradouroMatchResult(
        match_tipo=None,
        match_nome=_make_fuzzy_result(),
        logradouros=[_make_match()],
        ignorou_filtro_tipo=False,
    )
    assert result.resultado_multiplo is False


def test_resultado_multiplo_true_com_dois_itens() -> None:
    result = LogradouroMatchResult(
        match_tipo=None,
        match_nome=_make_fuzzy_result(),
        logradouros=[_make_match("000001"), _make_match("000002")],
        ignorou_filtro_tipo=False,
    )
    assert result.resultado_multiplo is True


def test_resultado_multiplo_false_com_lista_vazia() -> None:
    result = LogradouroMatchResult(
        match_tipo=None,
        match_nome=_make_fuzzy_result(),
        logradouros=[],
        ignorou_filtro_tipo=False,
    )
    assert result.resultado_multiplo is False


def test_codlogs_retorna_todos_os_codlogs() -> None:
    result = LogradouroMatchResult(
        match_tipo=None,
        match_nome=_make_fuzzy_result(),
        logradouros=[_make_match("AAA"), _make_match("BBB")],
        ignorou_filtro_tipo=False,
    )
    assert result.codlogs == ["AAA", "BBB"]


def test_codlogs_vazio_quando_sem_logradouros() -> None:
    result = LogradouroMatchResult(
        match_tipo=None,
        match_nome=_make_fuzzy_result(),
        logradouros=[],
        ignorou_filtro_tipo=False,
    )
    assert result.codlogs == []


def test_nome_logradouro_retorna_best_match_string() -> None:
    result = LogradouroMatchResult(
        match_tipo=None,
        match_nome=_make_fuzzy_result(best="PAULISTA"),
        logradouros=[],
        ignorou_filtro_tipo=False,
    )
    assert result.nome_logradouro == "PAULISTA"


def test_nome_logradouro_none_quando_sem_matches() -> None:
    match_sem_resultado = FuzzyMatchResult(
        original_query="x",
        cleaned_query="X",
        algorithm_used="jaro_winkler",
        requested_limit=5,
        matches=[],
    )
    result = LogradouroMatchResult(
        match_tipo=None,
        match_nome=match_sem_resultado,
        logradouros=[],
        ignorou_filtro_tipo=False,
    )
    assert result.nome_logradouro is None


def test_match_tipo_pode_ser_none() -> None:
    result = LogradouroMatchResult(
        match_tipo=None,
        match_nome=_make_fuzzy_result(),
        logradouros=[],
        ignorou_filtro_tipo=False,
    )
    assert result.match_tipo is None


def test_ignorou_filtro_tipo_preservado() -> None:
    result = LogradouroMatchResult(
        match_tipo=_make_fuzzy_result(),
        match_nome=_make_fuzzy_result(),
        logradouros=[],
        ignorou_filtro_tipo=True,
    )
    assert result.ignorou_filtro_tipo is True
