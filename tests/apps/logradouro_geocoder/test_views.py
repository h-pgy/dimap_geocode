import json
from typing import Any

import pytest
from bs4 import BeautifulSoup, Tag
from django.conf import settings
from django.test import Client
from django.urls import reverse

import apps.logradouro_geocoder.views as views
from services.domain.geometry import LineGeometry, reprojetar
from services.integrations.wfs import WfsFeatureCollection, WfsFeatureRequest

CODLOG = "156566"

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _eixo_no_mapa(x0: float, comprimento_m: float) -> dict[str, object]:
    y0 = 7395000.0
    metrico = LineGeometry(type="LineString", coordinates=[[x0, y0], [x0 + comprimento_m, y0]])
    no_mapa = reprojetar(metrico, settings.MAP_INTERPOLATION_CRS, settings.MAP_OUTPUT_CRS)
    return no_mapa.model_dump()


def _feat(id_segmento: str, geom: dict[str, object], par: str, impar: str) -> dict[str, object]:
    props: dict[str, object] = {
        "cd_identificador": id_segmento,
        "codlog": CODLOG,
        "cd_tipo_logradouro": "AV",
        "cd_titulo_logradouro": "BRIG",
        "nm_logradouro": "LUIS ANTONIO",
        "cd_numero_inicial_par": "2",
        "cd_numero_final_par": par,
        "cd_numero_inicial_impar": "1",
        "cd_numero_final_impar": impar,
    }
    return {"type": "Feature", "geometry": geom, "properties": props}


def _page(features_raw: list[dict[str, object]]) -> WfsFeatureCollection:
    return WfsFeatureCollection.model_validate(
        {"type": "FeatureCollection", "numberMatched": len(features_raw), "features": features_raw}
    )


def _instalar_fetcher_fake(
    monkeypatch: pytest.MonkeyPatch,
    pagina: WfsFeatureCollection,
    capturado: list[WfsFeatureRequest],
) -> None:
    def _fetcher_fake(req: WfsFeatureRequest) -> object:
        capturado.append(req)
        return iter([pagina])

    def _build_fetcher_fake(_settings: object) -> object:
        return _fetcher_fake

    monkeypatch.setattr(views, "build_fetcher", _build_fetcher_fake)


def _payload(soup: BeautifulSoup) -> dict[str, Any]:
    script = soup.find("script", id="mapa-payload")
    assert isinstance(script, Tag)
    return json.loads(script.get_text())  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# A resposta do logradouro abre a gaveta dele
# ---------------------------------------------------------------------------


def test_geocodificar_abre_a_gaveta_do_logradouro(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    segmentos = [
        _feat("SEG001", _eixo_no_mapa(333000.0, 1500.0), par="1000", impar="999"),
        _feat("SEG002", _eixo_no_mapa(334500.0, 1200.0), par="2000", impar="2747"),
    ]
    capturado: list[WfsFeatureRequest] = []
    _instalar_fetcher_fake(monkeypatch, _page(segmentos), capturado)

    resposta = client.post(reverse("logradouro_geocoder:geocodificar"), {"codlog": CODLOG})

    assert resposta.status_code == 200
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")
    features = _payload(soup)["geometria"]["features"]
    assert len(features) == 2
    assert features[0]["properties"]["rotulo"] == "AV BRIG LUIS ANTONIO"
    assert "AV BRIG LUIS ANTONIO" in features[0]["properties"]["popup_html"]

    oob = soup.find(id="gaveta-entidade")
    assert isinstance(oob, Tag)
    assert oob.has_attr("hx-swap-oob")
    gaveta = oob.select_one(f'[data-gaveta="logradouro-{CODLOG}"]')
    assert gaveta is not None
    texto = " ".join(gaveta.get_text().split())
    assert "AV BRIG LUIS ANTONIO" in texto
    assert CODLOG in texto
    assert "2,7 km" in texto
    assert "2.747" in texto
    assert len(capturado) == 1


# ---------------------------------------------------------------------------
# Histórico da gaveta lateral (SPEC design/021)
# ---------------------------------------------------------------------------


def test_gaveta_do_logradouro_entra_no_historico(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    segmento = _feat("SEG001", _eixo_no_mapa(333000.0, 1500.0), par="1000", impar="999")
    _instalar_fetcher_fake(monkeypatch, _page([segmento]), [])

    resposta = client.post(reverse("logradouro_geocoder:geocodificar"), {"codlog": CODLOG})

    raiz = BeautifulSoup(resposta.content.decode(), "html.parser").select_one(".gaveta-lateral")
    assert isinstance(raiz, Tag)
    assert raiz["data-gaveta"] == f"logradouro-{CODLOG}"
    historico = client.get(reverse("mapping:historico_gaveta"), {"chave": "outra-gaveta"})
    itens = BeautifulSoup(historico.content.decode(), "html.parser").select(".item-historico")
    assert len(itens) == 1
    assert itens[0].select_one('use[href="#glifo-gaveta-logradouro"]') is not None
    assert itens[0].get_text(strip=True) == f"AV BRIG LUIS ANTONIO · {CODLOG}"
