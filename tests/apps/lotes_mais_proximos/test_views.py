"""Testes de apps/lotes_mais_proximos/views.py: busca do lote mais próximo do ponto interpolado
(SPEC localizacao_lote/002) e lotes que cruzam um desenho (SPEC localizacao_lote/003) e a revisão
do conjunto (SPEC localizacao_lote/004) — rotas abertas, sem login (§3.5 do CLAUDE.md)."""

import json
import re
from typing import Any

import pytest
from bs4 import BeautifulSoup, Tag
from django.conf import settings
from django.test import Client
from django.urls import reverse

import apps.lotes_mais_proximos.views as views
from apps.lotes_mais_proximos.sessao import CHAVE_SESSAO, ConjuntoNaSessao
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
    assert placa.select_one('header button[aria-label="Fechar"]') is not None
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
    assert not contexto.has_attr("data-encerra-com")


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


# ---------------------------------------------------------------------------
# Revisão do conjunto (SPEC localizacao_lote/004): builders
# ---------------------------------------------------------------------------

DESENHO_DOS_LOTES = _retangulo_no_mapa(333000.0, 7395000.0, 60.0)


@pytest.fixture(autouse=True)
def _sessao_em_cache(settings: Any) -> None:
    # Sessão em banco pediria PostGIS de pé; o cache em memória guarda o mesmo conjunto sem ele.
    settings.SESSION_ENGINE = "django.contrib.sessions.backends.cache"


def _instalar_fetcher_que_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fetcher_que_falha(_req: WfsFeatureRequest) -> object:
        raise AssertionError("a revisão do conjunto não consulta o GeoServer")

    monkeypatch.setattr(views, "build_fetcher", lambda _settings: _fetcher_que_falha)


def _consultar_tres_lotes(client: Client, monkeypatch: pytest.MonkeyPatch) -> BeautifulSoup:
    lotes = [_feat_no_mapa(id_poligono, x0) for id_poligono, x0 in _TRES_LOTES]
    _instalar_fetcher_com_lotes(monkeypatch, lotes)
    return BeautifulSoup(_postar_lotes_do_desenho(client, DESENHO_DOS_LOTES), "html.parser")


_TRES_LOTES = (("1001", 333000.0), ("1002", 333020.0), ("1003", 333040.0))


def _instalar_fetcher_com_lotes(
    monkeypatch: pytest.MonkeyPatch,
    lotes: list[dict[str, object]],
) -> None:
    _instalar_fetcher_fake(monkeypatch, [_page(lotes)])


def _hx_vals(elemento: Tag) -> dict[str, str]:
    return json.loads(str(elemento["hx-vals"]))  # type: ignore[no-any-return]


def _chave_da_consulta(soup: BeautifulSoup) -> str:
    lixeira = soup.select_one('button[aria-label="Tirar do conjunto"]')
    assert isinstance(lixeira, Tag)
    return _hx_vals(lixeira)["chave"]


def _conjunto_na_sessao(client: Client) -> ConjuntoNaSessao | None:
    bruto = client.session.get(CHAVE_SESSAO)
    return None if bruto is None else ConjuntoNaSessao.model_validate(bruto)


def _revisar(client: Client, url_name: str, dados: dict[str, str]) -> BeautifulSoup:
    resposta = client.post(reverse(f"lotes_mais_proximos:{url_name}"), dados)
    assert resposta.status_code == 200
    return BeautifulSoup(resposta.content.decode(), "html.parser")


def _remover(client: Client, chave: str, id_poligono: str) -> BeautifulSoup:
    return _revisar(client, "remover_do_conjunto", {"chave": chave, "id_poligono": id_poligono})


def _ids_da_tabela(soup: BeautifulSoup) -> list[str]:
    return [str(linha["data-id-feature"]) for linha in soup.select("tr[data-id-feature]")]


def _ids_do_payload(soup: BeautifulSoup) -> list[str]:
    return [f["properties"]["id"] for f in _payload(soup)["geometria"]["features"]]


