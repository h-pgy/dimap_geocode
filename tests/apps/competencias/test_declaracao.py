"""Testes de apps/competencias/declaracao.py (SPEC autorizacao/001).

Cobre: RegistroAcoes (todas/por_slug) e declarar_acao (composição aninhada).
"""

from services.domain.autorizacao.contratos import Acao, VarianteIcone
from apps.competencias.declaracao import AcaoImplementada, RegistroAcoes, declarar_acao


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def _acao_implementada(
    slug: str = "search.exportar_csv",
    nome: str = "Exportar CSV",
    tooltip: str = "Exporta os resultados em CSV",
    url_name: str = "search:exportar_csv",
    partial: str = "_exportar_csv.html",
    variantes_icone: frozenset[VarianteIcone] = frozenset(),
) -> AcaoImplementada:
    return declarar_acao(
        slug=slug,
        nome=nome,
        tooltip=tooltip,
        url_name=url_name,
        partial=partial,
        variantes_icone=variantes_icone,
    )


# ---------------------------------------------------------------------------
# Consulta e enumeração de ações no registro
# ---------------------------------------------------------------------------


def test_registro_todas_devolve_as_acoes_inscritas() -> None:
    impl = _acao_implementada()
    registro = RegistroAcoes(acoes=(impl,))
    assert registro.todas() == (impl,)


def test_registro_por_slug_devolve_a_acao_correta() -> None:
    impl = _acao_implementada()
    registro = RegistroAcoes(acoes=(impl,))
    assert registro.por_slug("search.exportar_csv") == impl


def test_registro_por_slug_devolve_none_para_slug_inexistente() -> None:
    registro = RegistroAcoes(acoes=(_acao_implementada(),))
    assert registro.por_slug("nao.existe") is None


def test_registro_vazio_enumera_zero_acoes() -> None:
    registro = RegistroAcoes(acoes=())
    assert registro.todas() == ()


# ---------------------------------------------------------------------------
# Declaração e composição aninhada
# ---------------------------------------------------------------------------


def test_declarar_acao_compoe_contrato_aninhado() -> None:
    # declarar_acao achata a declaração no ponto de escrita; o contrato guarda aninhado.
    impl = _acao_implementada()
    assert isinstance(impl.acao, Acao)
    assert impl.acao.slug == "search.exportar_csv"
    assert impl.url_name == "search:exportar_csv"
