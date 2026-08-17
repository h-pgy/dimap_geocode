"""
Testes da árvore hierárquica (SPEC user_admin/018): a seção da página da unidade traz o organograma
inteiro com o caminho e o ego marcados pelo servidor (`no-arvore-caminho`/`no-arvore-ego` — o
contrato com o JS de abrir/fechar), cada card leva à página da sua unidade, e a página do
organograma abre sem nenhuma unidade em foco.

Todos levam o marker `banco`: a posição é montada a partir das tabelas.
"""

from bs4 import BeautifulSoup
from bs4.element import Tag
from django.test import Client
from django.urls import reverse

import pytest

from apps.user_admin.models import TipoUnidade, Unidade

banco = pytest.mark.banco


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Árvore Hierárquica",
        "nivel": 10,
        "pode_ser_raiz": True,
        "nivel_minimo_titular": 4,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(sigla: str, tipo: TipoUnidade | None = None, **overrides: object) -> Unidade:
    dados: dict[str, object] = {
        "nome": f"Unidade {sigla}",
        "sigla": sigla,
        "tipo": tipo or _tipo_unidade(nome=f"Tipo {sigla}"),
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _organograma() -> dict[str, Unidade]:
    """Cinco unidades em três níveis: um caminho (raiz → meio → ego), uma irmã do ego que não
    entra no caminho, e uma filha do ego."""
    raiz = _unidade(
        "SF-ARV",
        tipo=_tipo_unidade(nome="Secretaria Árvore", nivel=30, nivel_minimo_titular=6),
    )
    meio = _unidade(
        "SUREM-ARV",
        tipo=_tipo_unidade(nome="Subsecretaria Árvore", nivel=20, nivel_minimo_titular=5),
        pai=raiz,
    )
    ego = _unidade(
        "DIMAP-ARV",
        tipo=_tipo_unidade(nome="Divisão Árvore", nivel=10, nivel_minimo_titular=4),
        pai=meio,
    )
    irma = _unidade(
        "DICAD-ARV",
        tipo=_tipo_unidade(nome="Divisão Irmã Árvore", nivel=10, nivel_minimo_titular=4),
        pai=meio,
    )
    filha = _unidade(
        "DIMAP-1-ARV",
        tipo=_tipo_unidade(nome="Setor Árvore", nivel=5, nivel_minimo_titular=1),
        pai=ego,
    )
    return {
        "raiz": raiz,
        "meio": meio,
        "ego": ego,
        "irma": irma,
        "filha": filha,
    }


def _url_unidade(unidade: Unidade) -> str:
    return reverse("user_admin:pagina_unidade", kwargs={"pk": unidade.pk})


def _no_da_unidade(soup: BeautifulSoup, sigla: str) -> Tag:
    """A sigla é o único texto do card que a identifica sem ambiguidade (SPEC 018 §2): dela sobe até
    o nó do organograma que carrega as classes de estado."""
    rotulo = soup.find(class_="card-unidade-sigla", string=lambda texto: bool(texto) and texto.strip() == sigla)
    assert rotulo is not None, f"sigla {sigla} não encontrada no organograma"
    no = rotulo.find_parent(class_="no-arvore")
    assert no is not None
    return no


# ---------------------------------------------------------------------------
# Caminho marcado na página da unidade
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_secao_traz_o_organograma_inteiro_com_o_caminho_marcado(client: Client) -> None:
    unidades = _organograma()

    html = client.get(_url_unidade(unidades["ego"])).content.decode()
    soup = BeautifulSoup(html, "html.parser")

    for unidade in unidades.values():
        assert _no_da_unidade(soup, unidade.sigla) is not None

    assert "no-arvore-caminho" in _no_da_unidade(soup, unidades["raiz"].sigla)["class"]
    assert "no-arvore-caminho" in _no_da_unidade(soup, unidades["meio"].sigla)["class"]
    assert "no-arvore-ego" in _no_da_unidade(soup, unidades["ego"].sigla)["class"]
    assert "no-arvore-caminho" not in _no_da_unidade(soup, unidades["ego"].sigla)["class"]

    # Irmã e filha do ego não pertencem ao caminho.
    assert "no-arvore-caminho" not in _no_da_unidade(soup, unidades["irma"].sigla)["class"]
    assert "no-arvore-ego" not in _no_da_unidade(soup, unidades["irma"].sigla)["class"]
    assert "no-arvore-caminho" not in _no_da_unidade(soup, unidades["filha"].sigla)["class"]
    assert "no-arvore-ego" not in _no_da_unidade(soup, unidades["filha"].sigla)["class"]


# ---------------------------------------------------------------------------
# Segundo caminho: cada card leva à página da sua unidade
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_cada_card_leva_a_pagina_da_sua_unidade(client: Client) -> None:
    unidades = _organograma()

    html = client.get(_url_unidade(unidades["ego"])).content.decode()
    soup = BeautifulSoup(html, "html.parser")

    for unidade in unidades.values():
        no = _no_da_unidade(soup, unidade.sigla)
        elo = no.find("a", class_="card-unidade-pagina")
        assert elo is not None, f"{unidade.sigla} sem elo para a própria página"
        assert elo["href"] == _url_unidade(unidade)


# ---------------------------------------------------------------------------
# Página do organograma inteiro
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_pagina_da_arvore_abre_no_topo(client: Client) -> None:
    unidades = _organograma()

    resposta = client.get(reverse("user_admin:arvore_de_unidades"))
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 200
    for unidade in unidades.values():
        assert _no_da_unidade(soup, unidade.sigla) is not None
    assert soup.find(class_="no-arvore-ego") is None