# ---------------------------------------------------------------------------
# Conjunto guardado na sessão
# ---------------------------------------------------------------------------


def test_lotes_do_desenho_guarda_o_conjunto_na_sessao(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    soup = _consultar_tres_lotes(client, monkeypatch)

    guardado = _conjunto_na_sessao(client)
    assert guardado is not None
    assert len(guardado.conjunto.apurado.lotes) == 3
    assert guardado.conjunto.removidos == frozenset()

    lixeiras = soup.select('button[aria-label="Tirar do conjunto"]')
    assert [_hx_vals(lixeira)["id_poligono"] for lixeira in lixeiras] == ["1001", "1002", "1003"]
    assert {_hx_vals(lixeira)["chave"] for lixeira in lixeiras} == {guardado.chave}

    controles = soup.select_one("#controles-conjunto")
    assert controles is not None
    confirmar_limpar = controles.select_one("#aviso-limpar-lotes .btn-onsen")
    assert confirmar_limpar is not None
    assert confirmar_limpar["hx-post"] == reverse("lotes_mais_proximos:limpar_conjunto")
    assert _hx_vals(confirmar_limpar) == {"chave": guardado.chave}
    assert "3 lotes na tela" in controles.select_one("#aviso-limpar-lotes .badge").get_text()  # type: ignore[union-attr]

    confirmar_fechar = controles.select_one("#aviso-fechar-gaveta .btn-onsen")
    assert confirmar_fechar is not None
    assert confirmar_fechar["hx-post"] == reverse("lotes_mais_proximos:fechar_conjunto")
    assert _hx_vals(confirmar_fechar) == {"chave": guardado.chave}


def test_refazer_a_consulta_recomeca_o_conjunto(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primeira = _consultar_tres_lotes(client, monkeypatch)
    chave_antiga = _chave_da_consulta(primeira)
    _remover(client, chave_antiga, "1002")

    segunda = _consultar_tres_lotes(client, monkeypatch)

    assert _ids_da_tabela(segunda) == ["1001", "1002", "1003"]
    guardado = _conjunto_na_sessao(client)
    assert guardado is not None
    assert guardado.conjunto.removidos == frozenset()
    assert guardado.chave != chave_antiga


# ---------------------------------------------------------------------------
# Lixeira da linha
# ---------------------------------------------------------------------------


def test_remover_devolve_tabela_resumo_e_mapa_sem_o_lote_sem_consultar_o_wfs(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chave = _chave_da_consulta(_consultar_tres_lotes(client, monkeypatch))
    _instalar_fetcher_que_falha(monkeypatch)

    soup = _remover(client, chave, "1002")

    payload = _payload(soup)
    assert payload["enquadrar"] is False
    assert _ids_do_payload(soup) == ["1001", "1003"]

    tabela = soup.select_one("#tabela-conjunto")
    assert tabela is not None
    assert tabela.has_attr("hx-swap-oob")
    assert _ids_da_tabela(BeautifulSoup(str(tabela), "html.parser")) == ["1001", "1003"]

    resumo = soup.select_one("#resumo-conjunto")
    assert resumo is not None
    assert resumo.has_attr("hx-swap-oob")
    assert re.search(r"\b2\s+lotes\b", resumo.get_text(" ", strip=True))

    controles = soup.select_one("#controles-conjunto")
    assert controles is not None
    assert controles.has_attr("hx-swap-oob")
    assert "2 lotes na tela" in controles.select_one("#aviso-limpar-lotes .badge").get_text()  # type: ignore[union-attr]

    assert soup.find(id="gaveta-inferior-conteudo") is None
    assert soup.find(id="contexto-acao") is None


def test_remocoes_acumulam(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    chave = _chave_da_consulta(_consultar_tres_lotes(client, monkeypatch))

    _remover(client, chave, "1001")
    soup = _remover(client, chave, "1003")

    assert _ids_da_tabela(soup) == ["1002"]
    assert _ids_do_payload(soup) == ["1002"]
    guardado = _conjunto_na_sessao(client)
    assert guardado is not None
    assert guardado.conjunto.removidos == frozenset({"1001", "1003"})


def test_remover_ultimo_lote_mostra_falta_do_conjunto(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_fetcher_com_lotes(monkeypatch, [_feat_no_mapa("1001", 333000.0)])
    soup = BeautifulSoup(_postar_lotes_do_desenho(client, DESENHO_DOS_LOTES), "html.parser")
    chave = _chave_da_consulta(soup)

    soup = _remover(client, chave, "1001")

    tabela = soup.select_one("#tabela-conjunto")
    assert tabela is not None
    falta = tabela.select_one(".gaveta-vazia")
    assert falta is not None
    assert "tirados" in falta.get_text()
    assert "não cruza" not in falta.get_text()

    controles = soup.select_one("#controles-conjunto")
    assert controles is not None
    assert "Limpar lotes" not in controles.get_text()
    assert controles.select_one("dialog") is None
    fechar = controles.select_one('button[aria-label="Fechar"]')
    assert fechar is not None
    assert fechar["hx-post"] == reverse("lotes_mais_proximos:fechar_conjunto")


# ---------------------------------------------------------------------------
# Limpar lotes
# ---------------------------------------------------------------------------


def test_limpar_esvazia_o_conjunto_sem_consultar_o_wfs(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chave = _chave_da_consulta(_consultar_tres_lotes(client, monkeypatch))
    _instalar_fetcher_que_falha(monkeypatch)

    soup = _revisar(client, "limpar_conjunto", {"chave": chave})

    assert _payload(soup)["enquadrar"] is False
    assert _ids_do_payload(soup) == []
    tabela = soup.select_one("#tabela-conjunto")
    assert tabela is not None
    assert "tirados" in tabela.select_one(".gaveta-vazia").get_text()  # type: ignore[union-attr]
    guardado = _conjunto_na_sessao(client)
    assert guardado is not None
    assert guardado.chave == chave
    assert guardado.conjunto.removidos == frozenset({"1001", "1002", "1003"})


# ---------------------------------------------------------------------------
# Fechar a gaveta
# ---------------------------------------------------------------------------


def test_fechar_descarta_o_conjunto_e_encerra_o_contexto(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chave = _chave_da_consulta(_consultar_tres_lotes(client, monkeypatch))

    soup = _revisar(client, "fechar_conjunto", {"chave": chave})

    resultado = soup.select_one("#resultado-busca")
    assert resultado is not None
    assert resultado.has_attr("hx-swap-oob")
    assert _payload(soup) == {
        "geometria": {"type": "FeatureCollection", "features": []},
        "cor": settings.MAP_COR_RESULTADO_ACAO,
        "enquadrar": False,
    }
    contexto = soup.find(id="contexto-acao")
    assert isinstance(contexto, Tag)
    assert contexto.has_attr("hx-swap-oob")
    assert not contexto.has_attr("data-contexto-acao")

    assert _conjunto_na_sessao(client) is None
    recusa = _remover(client, chave, "1001")
    assert recusa.select_one('[role="alert"]') is not None


# ---------------------------------------------------------------------------
# Resultado que não é o vigente
# ---------------------------------------------------------------------------


def test_chave_nao_vigente_nao_mexe_no_conjunto_vigente(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _consultar_tres_lotes(client, monkeypatch)
    antes = _conjunto_na_sessao(client)
    dados = {"chave": "de-outra-aba"}

    remocao = _revisar(client, "remover_do_conjunto", {**dados, "id_poligono": "1001"})
    limpeza = _revisar(client, "limpar_conjunto", dados)
    for soup in (remocao, limpeza):
        assert soup.select_one('[role="alert"]') is not None
        assert soup.find("script", id="mapa-payload") is None

    encerramento = _revisar(client, "fechar_conjunto", dados)
    assert encerramento.find("script", id="mapa-payload") is not None

    assert _conjunto_na_sessao(client) == antes
