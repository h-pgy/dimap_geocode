"""Testes da SPEC design/021: as rotas `mapping:historico_gaveta` e `mapping:devolver_cena`, a
sessão que guarda o histórico e a marca do que troca a cena."""

import json

import pytest
from bs4 import BeautifulSoup, Tag
from django.test import Client
from django.urls import reverse

import apps.acoes_lote.views as acoes_lote_views
import apps.lotes_mais_proximos.views as lotes_views
from apps.acoes_lote.declaradas import ACOES_LOTE
from apps.mapping.historico_gaveta import CHAVE_SESSAO, abrir_no_historico
from services.domain.geometry import PolygonGeometry, reprojetar
from services.domain.historico_gaveta import Cena, Etiqueta, ItemHistorico, TipoGaveta
from services.integrations.wfs import WfsFeatureCollection

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


def _item(chave: str) -> ItemHistorico:
    etiqueta = Etiqueta(chave=chave, tipo=TipoGaveta.LOTE, resumo=f"SQL {chave}")
    gaveta = f'<div class="gaveta-lateral" data-gaveta="{chave}"></div>'
    mapa = {
        "geometria": {"type": "FeatureCollection", "features": []},
        "cor": "#D84F7F",
        "enquadrar": True,
    }
    return ItemHistorico(etiqueta=etiqueta, cena=Cena(gaveta=gaveta, mapa=mapa))


def _abrir_na_sessao(client: Client, item: ItemHistorico) -> None:
    sessao = client.session
    abrir_no_historico(sessao, item)
    sessao.save()


def _historico(client: Client, chave_na_tela: str) -> BeautifulSoup:
    resposta = client.get(reverse("mapping:historico_gaveta"), {"chave": chave_na_tela})
    assert resposta.status_code == 200
    return BeautifulSoup(resposta.content.decode(), "html.parser")


def _voltar(soup: BeautifulSoup) -> Tag:
    botao = soup.select_one(".voltar-gaveta > button")
    assert isinstance(botao, Tag)
    return botao


def _destino(gatilho: Tag) -> str:
    assert gatilho["hx-post"] == reverse("mapping:devolver_cena")
    vals: dict[str, str] = json.loads(str(gatilho["hx-vals"]))
    return vals["chave"]


def _retangulo_no_mapa(lado: float) -> dict[str, object]:
    x0 = 333000.0
    y0 = 7395000.0
    anel = [[x0, y0], [x0 + lado, y0], [x0 + lado, y0 + lado], [x0, y0 + lado], [x0, y0]]
    metrico = PolygonGeometry(type="Polygon", coordinates=[anel])
    return reprojetar(metrico, 31983, 4326).model_dump()


def _lote_no_mapa() -> dict[str, object]:
    props = {
        "cd_identificador": "1001",
        "cd_setor_fiscal": "005",
        "cd_quadra_fiscal": "003",
        "cd_lote": "0048",
        "cd_tipo_lote": "F",
        "cd_digito_sql": "5",
    }
    return {"type": "Feature", "geometry": _retangulo_no_mapa(20.0), "properties": props}


def _instalar_fetcher_de_lotes(monkeypatch: pytest.MonkeyPatch) -> None:
    pagina = WfsFeatureCollection.model_validate(
        {"type": "FeatureCollection", "numberMatched": 1, "features": [_lote_no_mapa()]}
    )
    monkeypatch.setattr(lotes_views, "build_fetcher", lambda _settings: lambda _req: iter([pagina]))


def _dar_competencia_sobre_o_lote(monkeypatch: pytest.MonkeyPatch) -> None:
    slugs = frozenset(item.acao.acao.slug for item in ACOES_LOTE.itens)
    monkeypatch.setattr(acoes_lote_views, "slugs_liberados", lambda _usuario: slugs)


def _dentro_da_trava(peca: Tag) -> bool:
    return peca.find_parent(attrs={"data-troca-cena": True}) is not None


# ---------------------------------------------------------------------------
# O voltar
# ---------------------------------------------------------------------------


