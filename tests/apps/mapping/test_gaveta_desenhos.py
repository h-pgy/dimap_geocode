"""Testes automatizados da SPEC design/020: a gaveta de desenhos da bancada, aberta sem login pela
rota `mapping:desenhos_da_bancada`, e a fiação em `core:home` e no styleguide."""

import json
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse

REPO_ROOT = Path(__file__).resolve().parents[3]
JS_INIT = REPO_ROOT / "static" / "src" / "js" / "mapa" / "init.js"

PONTO_GEOJSON = {"type": "Point", "coordinates": [-46.6559, -23.5614]}
POLIGONO_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[
        [-46.6560, -23.5620],
        [-46.6550, -23.5620],
        [-46.6550, -23.5610],
        [-46.6560, -23.5610],
        [-46.6560, -23.5620],
    ]],
}


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _postar_desenhos(
    desenhos: list[dict[str, Any]],
    selecionados: list[str] | None = None,
) -> HttpResponse:
    return Client().post(  # type: ignore[return-value]
        reverse("mapping:desenhos_da_bancada"),
        {
            "desenhos": json.dumps(desenhos),
            "selecionados": json.dumps(selecionados or []),
        },
    )


# ---------------------------------------------------------------------------
# Rota da gaveta dos desenhos — aberta sem login
# ---------------------------------------------------------------------------


def test_desenhos_da_bancada_abrem_a_gaveta_sem_login() -> None:
    resposta = _postar_desenhos([
        {"id_bancada": "1", "geometria": PONTO_GEOJSON},
        {"id_bancada": "2", "geometria": POLIGONO_GEOJSON},
    ])
    assert resposta.status_code == 200
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")

    pocos = soup.find_all(class_="poco-desenhos")
    assert len(pocos) == 2

    radios = soup.find_all("input", class_="linha-desenho__marca")
    marcados = {radio["value"] for radio in radios if radio.has_attr("checked")}
    assert marcados == {"1", "2"}


def test_radio_carrega_o_id_da_camada() -> None:
    resposta = _postar_desenhos([{"id_bancada": "42", "geometria": PONTO_GEOJSON}])
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")

    radio = soup.find("input", class_="linha-desenho__marca")
    assert radio is not None
    assert radio["value"] == "42"
    assert radio.has_attr("checked")


def test_colecao_vazia_nao_devolve_gaveta() -> None:
    resposta = _postar_desenhos([])
    assert resposta.status_code == 200
    assert resposta.content.decode().strip() == ""


# ---------------------------------------------------------------------------
# Home: URL declarada no container do mapa e sincronia carregada como módulo
# ---------------------------------------------------------------------------


def test_home_carrega_a_sincronia_dos_desenhos() -> None:
    resposta = Client().get(reverse("core:home"))
    assert resposta.status_code == 200
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")

    container = soup.select_one("[data-url-desenhos]")
    assert container is not None
    assert container["data-url-desenhos"] == reverse("mapping:desenhos_da_bancada")

    conteudo_init = JS_INIT.read_text(encoding="utf-8")
    assert 'from "./desenho/sincronia.js"' in conteudo_init
    assert "inicializarSincronia(mapa" in conteudo_init


# ---------------------------------------------------------------------------
# Styleguide
# ---------------------------------------------------------------------------


def test_styleguide_registra_as_pecas_do_poco() -> None:
    resposta = Client().get(reverse("core:design_system"))
    assert resposta.status_code == 200
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")

    assert soup.find(class_="poco-desenhos") is not None
    assert soup.find(class_="linha-desenho") is not None
