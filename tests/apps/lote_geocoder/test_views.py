"""Testes de apps/lote_geocoder/views.py (SPEC localizacao_lote/001): a gaveta lateral do lote
resolvido — dados públicos da ontologia do lote, sem login (§3.5 do CLAUDE.md)."""

import re

import pytest
from django.test import Client
from django.urls import reverse

import apps.lote_geocoder.views as views
from services.integrations.wfs import WfsFeatureCollection

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

POLYGON_GEOM: dict[str, object] = {
    "type": "Polygon",
    "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
}

_PROPS_LOTE_COM_SQL: dict[str, object] = {
    "cd_identificador": "POL001",
    "cd_setor_fiscal": "005",
    "cd_quadra_fiscal": "003",
    "cd_lote": "0048",
    "cd_tipo_lote": "F",
    "cd_tipo_quadra": "U",
    "cd_condominio": None,
    "cd_logradouro": "12345",
    "nm_logradouro_completo": "AV PAULISTA",
    "cd_numero_porta": "100",
    "cd_digito_sql": "5",
    "tx_complemento_endereco": None,
    "tx_situ_lote": "ATIVO",
    "dc_tipo_uso_imovel": "RESIDENCIAL VERTICAL",
    "qt_area_terreno": 250.5,
    "qt_area_construida": 120.0,
    "cd_cib": "1234",
}

_POST_LOTE: dict[str, str] = {
    "setor": "005",
    "quadra": "003",
    "lote": "0048",
    "tipo_lote": "F",
}


def _feat(props: dict[str, object]) -> dict[str, object]:
    return {"type": "Feature", "geometry": POLYGON_GEOM, "properties": props}


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


def _toggle_marcado(html: str) -> bool:
    match = re.search(r"<input[^>]*gaveta-lateral-toggle[^>]*>", html)
    return match is not None and "checked" in match.group()


# ---------------------------------------------------------------------------
# Gaveta abre com o SQL do lote resolvido
# ---------------------------------------------------------------------------


def test_geocodificar_lote_abre_gaveta_com_sql(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_fetcher_fake(monkeypatch, [_page([_feat(_PROPS_LOTE_COM_SQL)])])

    resposta = client.post(reverse("lote_geocoder:geocodificar"), _POST_LOTE)
    conteudo = resposta.content.decode()

    assert resposta.status_code == 200
    assert 'id="mapa-payload"' in conteudo
    assert 'id="gaveta-entidade"' in conteudo
    assert "gaveta-lateral" in conteudo
    assert "SQL 005.003.0048-5" in conteudo
    assert "Lançamento ativo" in conteudo
    assert _toggle_marcado(conteudo)


def test_gaveta_mostra_nao_informado_para_atributo_ausente(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    props = {k: v for k, v in _PROPS_LOTE_COM_SQL.items() if k != "qt_area_terreno"}
    _instalar_fetcher_fake(monkeypatch, [_page([_feat(props)])])

    resposta = client.post(reverse("lote_geocoder:geocodificar"), _POST_LOTE)

    assert "não informado" in resposta.content.decode()


def test_lote_sem_contribuinte_nao_inventa_sql(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    props = {k: v for k, v in _PROPS_LOTE_COM_SQL.items() if k != "cd_digito_sql"}
    _instalar_fetcher_fake(monkeypatch, [_page([_feat(props)])])

    resposta = client.post(reverse("lote_geocoder:geocodificar"), _POST_LOTE)
    conteudo = resposta.content.decode()

    assert "Sem contribuinte" in conteudo
    assert "SQL " not in conteudo


# ---------------------------------------------------------------------------
# Sem geometria, sem gaveta
# ---------------------------------------------------------------------------


def test_lote_sem_geometria_nao_abre_gaveta(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_fetcher_fake(monkeypatch, [_page([])])

    resposta = client.post(
        reverse("lote_geocoder:geocodificar"),
        {"setor": "999", "quadra": "999", "lote": "9999", "tipo_lote": "F"},
    )
    conteudo = resposta.content.decode()

    assert resposta.status_code == 200
    assert "alert-warning" in conteudo
    assert 'id="gaveta-entidade"' not in conteudo


# ---------------------------------------------------------------------------
# Rota da SPEC 001 (lote por SQL) segue sem o card de distância (SPEC localizacao_lote/002)
# ---------------------------------------------------------------------------


def test_gaveta_do_lote_sem_distancia_nao_mostra_o_card(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_fetcher_fake(monkeypatch, [_page([_feat(_PROPS_LOTE_COM_SQL)])])

    resposta = client.post(reverse("lote_geocoder:geocodificar"), _POST_LOTE)
    conteudo = resposta.content.decode()

    assert "gaveta-lateral" in conteudo
    assert "Distância do endereço" not in conteudo
