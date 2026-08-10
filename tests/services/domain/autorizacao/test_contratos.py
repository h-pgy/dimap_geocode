"""Testes de services/domain/autorizacao/contratos.py (SPEC autorizacao/001).

Cobre: Acao recusa slug fora do padrão <app>.<nome>, nome vazio e tooltip vazio.
"""

import pytest
from pydantic import ValidationError

from services.domain.autorizacao.contratos import Acao, VarianteIcone


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def _acao(
    slug: str = "search.exportar_csv",
    nome: str = "Exportar CSV",
    tooltip: str = "Exporta os resultados em CSV",
    nome_curto: str | None = None,
    variantes_icone: frozenset[VarianteIcone] = frozenset(),
) -> Acao:
    return Acao(
        slug=slug,
        nome=nome,
        tooltip=tooltip,
        nome_curto=nome_curto,
        variantes_icone=variantes_icone,
    )


# ---------------------------------------------------------------------------
# Validação de formato de slug
# ---------------------------------------------------------------------------


def test_acao_slug_sem_ponto_e_invalido() -> None:
    with pytest.raises(ValidationError) as exc:
        _acao(slug="semnamespace")
    assert any("slug" in err["loc"] for err in exc.value.errors())


def test_acao_slug_com_mais_de_um_ponto_e_invalido() -> None:
    with pytest.raises(ValidationError) as exc:
        _acao(slug="a.b.c")
    assert any("slug" in err["loc"] for err in exc.value.errors())


def test_acao_slug_com_maiuscula_e_invalido() -> None:
    with pytest.raises(ValidationError) as exc:
        _acao(slug="Search.exportar")
    assert any("slug" in err["loc"] for err in exc.value.errors())


def test_acao_slug_iniciando_com_numero_e_invalido() -> None:
    with pytest.raises(ValidationError) as exc:
        _acao(slug="1app.acao")
    assert any("slug" in err["loc"] for err in exc.value.errors())


def test_acao_slug_valido_e_aceito() -> None:
    acao = _acao(slug="search.exportar_csv")
    assert acao.slug == "search.exportar_csv"


# ---------------------------------------------------------------------------
# Validação de campos obrigatórios
# ---------------------------------------------------------------------------


def test_acao_nome_vazio_e_invalido() -> None:
    with pytest.raises(ValidationError) as exc:
        _acao(nome="")
    assert any("nome" in err["loc"] for err in exc.value.errors())


def test_acao_tooltip_vazio_e_invalido() -> None:
    with pytest.raises(ValidationError) as exc:
        _acao(tooltip="")
    assert any("tooltip" in err["loc"] for err in exc.value.errors())


# ---------------------------------------------------------------------------
# Valores padrão e atributos opcionais
# ---------------------------------------------------------------------------


def test_acao_nome_curto_e_opcional() -> None:
    acao = _acao(nome_curto=None)
    assert acao.nome_curto is None


def test_acao_variantes_icone_default_e_frozenset_vazio() -> None:
    acao = _acao()
    assert acao.variantes_icone == frozenset()


def test_acao_aceita_variantes_icone() -> None:
    acao = _acao(
        variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    )
    assert VarianteIcone.PEQUENO in acao.variantes_icone
    assert VarianteIcone.GRANDE in acao.variantes_icone
