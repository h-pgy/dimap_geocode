"""
Testes de apps/cargos/views.py — `listar_cargos` (SPEC user_admin/029): leitura aberta a qualquer
servidor autenticado, sem os gestos de ato para quem não administra o sistema. O toggle "Mostrar
cargos extintos" é 100% client-side (Caveats) — o servidor sempre manda todas as linhas, marcadas,
e não há mais estado de "extintas" para testar aqui; quem oculta é `filtro_linha_extinta.js`, fora
do alcance de `django.test.Client`. Mesmo regime de `unidades:listar_unidades` (SPEC
user_admin/025). Todos levam o marker `banco`.
"""

from datetime import date

from bs4 import BeautifulSoup
from django.test import Client
from django.urls import reverse

import pytest

from apps.cargos.extincao import extinguir_cargo
from apps.cargos.models import CargoBase, CargoComissao
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil

banco = pytest.mark.banco


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


def _cargo_base(**overrides: object) -> CargoBase:
    dados: dict[str, object] = {"nome": "Cargo Base Listagem", "sigla": "CGBL"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _perfil(unidade: Unidade, rf: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": "Sem Caneta",
        "sobrenome": "Listagem",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _cargo(nome: str, **overrides: object) -> CargoComissao:
    dados: dict[str, object] = {"sigla": "CDA", "nivel": 4, "e_chefia": True, "nome": nome}
    dados.update(overrides)
    return CargoComissao.objects.create(**dados)  # type: ignore[arg-type]


def _url_listar() -> str:
    return reverse("cargos:listar_cargos")


# ---------------------------------------------------------------------------
# O extinto sempre chega ao HTML, marcado — quem o esconde é o toggle no cliente
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_corpo_sempre_traz_os_extintos_marcados(client: Client) -> None:
    perfil = _perfil(_unidade("CARGO-LIST"), "9600400")
    extinto = _cargo("Cargo Sempre Na Lista")
    extinguir_cargo(extinto, date(2026, 9, 4))

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
    perfil = _perfil(_unidade("CARGO-ABERTA"), "9600500")
    _cargo("Cargo Visível Na Lista")

    client.force_login(perfil)
    resposta = client.get(_url_listar())
    sopa = BeautifulSoup(resposta.content.decode(), "html.parser")

    assert resposta.status_code == 200
    # Nem o card de criar, nem o lápis/lixeira por linha: quem não administra o sistema só lê.
    assert "Novo cargo" not in sopa.get_text()
    assert sopa.select_one("[data-abrir-modal]") is None
