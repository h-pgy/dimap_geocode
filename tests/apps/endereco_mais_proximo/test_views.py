import json
from typing import Any

import pytest
from bs4 import BeautifulSoup, Tag
from django.conf import settings
from django.test import Client
from django.urls import reverse

import apps.endereco_mais_proximo.views as views
from services.domain.geometry import PointGeometry, reprojetar
from services.integrations.wfs import WfsFeatureCollection, WfsFeatureRequest

CODLOG = "156566"

PONTO_NO_MAPA: dict[str, object] = {"type": "Point", "coordinates": [-46.6559, -23.5614]}
POLIGONO_NO_MAPA: dict[str, object] = {
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


def _feat(
    id_segmento: str,
    geom: dict[str, object],
    *,
    par: tuple[int, int] | None = None,
    impar: tuple[int, int] | None = None,
) -> dict[str, object]:
    props: dict[str, object] = {
        "cd_identificador": id_segmento,
        "codlog": CODLOG,
        "cd_tipo_logradouro": "AV",
        "nm_logradouro": "PAULISTA",
        "cd_numero_inicial_par": None if par is None else par[0],
        "cd_numero_final_par": None if par is None else par[1],
        "cd_numero_inicial_impar": None if impar is None else impar[0],
        "cd_numero_final_impar": None if impar is None else impar[1],
    }
    return {"type": "Feature", "geometry": geom, "properties": props}


# Eixo a leste, ao norte do ponto: o ponto fica à direita, do lado par, no meio do segmento.
def _eixo_metrico(afastamento_m: float) -> dict[str, object]:
    ponto = PointGeometry.model_validate(PONTO_NO_MAPA)
    x, y = reprojetar(ponto, 4326, 31983).coordinates
    y_eixo = y + afastamento_m
    return {"type": "LineString", "coordinates": [[x - 20.0, y_eixo], [x + 20.0, y_eixo]]}


def _page(features_raw: list[dict[str, object]]) -> WfsFeatureCollection:
    return WfsFeatureCollection.model_validate(
        {"type": "FeatureCollection", "numberMatched": len(features_raw), "features": features_raw}
    )


def _instalar_fetcher_fake(
    monkeypatch: pytest.MonkeyPatch,
    respostas: list[list[WfsFeatureCollection]],
    capturado: list[WfsFeatureRequest],
) -> None:
    def _fetcher_fake(req: WfsFeatureRequest) -> object:
        pages = respostas[len(capturado)]
        capturado.append(req)
        return iter(pages)

    def _build_fetcher_fake(_settings: object) -> object:
        return _fetcher_fake

    monkeypatch.setattr(views, "build_fetcher", _build_fetcher_fake)


def _postar_desenho(client: Client, geometria: dict[str, object]) -> Any:
    return client.post(
        reverse("endereco_mais_proximo:do_ponto"),
        {"id_bancada": "7", "desenho": json.dumps(geometria)},
    )


def _payload(soup: BeautifulSoup) -> dict[str, Any]:
    script = soup.find("script", id="mapa-payload")
    assert isinstance(script, Tag)
    return json.loads(script.get_text())  # type: ignore[no-any-return]


def _toggle_dos_desenhos_recolhido(soup: BeautifulSoup) -> bool:
    toggle = soup.find("input", id="gaveta-desenhos-toggle")
    return isinstance(toggle, Tag) and toggle.has_attr("hx-swap-oob") and not toggle.has_attr("checked")


# ---------------------------------------------------------------------------
# Encontrou: o ponto do endereço e a gaveta da busca; recusas sem payload
# ---------------------------------------------------------------------------


def test_do_ponto_devolve_mapa_e_gaveta_do_endereco(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    numerado = _feat("SEG001", _eixo_metrico(5.0), par=(100, 200), impar=(101, 199))
    sem_numeracao = _feat("SEG002", _eixo_metrico(5.0))
    capturado: list[WfsFeatureRequest] = []
    respostas = [
        [_page([numerado])],
        [_page([numerado])],
        [_page([sem_numeracao])],
    ]
    _instalar_fetcher_fake(monkeypatch, respostas, capturado)

    resposta = _postar_desenho(client, PONTO_NO_MAPA)

    assert resposta.status_code == 200
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")
    payload = _payload(soup)
    assert payload["cor"] == settings.MAP_COR_PONTO
    features = payload["geometria"]["features"]
    assert len(features) == 1
    assert features[0]["geometry"]["type"] == "Point"
    assert f"codlog {CODLOG}" in features[0]["properties"]["popup_html"]

    gaveta = soup.find(id="gaveta-entidade")
    assert isinstance(gaveta, Tag)
    assert gaveta.has_attr("hx-swap-oob")
    texto_da_gaveta = " ".join(gaveta.get_text().split())
    assert "AV PAULISTA, 150" in texto_da_gaveta
    assert CODLOG in texto_da_gaveta
    assert "100 – 200" in texto_da_gaveta
    assert len(capturado) == 2

    sem_numerado = _postar_desenho(client, PONTO_NO_MAPA)

    assert sem_numerado.status_code == 200
    soup_sem_numerado = BeautifulSoup(sem_numerado.content.decode(), "html.parser")
    aviso = soup_sem_numerado.select_one('[role="alert"]')
    assert aviso is not None
    assert f"a {settings.MAIS_PROXIMO_RAIO_LIMITE_M:.0f} metros do ponto" in aviso.get_text()
    assert soup_sem_numerado.find("script", id="mapa-payload") is None
    assert _toggle_dos_desenhos_recolhido(soup_sem_numerado)
    assert len(capturado) == 3

    poligono = _postar_desenho(client, POLIGONO_NO_MAPA)

    assert poligono.status_code == 422
    assert len(capturado) == 3
