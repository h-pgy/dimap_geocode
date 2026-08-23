"""Testes de apps/competencias/catalogo.py (SPEC autorizacao/007): o que o modal de atribuir
oferece a uma unidade.

Marker `banco`: a oferta é a diferença entre a tabela de ações e as atribuições já gravadas.
"""

import pytest

from apps.competencias.catalogo import acoes_oferecidas
from apps.competencias.models import Acao, AtribuicaoUnidade
from apps.unidades.models import TipoUnidade, Unidade

banco = pytest.mark.banco


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _unidade(sigla: str) -> Unidade:
    tipo = TipoUnidade.objects.create(
        nome=f"Tipo {sigla}",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )
    return Unidade.objects.create(nome=f"Unidade {sigla}", sigla=sigla, tipo=tipo)


def _acao(slug: str, **overrides: object) -> Acao:
    dados: dict[str, object] = {"nome": f"Ação {slug}", "tooltip": "tt", "ativa": True}
    dados.update(overrides)
    return Acao.objects.create(slug=slug, **dados)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# O que o catálogo oferece
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_catalogo_oferece_so_o_que_falta() -> None:
    unidade = _unidade("CAT-UNIDADE")
    ja_atribuida = _acao("competencias.cat_ja_atribuida")
    AtribuicaoUnidade.objects.create(unidade=unidade, acao=ja_atribuida)
    inativa = _acao("competencias.cat_inativa", ativa=False)
    # A estrutural entra como qualquer outra: sem a atribuição não há o que conceder depois.
    estrutural = _acao("competencias.cat_estrutural", estrutural=True)
    disponivel = _acao("competencias.cat_disponivel")

    oferecidas = set(acoes_oferecidas(unidade))

    assert oferecidas == {estrutural, disponivel}
    assert ja_atribuida not in oferecidas
    assert inativa not in oferecidas


@banco
@pytest.mark.django_db
def test_atribuicao_de_outra_unidade_nao_tira_a_acao_da_oferta() -> None:
    """A oferta é por unidade: a ação que a vizinha já exerce continua disponível aqui."""
    unidade = _unidade("CAT-DESTA")
    vizinha = _unidade("CAT-VIZINHA")
    acao = _acao("competencias.cat_da_vizinha")
    AtribuicaoUnidade.objects.create(unidade=vizinha, acao=acao)

    assert acao in set(acoes_oferecidas(unidade))
