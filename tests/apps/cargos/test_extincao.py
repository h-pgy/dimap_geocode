"""
Testes de apps/cargos/extincao.py e apps/cargos/consulta.py (SPEC user_admin/029): o ato entra em
extinção sem revalidar nada — o cargo continua sendo avaliado, e só a nomeação (`cargos_nomeaveis`)
filtra o extinto.

Chamam `extinguir_cargo`/`reativar_cargo` direto, e não pela rota: as quatro ações são exclusivas
do superusuário e sem alcance, e o contrato HTTP delas (segurança, registro, edição) está em
tests/apps/cargos/views/. Todos levam o marker `banco`.
"""

from datetime import date

import pytest

from apps.cargos.consulta import cargos_nomeaveis
from apps.cargos.extincao import extinguir_cargo, reativar_cargo
from apps.cargos.models import CargoBase, CargoComissao
from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil

banco = pytest.mark.banco

HOJE = date(2026, 9, 4)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _cargo(nome: str, **overrides: object) -> CargoComissao:
    dados: dict[str, object] = {"sigla": "CDA", "nivel": 4, "e_chefia": True, "nome": nome}
    dados.update(overrides)
    return CargoComissao.objects.create(**dados)  # type: ignore[arg-type]


def _tipo_unidade(nome: str, **overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {"nome": nome, "nivel": 10, "pode_ser_raiz": True, "nivel_minimo_titular": 1}
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(sigla: str, **overrides: object) -> Unidade:
    dados: dict[str, object] = {"nome": f"Unidade {sigla}", "sigla": sigla, "tipo": _tipo_unidade(f"Tipo {sigla}")}
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base(**overrides: object) -> CargoBase:
    dados: dict[str, object] = {"nome": "Cargo Base Extinção", "sigla": "CGBE"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _perfil(unidade: Unidade, rf: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": "Servidor",
        "sobrenome": "Extinção",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


# ---------------------------------------------------------------------------
# O ato move a data e a nomeação segue a data
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_extinguir_data_o_cargo_e_o_tira_da_nomeacao() -> None:
    cargo = _cargo("Cargo Extinguido")

    desfecho = extinguir_cargo(cargo, HOJE)

    assert desfecho.cargo is not None
    assert desfecho.cargo.extinto_em == HOJE
    assert cargo.pk not in cargos_nomeaveis().values_list("pk", flat=True)


@banco
@pytest.mark.django_db
def test_cargo_extinto_segue_ofertado_a_quem_ja_o_ocupa() -> None:
    ocupado = _cargo("Cargo Ocupado Extinto")
    outro_extinto = _cargo("Outro Cargo Extinto")
    extinguir_cargo(ocupado, HOJE)
    extinguir_cargo(outro_extinto, HOJE)

    nomeaveis = set(cargos_nomeaveis(cargo_atual_id=ocupado.pk).values_list("pk", flat=True))

    assert ocupado.pk in nomeaveis
    assert outro_extinto.pk not in nomeaveis


@banco
@pytest.mark.django_db
def test_reativar_devolve_o_cargo_a_nomeacao() -> None:
    cargo = _cargo("Cargo Reativado")
    extinguir_cargo(cargo, HOJE)

    desfecho = reativar_cargo(cargo)

    assert desfecho.cargo is not None
    assert desfecho.cargo.extinto_em is None
    assert cargo.pk in cargos_nomeaveis().values_list("pk", flat=True)


# ---------------------------------------------------------------------------
# Extinguir não revalida nada: a competência segue de pé
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_cargo_extinto_continua_exercendo_competencia() -> None:
    unidade = _unidade("CARGO-COMP")
    cargo = _cargo("Cargo Competência Extinta")
    ocupante = _perfil(unidade, "9600000", cargo_comissao=cargo)
    acao, _ = Acao.objects.get_or_create(
        slug="competencias.definir_atribuicao",
        defaults={"nome": "Definir atribuição", "tooltip": "tt", "estrutural": False},
    )
    atribuicao = AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)
    Concessao.objects.create(atribuicao=atribuicao, cargo_comissao=cargo)
    assert Perfil.objects.get(pk=ocupante.pk).has_perm("competencias.definir_atribuicao")

    extinguir_cargo(cargo, HOJE)

    assert Perfil.objects.get(pk=ocupante.pk).has_perm("competencias.definir_atribuicao")
