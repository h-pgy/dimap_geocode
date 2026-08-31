"""
Testes dos atos de titularidade (SPEC user_admin/014): definir e destituir titular em transação —
a troca destitui o anterior na mesma operação, e destituir sozinho abre a vaga.

Marker `banco`: os atos escrevem em Perfil e a unicidade é constraint do Postgres.
"""

from django.utils import timezone

import pytest

from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, CargoComissao, Perfil
from apps.unidades.titularidade import (
    candidatos_a_titular,
    definir_titular,
    destituir_titular,
)

banco = pytest.mark.banco


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Titularidade",
        "nivel": 10,
        "pode_ser_raiz": True,
        "nivel_minimo_titular": 4,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo(**overrides: object) -> CargoComissao:
    dados: dict[str, object] = {
        "sigla": "CDA",
        "nivel": 4,
        "e_chefia": True,
        "nome": "Diretor de Divisão Titularidade",
    }
    dados.update(overrides)
    return CargoComissao.objects.create(**dados)  # type: ignore[arg-type]


def _perfil(unidade: Unidade, cargo: CargoComissao, **overrides: object) -> Perfil:
    cargo_base, _ = CargoBase.objects.get_or_create(
        nome="Cargo Titularidade", sigla="CGTD"
    )
    dados: dict[str, object] = {
        "rf": "700201",
        "nome": "Fulano",
        "sobrenome": "de Tal",
        "cargo_base": cargo_base,
        "unidade": unidade,
        "cargo_comissao": cargo,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


@banco
@pytest.mark.django_db
def test_troca_destitui_o_anterior_e_destituir_abre_a_vaga() -> None:
    tipo = _tipo_unidade()
    unidade = Unidade.objects.create(
        nome="Divisão Titularidade", sigla="DIVTD", tipo=tipo
    )
    cargo = _cargo()
    anterior = _perfil(unidade, cargo, rf="700201", nome="Anterior")
    novo = _perfil(unidade, cargo, rf="700202", nome="Novo")

    definir_titular(anterior)
    definir_titular(novo)

    anterior.refresh_from_db()
    assert anterior.e_titular is False
    assert Perfil.objects.filter(unidade=unidade, e_titular=True).count() == 1
    assert unidade.titular == novo

    destituir_titular(unidade)

    assert Perfil.objects.filter(unidade=unidade, e_titular=True).count() == 0
    assert unidade.titular is None


# ---------------------------------------------------------------------------
# Exonerado não é candidato a titular (SPEC user_admin/027)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_exonerado_nao_e_candidato_a_titular() -> None:
    tipo = _tipo_unidade(nome="Divisão Titular Exonerado")
    unidade = Unidade.objects.create(
        nome="Divisão Titular Exonerado", sigla="DIVTDEXO", tipo=tipo
    )
    cargo = _cargo(nome="Diretor Titular Exonerado")
    exonerado = _perfil(
        unidade,
        cargo,
        rf="700210",
        nome="Exonerado",
        is_active=False,
        exonerado_em=timezone.localdate(),
    )

    assert exonerado not in candidatos_a_titular(unidade)
