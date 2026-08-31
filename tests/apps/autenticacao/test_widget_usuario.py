"""
Testes do widget de usuário no topo (`#widget-area-usuario`, `templates/base.html`) e do context
processor que o alimenta quando autenticado (SPEC autenticacao/001): o widget alterna entre o
estado anônimo, que aponta para o login, e o autenticado, que exibe a identidade do servidor e
aponta para o painel (SPEC painel/001) — o hub da área administrativa, não mais direto para a
própria página de perfil.

O estado autenticado leva o marker `banco`: depende de Perfil e Unidade persistidos.
"""

from bs4 import BeautifulSoup
from django.test import Client
from django.urls import reverse

import pytest

from apps.unidades.models import CorUnidade, TipoUnidade, Unidade
from apps.unidades.paleta import HEX_POR_COR
from apps.user_admin.models import CargoBase, Perfil

banco = pytest.mark.banco


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Widget Usuário",
        "nivel": 10,
        "pode_ser_raiz": True,
        "nivel_minimo_titular": 1,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(**overrides: object) -> Unidade:
    dados: dict[str, object] = {
        "nome": "Unidade Widget Usuário",
        "sigla": "WGT",
        "cor": CorUnidade.SAKURA_600,
        "tipo": _tipo_unidade(),
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base() -> CargoBase:
    cargo, _ = CargoBase.objects.get_or_create(nome="Cargo Widget Usuário", sigla="CGWU")
    return cargo


def _perfil(**overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": "9501234",
        "nome": "Fulana",
        "sobrenome": "Widget",
        "cargo_base": _cargo_base(),
        "unidade": _unidade(),
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("SenhaForte123!")
    perfil.save()
    return perfil


# ---------------------------------------------------------------------------
# Estados do widget
# ---------------------------------------------------------------------------


def test_widget_usuario_anonimo_exibe_link_login_e_icone_padrao(client: Client) -> None:
    html = client.get(reverse("core:home")).content.decode()
    widget = BeautifulSoup(html, "html.parser").find(id="widget-area-usuario")

    assert widget is not None
    assert widget["href"] == reverse("autenticacao:login")
    assert "Entrar" in widget.get_text()


@banco
@pytest.mark.django_db
def test_widget_usuario_autenticado_exibe_avatar_e_link_painel(client: Client) -> None:
    perfil = _perfil()
    client.force_login(perfil)

    html = client.get(reverse("core:home")).content.decode()
    widget = BeautifulSoup(html, "html.parser").find(id="widget-area-usuario")

    assert widget is not None
    assert widget["href"] == reverse("painel:painel")
    assert perfil.nome in widget.get_text()
    assert f"--cor-unidade: {HEX_POR_COR[CorUnidade.SAKURA_600]}" in html
