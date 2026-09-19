"""Testes de apps/lotes_mais_proximos/views.py: busca do lote mais próximo do ponto interpolado
(SPEC localizacao_lote/002) e lotes que cruzam um desenho (SPEC localizacao_lote/003) — rotas
abertas, sem login (§3.5 do CLAUDE.md)."""

import json
import re
from typing import Any

import pytest
from bs4 import BeautifulSoup, Tag
from django.conf import settings
from django.test import Client
from django.urls import reverse

import apps.lotes_mais_proximos.views as views
from services.domain.geometry import PolygonGeometry, reprojetar
from services.integrations.wfs import WfsFeatureCollection, WfsFeatureRequest

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

_PROPS_LOTE: dict[str, object] = {
    "cd_identificador": "POL001",
    "cd_setor_fiscal": "005",
    "cd_quadra_fiscal": "003",
    "cd_lote": "0048",
    "cd_tipo_lote": "F",
}


def _quadrado(x0: float, y0: float, lado: float) -> dict[str, object]:
    anel = [[x0, y0], [x0 + lado, y0], [x0 + lado, y0 + lado], [x0, y0 + lado], [x0, y0]]
    return {"type": "Polygon", "coordinates": [anel]}


def _feat(props: dict[str, object], geom: dict[str, object]) -> dict[str, object]:
    return {"type": "Feature", "geometry": geom, "properties": props}


def _page(features_raw: list[dict[str, object]]) -> WfsFeatureCollection:
    return WfsFeatureCollection.model_validate(
        {"type": "FeatureCollection", "numberMatched": len(features_raw), "features": features_raw}
    )


def _retangulo_no_mapa(x0: float, y0: float, lado: float) -> dict[str, object]:
    anel = [[x0, y0], [x0 + lado, y0], [x0 + lado, y0 + lado], [x0, y0 + lado], [x0, y0]]
    metrico = PolygonGeometry(type="Polygon", coordinates=[anel])
    return reprojetar(metrico, 31983, 4326).model_dump()


def _laco_em_oito() -> dict[str, object]:
    anel = [
        [-46.6560, -23.5620],
        [-46.6550, -23.5610],
        [-46.6550, -23.5620],
        [-46.6560, -23.5610],
        [-46.6560, -23.5620],
    ]
    return {"type": "Polygon", "coordinates": [anel]}


def _instalar_fetcher_fake(
    monkeypatch: pytest.MonkeyPatch,
    pages: list[WfsFeatureCollection],
    capturado: list[WfsFeatureRequest] | None = None,
) -> None:
    def _fetcher_fake(req: WfsFeatureRequest) -> object:
        if capturado is not None:
            capturado.append(req)
        return iter(pages)

    def _build_fetcher_fake(_settings: object) -> object:
        return _fetcher_fake

    monkeypatch.setattr(views, "build_fetcher", _build_fetcher_fake)


_POST_BASE: dict[str, str] = {
    "lon": "-46.6565",
    "lat": "-23.5631",
    "codlog": "156566",
    "origem": "AVENIDA PAULISTA, 300",
}


# ---------------------------------------------------------------------------
# Encontrou lote: payload com ponto + lote, e a gaveta do lote com o card de distância
# ---------------------------------------------------------------------------


