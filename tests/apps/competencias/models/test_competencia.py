"""
Testes de `AtribuicaoUnidade` e `Concessao` (SPEC autorizacao/002): o XOR entre `cargo_base` e
`cargo_comissao`, a unicidade dos dois níveis (inclusive nos dois ramos do XOR, onde o FK nulo do
outro ramo poderia deixar a duplicata passar) e o CASCADE da atribuição sobre suas concessões.
"""

from django.db import IntegrityError, transaction

import pytest

from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao
from apps.user_admin.models import CargoBase, CargoComissao, TipoUnidade, Unidade

banco = pytest.mark.banco


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Teste",
        "nivel": 10,
        "pode_ser_raiz": True,
        "nivel_minimo_titular": 1,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(**overrides: object) -> Unidade:
    dados: dict[str, object] = {
        "nome": "Unidade Teste",
        "sigla": "UT",
        "tipo": _tipo_unidade(),
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _acao(**overrides: object) -> Acao:
    dados: dict[str, object] = {
        "slug": "competencias.teste",
        "nome": "Ação de Teste",
        "tooltip": "Tooltip de teste",
    }
    dados.update(overrides)
    return Acao.objects.create(**dados)  # type: ignore[arg-type]


def _atribuicao(**overrides: object) -> AtribuicaoUnidade:
    dados: dict[str, object] = {
        "unidade": _unidade(),
        "acao": _acao(),
    }
    dados.update(overrides)
    return AtribuicaoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base(**overrides: object) -> CargoBase:
    dados: dict[str, object] = {"nome": "Cargo Teste", "sigla": "CT"}
    dados.update(overrides)
    return CargoBase.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_comissao(**overrides: object) -> CargoComissao:
    dados: dict[str, object] = {
        "sigla": "CDA",
        "nivel": 1,
        "e_chefia": True,
        "alta_administracao": False,
        "nome": "Cargo Comissão Teste",
    }
    dados.update(overrides)
    return CargoComissao.objects.create(**dados)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# XOR entre cargo_base e cargo_comissao
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_concessao_exige_exatamente_um_cargo() -> None:
    atribuicao = _atribuicao()

    with transaction.atomic(), pytest.raises(IntegrityError):
        Concessao.objects.create(atribuicao=atribuicao)

    with transaction.atomic(), pytest.raises(IntegrityError):
        Concessao.objects.create(
            atribuicao=atribuicao,
            cargo_base=_cargo_base(),
            cargo_comissao=_cargo_comissao(),
        )


# ---------------------------------------------------------------------------
# CASCADE da atribuição sobre as concessões
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_remover_atribuicao_remove_concessoes() -> None:
    atribuicao = _atribuicao()
    concessao = Concessao.objects.create(
        atribuicao=atribuicao, cargo_base=_cargo_base()
    )

    atribuicao.delete()

    assert not Concessao.objects.filter(pk=concessao.pk).exists()


# ---------------------------------------------------------------------------
# Unicidade dos dois níveis
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_atribuicao_e_concessao_nao_se_duplicam() -> None:
    unidade = _unidade()
    acao = _acao()
    atribuicao = AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)

    with transaction.atomic(), pytest.raises(IntegrityError):
        AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)

    cargo_base = _cargo_base()
    Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo_base)
    with transaction.atomic(), pytest.raises(IntegrityError):
        Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo_base)

    cargo_comissao = _cargo_comissao()
    Concessao.objects.create(atribuicao=atribuicao, cargo_comissao=cargo_comissao)
    with transaction.atomic(), pytest.raises(IntegrityError):
        Concessao.objects.create(atribuicao=atribuicao, cargo_comissao=cargo_comissao)
