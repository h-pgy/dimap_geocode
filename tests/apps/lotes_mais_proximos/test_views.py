"""Testes de apps/lotes_mais_proximos/views.py (SPEC localizacao_lote/002): busca do lote mais
próximo do ponto interpolado — rota aberta, sem login (§3.5 do CLAUDE.md)."""

import pytest
from django.test import Client
from django.urls import reverse

import apps.lotes_mais_proximos.views as views
from services.integrations.wfs import WfsFeatureCollection

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


def _instalar_fetcher_fake(
    monkeypatch: pytest.MonkeyPatch,
    pages: list[WfsFeatureCollection],
) -> None:
    def _build_fetcher_fake(_settings: object) -> object:
        return lambda _req: iter(pages)

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
