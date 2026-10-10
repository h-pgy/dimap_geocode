"""
Testes de apps/unidades/views.py — `listar_tipos_unidade` (SPEC user_admin/031): leitura aberta a
qualquer servidor autenticado, sem os gestos de ato para quem não administra o sistema. O toggle
"Mostrar tipos extintos" é 100% client-side (Caveats) — o servidor sempre manda todas as linhas,
marcadas, e não há estado de "extintos" para testar aqui; quem oculta é `filtro_linha_extinta.js`,
fora do alcance de `django.test.Client`. Todos levam o marker `banco`.
"""

from datetime import date

from django.test import Client
from django.urls import reverse

import pytest

from apps.cargos.models import CargoBase
from apps.unidades.extincao_tipo import extinguir_tipo_unidade
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil

banco = pytest.mark.banco

ROTAS_DE_ATO = (
    "unidades:modal_criar_tipo_unidade",
    "unidades:modal_editar_tipo_unidade",
    "unidades:modal_extinguir_tipo_unidade",
    "unidades:modal_reativar_tipo_unidade",
)


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
    dados: dict[str, object] = {"nome": "Cargo Base Listagem Tipo", "sigla": "CGBLT"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _perfil(unidade: Unidade, rf: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": "Sem Caneta",
        "sobrenome": "Listagem Tipo",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _url_listar() -> str:
    return reverse("unidades:listar_tipos_unidade")


# ---------------------------------------------------------------------------
# O extinto sempre chega ao HTML, marcado — quem o esconde é o toggle no cliente
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_corpo_sempre_traz_os_tipos_extintos_marcados(client: Client) -> None:
    perfil = _perfil(_unidade("TIPO-LIST"), "9610400")
    extinto = _tipo_unidade("Tipo Sempre Na Lista")
    extinguir_tipo_unidade(extinto, date(2026, 10, 7))

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
    perfil = _perfil(_unidade("TIPO-ABERTA"), "9610500")
    visivel = _tipo_unidade("Tipo Visível Na Lista")

    client.force_login(perfil)
    resposta = client.get(_url_listar())
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert visivel.nome in html
    # Nem o botão de criar, nem o lápis/lixeira por linha: quem não administra o sistema só lê.
    assert "Novo tipo" not in html
    for rota in ROTAS_DE_ATO:
        assert reverse(rota) not in html, rota