def test_voltar_alterna_entre_as_duas_ultimas(client: Client) -> None:
    _abrir_na_sessao(client, _item("lote-1"))

    primeira = _historico(client, "lote-1")

    assert _voltar(primeira).has_attr("disabled")
    assert not _voltar(primeira).has_attr("hx-post")
    assert primeira.select(".item-historico") == []

    _abrir_na_sessao(client, _item("lote-2"))

    assert _destino(_voltar(_historico(client, "lote-2"))) == "lote-1"

    client.post(reverse("mapping:devolver_cena"), {"chave": "lote-1"})

    assert _destino(_voltar(_historico(client, "lote-1"))) == "lote-2"


def test_cena_fora_do_historico_vira_aviso(client: Client) -> None:
    resposta = client.post(reverse("mapping:devolver_cena"), {"chave": "lote-999"})

    assert resposta.status_code == 200
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")
    assert soup.select_one('[role="alert"]') is not None
    assert soup.find(id="mapa-payload") is None
    assert soup.find(id="gaveta-entidade") is None


# ---------------------------------------------------------------------------
# A trava
# ---------------------------------------------------------------------------


def test_o_que_troca_a_cena_declara_a_trava(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _abrir_na_sessao(client, _item("lote-1"))
    _abrir_na_sessao(client, _item("lote-2"))

    canto = _historico(client, "lote-2")

    assert _dentro_da_trava(_voltar(canto))
    itens = canto.select(".item-historico")
    assert len(itens) == 1
    assert all(_dentro_da_trava(item) for item in itens)
    dica_do_voltar = canto.select_one(".dica-trava")
    assert isinstance(dica_do_voltar, Tag)
    assert not _dentro_da_trava(dica_do_voltar)

    desenhos = client.post(
        reverse("mapping:desenhos_da_bancada"),
        {
            "desenhos": json.dumps([{"id_bancada": "2", "geometria": POLIGONO_GEOJSON}]),
            "selecionado": "2",
        },
    )
    poco = BeautifulSoup(desenhos.content.decode(), "html.parser").select_one(".poco-desenhos")
    assert isinstance(poco, Tag)
    acoes_do_poco = poco.select("button[hx-post]")
    assert acoes_do_poco
    assert all(_dentro_da_trava(acao) for acao in acoes_do_poco)
    dica_do_poco = poco.select_one(".dica-trava")
    assert isinstance(dica_do_poco, Tag)
    assert not _dentro_da_trava(dica_do_poco)

    _instalar_fetcher_de_lotes(monkeypatch)
    resultado = client.post(
        reverse("lotes_mais_proximos:lotes_do_desenho"),
        {"id_bancada": "2", "desenho": json.dumps(_retangulo_no_mapa(60.0))},
    )
    inferior = BeautifulSoup(resultado.content.decode(), "html.parser")
    assert inferior.select_one('button[aria-label="Tirar do conjunto"]') is not None
    assert inferior.select("[data-troca-cena]") == []

    _dar_competencia_sobre_o_lote(monkeypatch)
    acoes = client.get(reverse("acoes_lote:acoes"), {"sql": "005.003.0048-5", "id": "1001"})
    poco_do_lote = BeautifulSoup(acoes.content.decode(), "html.parser")
    assert poco_do_lote.select_one(".poco-acoes button") is not None
    assert poco_do_lote.select("[data-troca-cena]") == []


# ---------------------------------------------------------------------------
# A sessão
# ---------------------------------------------------------------------------


def test_sessao_de_outro_formato_recomeca_vazia(client: Client) -> None:
    sessao = client.session
    sessao[CHAVE_SESSAO] = {"itens": [{"chave": "lote-1", "html": "<div></div>"}]}
    sessao.save()

    resposta = client.post(
        reverse("mapping:desenhos_da_bancada"),
        {"desenhos": json.dumps([{"id_bancada": "1", "geometria": PONTO_GEOJSON}])},
    )

    assert resposta.status_code == 200
    gaveta = BeautifulSoup(resposta.content.decode(), "html.parser")
    assert gaveta.select_one('.gaveta-lateral[data-gaveta="desenhos"]') is not None
    resumos = [
        item.get_text(strip=True) for item in _historico(client, "lote-1").select(".item-historico")
    ]
    assert resumos == ["1 desenho"]
