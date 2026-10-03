import json
from typing import Any

import pytest
from bs4 import BeautifulSoup, Tag
from django.conf import settings
from django.test import Client
from django.urls import reverse

import apps.logradouro_geocoder.views as views_logradouro
import apps.logradouro_mais_proximo.views as views
from services.domain.geometry import PointGeometry, reprojetar
from services.integrations.wfs import WfsFeatureCollection, WfsFeatureRequest

CODLOG_PERTO = "156566"
CODLOG_LONGE = "177911"

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
LINHA_NO_MAPA: dict[str, object] = {
    "type": "LineString",
    "coordinates": [[-46.6560, -23.5615], [-46.6550, -23.5613]],
}

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _feat(id_segmento: str, codlog: str, geom: dict[str, object]) -> dict[str, object]:
    props: dict[str, object] = {
        "cd_identificador": id_segmento,
        "codlog": codlog,
        "cd_tipo_logradouro": "AV",
        "nm_logradouro": f"LOGRADOURO {codlog}",
    }
    return {"type": "Feature", "geometry": geom, "properties": props}


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

    # A resposta reaproveitada consulta por conta própria, com o fetcher do app de busca.
    monkeypatch.setattr(views, "build_fetcher", _build_fetcher_fake)
    monkeypatch.setattr(views_logradouro, "build_fetcher", _build_fetcher_fake)


def _postar_desenho(client: Client, geometria: dict[str, object]) -> Any:
    return client.post(
        reverse("logradouro_mais_proximo:do_ponto"),
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
# Encontrou: a linha do logradouro inteiro, como na busca
# ---------------------------------------------------------------------------


def test_do_ponto_devolve_a_linha_do_logradouro_mais_proximo(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    no_raio = [
        _feat("LONGE", CODLOG_LONGE, _eixo_metrico(30.0)),
        _feat("PERTO", CODLOG_PERTO, _eixo_metrico(5.0)),
    ]
    do_codlog = [
        _feat("SEG001", CODLOG_PERTO, LINHA_NO_MAPA),
        _feat("SEG002", CODLOG_PERTO, LINHA_NO_MAPA),
    ]
    capturado: list[WfsFeatureRequest] = []
    _instalar_fetcher_fake(monkeypatch, [[_page(no_raio)], [_page(do_codlog)]], capturado)

    resposta = _postar_desenho(client, PONTO_NO_MAPA)

    assert resposta.status_code == 200
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")
    payload = _payload(soup)
    assert payload["cor"] == settings.MAP_COR_LINHA
    features = payload["geometria"]["features"]
    assert len(features) == 2
    assert all(f"codlog {CODLOG_PERTO}" in f["properties"]["popup_html"] for f in features)

    gaveta = soup.find(id="gaveta-entidade")
    assert isinstance(gaveta, Tag)
    assert gaveta.has_attr("hx-swap-oob")
    assert gaveta.contents == []

    assert len(capturado) == 2
    cql_do_codlog = capturado[1].cql_filter.to_cql()  # type: ignore[union-attr]
    assert f"'{CODLOG_PERTO}'" in cql_do_codlog


# ---------------------------------------------------------------------------
# Recusa: sem logradouro no raio, e desenho que não é ponto
# ---------------------------------------------------------------------------


def test_do_ponto_recusa_sem_logradouro_e_nao_ponto(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capturado: list[WfsFeatureRequest] = []
    _instalar_fetcher_fake(monkeypatch, [[_page([])]], capturado)

    resposta = _postar_desenho(client, PONTO_NO_MAPA)

    assert resposta.status_code == 200
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")
    aviso = soup.select_one('[role="alert"]')
    assert aviso is not None
    assert f"a {settings.MAIS_PROXIMO_RAIO_LIMITE_M:.0f} metros do ponto" in aviso.get_text()
    assert soup.find("script", id="mapa-payload") is None
    assert _toggle_dos_desenhos_recolhido(soup)
    assert len(capturado) == 1

    resposta_poligono = _postar_desenho(client, POLIGONO_NO_MAPA)

    assert resposta_poligono.status_code == 422
    assert len(capturado) == 1
