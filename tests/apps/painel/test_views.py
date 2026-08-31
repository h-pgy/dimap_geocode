"""Testes de apps/painel/views.py (SPEC painel/001): o painel exige login, e é ele — não mais a
página do próprio perfil — o destino de quem acaba de entrar no sistema.
"""

from django.test import Client
from django.urls import reverse

import pytest

from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, Perfil

banco = pytest.mark.banco

SENHA = "SenhaForte123!"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(rf: str) -> TipoUnidade:
    return TipoUnidade.objects.create(
        nome=f"Divisão Painel {rf}",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )


def _unidade(rf: str) -> Unidade:
    return Unidade.objects.create(
        nome=f"Unidade Painel {rf}",
        sigla=f"PNL-{rf}",
        tipo=_tipo_unidade(rf),
    )


def _cargo_base() -> CargoBase:
    cargo, _ = CargoBase.objects.get_or_create(nome="Cargo Painel", sigla="CGPN")
    return cargo


def _perfil(rf: str) -> Perfil:
    perfil = Perfil(
        rf=rf,
        nome="Fulana",
        sobrenome="Painel",
        cargo_base=_cargo_base(),
        unidade=_unidade(rf),
        senha_provisoria=False,
    )
    perfil.set_password(SENHA)
    perfil.save()
    return perfil


# ---------------------------------------------------------------------------
# Visitante anônimo não alcança o painel
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_painel_exige_login(client: Client) -> None:
    resposta = client.get(reverse("painel:painel"))

    assert resposta.status_code == 302
    assert resposta.url.startswith(reverse("autenticacao:login"))


# ---------------------------------------------------------------------------
# Entrar no sistema leva ao painel, não à página do próprio perfil
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_login_leva_ao_painel(client: Client) -> None:
    rf = "9601001"
    _perfil(rf)

    resposta = client.post(reverse("autenticacao:login"), {"rf": rf, "password": SENHA})

    assert resposta.status_code == 302
    assert resposta.url == reverse("painel:painel")