def test_mais_proximo_anonimo_devolve_ponto_lote_e_gaveta_do_lote(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lote = _feat(_PROPS_LOTE, _quadrado(333000.0, 7395000.0, 50.0))
    _instalar_fetcher_fake(monkeypatch, [_page([lote])])

    resposta = client.post(reverse("lotes_mais_proximos:mais_proximo"), _POST_BASE)
    conteudo = resposta.content.decode()

    assert resposta.status_code == 200
    assert 'id="mapa-payload"' in conteudo
    assert conteudo.count('"Feature"') >= 2  # ponto de origem + polígono do lote, no mesmo payload
    assert 'id="gaveta-entidade"' in conteudo
    assert "gaveta-lateral" in conteudo
    assert "Distância do endereço" in conteudo
    assert "AVENIDA PAULISTA, 300" in conteudo


# ---------------------------------------------------------------------------
# Sem lote no raio: aviso com o raio do ambiente
# ---------------------------------------------------------------------------


def test_mais_proximo_sem_lote_responde_aviso_com_raio(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_fetcher_fake(monkeypatch, [_page([])])

    resposta = client.post(reverse("lotes_mais_proximos:mais_proximo"), _POST_BASE)
    conteudo = resposta.content.decode()

    assert resposta.status_code == 200
    assert "alert-warning" in conteudo
    assert "a 50 metros do ponto de busca" in conteudo


# ---------------------------------------------------------------------------
# Lotes do desenho (SPEC localizacao_lote/003): builders
# ---------------------------------------------------------------------------

SLUG_LOTES_INTERSECTADOS = "lotes_mais_proximos.lotes_intersectados"


def _feat_no_mapa(id_poligono: str, x0: float) -> dict[str, object]:
    props = {**_PROPS_LOTE, "cd_identificador": id_poligono, "cd_digito_sql": "5"}
    return _feat(props, _retangulo_no_mapa(x0, 7395000.0, 20.0))


def _postar_lotes_do_desenho(client: Client, geometria: dict[str, object]) -> str:
    resposta = client.post(
        reverse("lotes_mais_proximos:lotes_do_desenho"),
        {"id_bancada": "7", "desenho": json.dumps(geometria)},
    )
    assert resposta.status_code == 200
    return resposta.content.decode()


def _payload(soup: BeautifulSoup) -> dict[str, Any]:
    script = soup.find("script", id="mapa-payload")
    assert isinstance(script, Tag)
    return json.loads(script.get_text())  # type: ignore[no-any-return]


def _toggle_dos_desenhos_recolhido(soup: BeautifulSoup) -> bool:
    toggle = soup.find("input", id="gaveta-desenhos-toggle")
    return isinstance(toggle, Tag) and toggle.has_attr("hx-swap-oob") and not toggle.has_attr("checked")


# ---------------------------------------------------------------------------
# Lotes do desenho: mapa, tabela na gaveta inferior e contexto de ação
# ---------------------------------------------------------------------------


def test_lotes_do_desenho_devolve_mapa_tabela_e_recolhe_os_desenhos(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_fetcher_fake(
        monkeypatch,
        [_page([_feat_no_mapa("1001", 333000.0), _feat_no_mapa("1002", 333020.0)])],
    )

    conteudo = _postar_lotes_do_desenho(client, _retangulo_no_mapa(333000.0, 7395000.0, 40.0))
    soup = BeautifulSoup(conteudo, "html.parser")

    url_detalhe = reverse("lotes_mais_proximos:detalhe_do_lote")
    payload = _payload(soup)
    assert payload["cor"] == settings.MAP_COR_RESULTADO_ACAO
    propriedades = [feature["properties"] for feature in payload["geometria"]["features"]]
    assert [p["id"] for p in propriedades] == ["1001", "1002"]
    assert [p["url_ficha"] for p in propriedades] == [
        f"{url_detalhe}?id=1001",
        f"{url_detalhe}?id=1002",
    ]

    gaveta = soup.find(id="gaveta-inferior-conteudo")
    assert isinstance(gaveta, Tag)
    assert gaveta.has_attr("hx-swap-oob")
    toggle_resultado = gaveta.find("input", id="gaveta-resultado")
    assert isinstance(toggle_resultado, Tag)
    assert toggle_resultado.has_attr("checked")
    placa = gaveta.select_one("aside.gaveta-inferior")
    assert placa is not None
    recolher = placa.find("input", id="gaveta-resultado-recolhida", recursive=False)
    assert isinstance(recolher, Tag)
    assert not recolher.has_attr("checked")
    assert {label["for"] for label in placa.select(".gaveta-alca, .paleta-gaveta-inferior")} == {
        "gaveta-resultado-recolhida"
    }
    assert placa.select_one('header label[aria-label="Fechar"]')["for"] == "gaveta-resultado"  # type: ignore[index]
    assert re.search(r"\b2\s+lotes\b", gaveta.get_text(" ", strip=True))
    linhas = gaveta.select("tr[data-id-feature]")
    assert [linha["data-id-feature"] for linha in linhas] == ["1001", "1002"]
    assert [linha["hx-get"] for linha in linhas] == [p["url_ficha"] for p in propriedades]
    assert {linha["hx-target"] for linha in linhas} == {"#gaveta-entidade"}

    assert _toggle_dos_desenhos_recolhido(soup)

    contexto = soup.find(id="contexto-acao")
    assert isinstance(contexto, Tag)
    assert contexto.has_attr("hx-swap-oob")
    assert contexto["data-contexto-acao"] == SLUG_LOTES_INTERSECTADOS
    assert contexto["data-desenho"] == "7"
    assert contexto["data-encerra-com"] == "#gaveta-resultado"


def test_lotes_do_desenho_recusa_invalido_e_nao_poligono(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capturado: list[WfsFeatureRequest] = []
    _instalar_fetcher_fake(monkeypatch, [_page([])], capturado)

    conteudo = _postar_lotes_do_desenho(client, _laco_em_oito())
    soup = BeautifulSoup(conteudo, "html.parser")
    assert soup.select_one('[role="alert"]') is not None
    assert soup.find("script", id="mapa-payload") is None
    assert _toggle_dos_desenhos_recolhido(soup)

    ponto = {"type": "Point", "coordinates": [-46.6559, -23.5614]}
    resposta = client.post(
        reverse("lotes_mais_proximos:lotes_do_desenho"),
        {"id_bancada": "7", "desenho": json.dumps(ponto)},
    )
    assert resposta.status_code == 422

    assert capturado == []


# ---------------------------------------------------------------------------
# Detalhe do lote: a gaveta do lote da SPEC 001, pelo identificador do polígono
# ---------------------------------------------------------------------------


def test_detalhe_do_lote_abre_a_gaveta_do_lote(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capturado: list[WfsFeatureRequest] = []
    _instalar_fetcher_fake(monkeypatch, [_page([_feat_no_mapa("1001", 333000.0)])], capturado)

    resposta = client.get(reverse("lotes_mais_proximos:detalhe_do_lote"), {"id": "1001"})
    assert resposta.status_code == 200
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")

    raiz = soup.select_one(".gaveta-lateral")
    assert raiz is not None
    assert raiz["data-gaveta"] == "lote-1001"
    assert "SQL 005.003.0048-5" in raiz.get_text()

    cql = capturado[0].cql_filter.to_cql()  # type: ignore[union-attr]
    assert re.search(r"cd_identificador = '?1001'?", cql)
