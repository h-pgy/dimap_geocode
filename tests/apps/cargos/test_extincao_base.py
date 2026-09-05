"""
Testes de apps/cargos/extincao.py e apps/cargos/consulta.py sobre o catálogo de cargo base (SPEC
user_admin/030): mesmo ato de user_admin/029, outro catálogo — o cargo entra em extinção sem
revalidar nada, e só a nomeação (`cargos_base_nomeaveis`) filtra o extinto.

Chamam `extinguir_cargo_base`/`reativar_cargo_base` direto, e não pela rota: as quatro ações são
exclusivas do superusuário e sem alcance, e o contrato HTTP delas está em tests/apps/cargos/views/.
Todos levam o marker `banco`.
"""

from datetime import date
from itertools import count

import pytest

from apps.cargos.consulta import cargos_base_nomeaveis
from apps.cargos.extincao import extinguir_cargo_base, reativar_cargo_base
from apps.cargos.models import CargoBase
from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil

banco = pytest.mark.banco

HOJE = date(2026, 9, 4)
# CargoBase.sigla é única: um contador garante sigla nova a cada cargo, mesmo entre nomes que
# comecem iguais ("Cargo Base ...").
_SIGLAS = count(1)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _cargo_base(nome: str, **overrides: object) -> CargoBase:
    dados: dict[str, object] = {"sigla": f"CB{next(_SIGLAS)}", "nome": nome}
    dados.update(overrides)
    return CargoBase.objects.create(**dados)  # type: ignore[arg-type]


def _tipo_unidade(nome: str, **overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {"nome": nome, "nivel": 10, "pode_ser_raiz": True, "nivel_minimo_titular": 1}
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(sigla: str, **overrides: object) -> Unidade:
    dados: dict[str, object] = {"nome": f"Unidade {sigla}", "sigla": sigla, "tipo": _tipo_unidade(f"Tipo {sigla}")}
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _perfil(unidade: Unidade, rf: str, cargo_base: CargoBase, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": "Servidor",
        "sobrenome": "Extinção Base",
        "cargo_base": cargo_base,
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
def test_extinguir_data_o_cargo_base_e_o_tira_da_nomeacao() -> None:
    cargo = _cargo_base("Cargo Base Extinguido")

    desfecho = extinguir_cargo_base(cargo, HOJE)

    assert desfecho.cargo is not None
    assert desfecho.cargo.extinto_em == HOJE
    assert cargo.pk not in cargos_base_nomeaveis().values_list("pk", flat=True)


@banco
@pytest.mark.django_db
def test_cargo_base_extinto_segue_ofertado_a_quem_ja_o_ocupa() -> None:
    ocupado = _cargo_base("Cargo Base Ocupado Extinto")
    outro_extinto = _cargo_base("Outro Cargo Base Extinto")
    extinguir_cargo_base(ocupado, HOJE)
    extinguir_cargo_base(outro_extinto, HOJE)

    nomeaveis = set(cargos_base_nomeaveis(cargo_atual_id=ocupado.pk).values_list("pk", flat=True))

    assert ocupado.pk in nomeaveis
    assert outro_extinto.pk not in nomeaveis


@banco
@pytest.mark.django_db
def test_reativar_devolve_o_cargo_base_a_nomeacao() -> None:
    cargo = _cargo_base("Cargo Base Reativado")
    extinguir_cargo_base(cargo, HOJE)

    desfecho = reativar_cargo_base(cargo)

    assert desfecho.cargo is not None
    assert desfecho.cargo.extinto_em is None
    assert cargo.pk in cargos_base_nomeaveis().values_list("pk", flat=True)


# ---------------------------------------------------------------------------
# Extinguir não revalida nada: a competência segue de pé
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_cargo_base_extinto_continua_exercendo_competencia() -> None:
    unidade = _unidade("CARGOBASE-COMP")
    cargo = _cargo_base("Cargo Base Competência Extinta")
    ocupante = _perfil(unidade, "9610000", cargo)
    acao, _ = Acao.objects.get_or_create(
        slug="competencias.definir_atribuicao",
        defaults={"nome": "Definir atribuição", "tooltip": "tt", "estrutural": False},
    )
    atribuicao = AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)
    Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo)
    assert Perfil.objects.get(pk=ocupante.pk).has_perm("competencias.definir_atribuicao")

    extinguir_cargo_base(cargo, HOJE)

    assert Perfil.objects.get(pk=ocupante.pk).has_perm("competencias.definir_atribuicao")
