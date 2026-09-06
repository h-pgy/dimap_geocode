"""Testes de apps/competencias/schemas.py (SPEC autorizacao/001).

Cobre: RegistroAcoes (todas/por_slug).
"""

from services.domain.autorizacao.contratos import VarianteIcone
from apps.competencias.schemas import AcaoImplementada, RegistroAcoes
from apps.competencias.utils import instanciar_acao


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def _acao_implementada(
    slug: str = "search.exportar_csv",
    nome: str = "Exportar CSV",
    tooltip: str = "Exporta os resultados em CSV",
    url_name: str = "search:exportar_csv",
    variantes_icone: frozenset[VarianteIcone] = frozenset(),
) -> AcaoImplementada:
    return instanciar_acao(
        slug=slug,
        nome=nome,
        tooltip=tooltip,
        url_name=url_name,
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
