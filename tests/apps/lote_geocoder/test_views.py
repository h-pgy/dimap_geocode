"""Testes de apps/lote_geocoder/views.py (SPEC localizacao_lote/001): a gaveta lateral do lote
resolvido — dados públicos da ontologia do lote, sem login (§3.5 do CLAUDE.md)."""

import re

import pytest
from bs4 import BeautifulSoup, Tag
from django.contrib.sessions.backends.cache import SessionStore
from django.http import HttpRequest
from django.test import Client, RequestFactory
from django.urls import reverse

import apps.acoes_lote.views as acoes_lote_views
import apps.lote_geocoder.views as views
from apps.mapping import views as mapping_views
from apps.unidades.models import CorUnidade, Unidade
from apps.user_admin.models import Perfil
from services.domain.geometry import PolygonGeometry, reprojetar
from services.integrations.wfs import WfsFeatureCollection

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------



def _retangulo_no_mapa(largura: float, altura: float) -> dict[str, object]:
    x0 = 333000.0
    y0 = 7395000.0
    anel = [[x0, y0], [x0 + largura, y0], [x0 + largura, y0 + altura], [x0, y0 + altura], [x0, y0]]
    metrico = PolygonGeometry(type="Polygon", coordinates=[anel])
    return reprojetar(metrico, 31983, 4326).model_dump()


# 600 m² no polígono contra 250,5 m² no cadastro: divergência de +139,5%.
POLYGON_GEOM: dict[str, object] = _retangulo_no_mapa(20.0, 30.0)

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
    consultas: list[object] | None = None,
) -> None:
    def _fetcher_fake(req: object) -> object:
        if consultas is not None:
            consultas.append(req)
        return iter(pages)

    def _build_fetcher_fake(_settings: object) -> object:
        return _fetcher_fake

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
    assert re.search(r'badge-error[^"]*">\s*\+139,5%', conteudo)


def test_gaveta_mostra_nao_informado_para_atributo_ausente(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    props = {k: v for k, v in _PROPS_LOTE_COM_SQL.items() if k != "qt_area_terreno"}
    _instalar_fetcher_fake(monkeypatch, [_page([_feat(props)])])

    resposta = client.post(reverse("lote_geocoder:geocodificar"), _POST_LOTE)
    conteudo = resposta.content.decode()

    assert re.search(r"Divergência</p>\s*<p[^>]*valor-ausente[^>]*>não informado", conteudo)
    assert re.search(r"Cadastro</p>\s*<p[^>]*valor-ausente[^>]*>não informado", conteudo)
    assert re.search(r"Polígono</p>\s*<p[^>]*>600 ", conteudo)


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


# ---------------------------------------------------------------------------
# Histórico da gaveta lateral (SPEC design/021)
# ---------------------------------------------------------------------------

CHAVE_DO_LOTE = "lote-POL001"


def _perfil_com_competencia() -> Perfil:
    # Sem banco: o superusuário recebe o registro inteiro de ações, sem consulta de permissão.
    return Perfil(
        rf="890021",
        nome="Servidor",
        sobrenome="Competente",
        unidade=Unidade(nome="DIMAP-1", cor=CorUnidade.AGUA_700),
        is_superuser=True,
    )


def _pedido_do_perfil(request: HttpRequest, perfil: Perfil, sessao: SessionStore) -> HttpRequest:
    request.user = perfil
    request.session = sessao
    return request


def _soup(conteudo: bytes) -> BeautifulSoup:
    return BeautifulSoup(conteudo.decode(), "html.parser")


def _payload_bruto(soup: BeautifulSoup) -> str:
    script = soup.find("script", id="mapa-payload")
    assert isinstance(script, Tag)
    return script.get_text()


def _gaveta_no_oob(soup: BeautifulSoup) -> Tag:
    oob = soup.find(id="gaveta-entidade")
    assert isinstance(oob, Tag)
    assert oob.has_attr("hx-swap-oob")
    return oob


def test_gaveta_do_lote_entra_no_historico(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_fetcher_fake(monkeypatch, [_page([_feat(_PROPS_LOTE_COM_SQL)])])

    resposta = client.post(reverse("lote_geocoder:geocodificar"), _POST_LOTE)

    raiz = _soup(resposta.content).select_one(".gaveta-lateral")
    assert isinstance(raiz, Tag)
    assert raiz["data-gaveta"] == CHAVE_DO_LOTE
    historico = client.get(reverse("mapping:historico_gaveta"), {"chave": "outra-gaveta"})
    itens = _soup(historico.content).select(".item-historico")
    assert len(itens) == 1
    assert itens[0].select_one('use[href="#glifo-gaveta-lote"]') is not None
    assert itens[0].get_text(strip=True) == "SQL 005.003.0048-5"


def test_devolver_cena_reenvia_gaveta_e_mapa_sem_consultar_a_base(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consultas: list[object] = []
    _instalar_fetcher_fake(monkeypatch, [_page([_feat(_PROPS_LOTE_COM_SQL)])], consultas)
    aberta = _soup(client.post(reverse("lote_geocoder:geocodificar"), _POST_LOTE).content)

    resposta = client.post(reverse("mapping:devolver_cena"), {"chave": CHAVE_DO_LOTE})

    assert resposta.status_code == 200
    devolvida = _soup(resposta.content)
    assert _payload_bruto(devolvida) == _payload_bruto(aberta)
    assert _gaveta_no_oob(devolvida).decode_contents() == _gaveta_no_oob(aberta).decode_contents()
    assert "SQL 005.003.0048-5" in _gaveta_no_oob(devolvida).get_text()
    assert len(consultas) == 1


def test_gaveta_devolvida_pede_as_acoes_de_novo(monkeypatch: pytest.MonkeyPatch) -> None:
    # O router de ações só aceita id de polígono numérico, como o da base.
    props = {**_PROPS_LOTE_COM_SQL, "cd_identificador": "1001"}
    _instalar_fetcher_fake(monkeypatch, [_page([_feat(props)])])
    perfil = _perfil_com_competencia()
    sessao = SessionStore()
    fabrica = RequestFactory()
    abrir = fabrica.post(reverse("lote_geocoder:geocodificar"), _POST_LOTE)
    views.geocodificar(_pedido_do_perfil(abrir, perfil, sessao))

    devolver = fabrica.post(reverse("mapping:devolver_cena"), {"chave": "lote-1001"})
    resposta = mapping_views.devolver_cena(_pedido_do_perfil(devolver, perfil, sessao))

    gaveta = _gaveta_no_oob(_soup(resposta.content))
    carga = gaveta.select_one(f'[hx-trigger="load"][hx-get^="{reverse("acoes_lote:acoes")}"]')
    assert isinstance(carga, Tag)
    assert gaveta.select(".gaveta-lateral-conteudo button") == []
    # Quem abriu tem competência: a carga, pedida agora, é que traz a ação.
    pedir_acoes = fabrica.get(str(carga["hx-get"]))
    acoes = acoes_lote_views.acoes(_pedido_do_perfil(pedir_acoes, perfil, sessao))
    assert _soup(acoes.content).select_one(".poco-acoes button") is not None
