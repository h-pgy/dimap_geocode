"""
Testes da adequação de titularidade cruzando Perfil e Unidade (SPEC user_admin/014): o cargo do
titular precisa satisfazer o mínimo do tipo da própria unidade, e a validação recusa tanto quando
o cargo é rebaixado quanto quando a unidade muda para um tipo mais exigente.

Marker `banco`: a adequação cruza tabela (Perfil → cargo, Perfil → unidade → tipo) e só se
verifica contra o Postgres real — o mesmo caso que Unidade.clean() já resolve para a hierarquia.
"""

from django.core.exceptions import ValidationError

import pytest

from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, CargoComissao, Perfil

banco = pytest.mark.banco


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Adequação",
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
        "nome": "Diretor de Divisão Adequação",
    }
    dados.update(overrides)
    return CargoComissao.objects.create(**dados)  # type: ignore[arg-type]


def _titular(unidade: Unidade, cargo: CargoComissao) -> Perfil:
    cargo_base, _ = CargoBase.objects.get_or_create(nome="Cargo Adequação", sigla="CGA")
    perfil = Perfil(
        rf="700101",
        nome="Titular",
        sobrenome="Adequação",
        cargo_base=cargo_base,
        unidade=unidade,
        cargo_comissao=cargo,
        e_titular=True,
    )
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


@banco
@pytest.mark.django_db
def test_titular_invalido_e_recusado_na_validacao() -> None:
    tipo = _tipo_unidade()
    unidade = Unidade.objects.create(nome="Divisão Adequação", sigla="DIVA", tipo=tipo)
    cargo_adequado = _cargo()
    titular = _titular(unidade, cargo_adequado)

    # Rebaixar o cargo do titular: nível 2 fica abaixo do mínimo do tipo (4).
    titular.cargo_comissao = _cargo(
        sigla="CS", nivel=2, nome="Chefe de Seção Adequação"
    )
    with pytest.raises(ValidationError):
        titular.full_clean()

    # Mudar a unidade para um tipo que o titular atual (nível 4) não satisfaz (mínimo 6).
    tipo_mais_exigente = _tipo_unidade(
        nome="Coordenadoria Adequação",
        nivel=20,
        nivel_minimo_titular=6,
    )
    unidade.tipo = tipo_mais_exigente
    with pytest.raises(ValidationError):
        unidade.full_clean()
