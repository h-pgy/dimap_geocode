"""
Testes de apps/cargos/views.py — `listar_cargos_base` (SPEC user_admin/030): leitura aberta a
qualquer servidor autenticado, sem os gestos de ato para quem não administra o sistema. Mesmo
regime de `listar_cargos` (SPEC user_admin/029): o toggle "Mostrar cargos extintos" é 100%
client-side desde a primeira versão (SPEC 029, Caveats) — o servidor sempre manda todas as linhas,
marcadas, e não há round-trip para testar aqui. Todos levam o marker `banco`.
"""

from datetime import date
from itertools import count

from bs4 import BeautifulSoup
from django.test import Client
from django.urls import reverse

import pytest

from apps.cargos.extincao import extinguir_cargo_base
from apps.cargos.models import CargoBase
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil

banco = pytest.mark.banco
_SIGLAS = count(1)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(nome: str, **overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {"nome": nome, "nivel": 10, "pode_ser_raiz": True, "nivel_minimo_titular": 1}
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(sigla: str, **overrides: object) -> Unidade:
    dados: dict[str, object] = {"nome": f"Unidade {sigla}", "sigla": sigla, "tipo": _tipo_unidade(f"Tipo {sigla}")}
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base(nome: str = "Cargo Base Listagem", **overrides: object) -> CargoBase:
    defaults: dict[str, object] = {"sigla": f"CB{next(_SIGLAS)}"}
    defaults.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(nome=nome, defaults=defaults)  # type: ignore[arg-type]
    return cargo


def _perfil(unidade: Unidade, rf: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": "Sem Caneta",
        "sobrenome": "Listagem Base",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _url_listar() -> str:
    return reverse("cargos:listar_cargos_base")


# ---------------------------------------------------------------------------
# O extinto sempre chega ao HTML, marcado — quem o esconde é o toggle no cliente
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_corpo_sempre_traz_os_extintos_marcados(client: Client) -> None:
    perfil = _perfil(_unidade("CARGOBASE-LIST"), "9610100")
    extinto = _cargo_base("Cargo Base Sempre Na Lista", sigla="CBSL")
    extinguir_cargo_base(extinto, date(2026, 9, 4))

    client.force_login(perfil)
    resposta = client.get(_url_listar()).content.decode()

    assert extinto.nome in resposta
    assert 'class="linha-extinta"' in resposta


# ---------------------------------------------------------------------------
# Leitura aberta, sem os gestos de ato para quem não administra o sistema
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_listagem_aberta_a_qualquer_autenticado(client: Client) -> None:
    perfil = _perfil(_unidade("CARGOBASE-ABERTA"), "9610200")
    _cargo_base("Cargo Base Visível Na Lista", sigla="CBVL")

    client.force_login(perfil)
    resposta = client.get(_url_listar())
    sopa = BeautifulSoup(resposta.content.decode(), "html.parser")

    assert resposta.status_code == 200
    assert "Novo cargo base" not in sopa.get_text()
    assert sopa.select_one("[data-abrir-modal]") is None
