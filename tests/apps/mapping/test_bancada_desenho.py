"""Testes automatizados da SPEC design/018: bancada de desenho no mapa (Leaflet-Geoman)."""

from pathlib import Path
import re

from bs4 import BeautifulSoup
from django.template.loader import render_to_string
from django.test import Client
from django.urls import reverse

REPO_ROOT = Path(__file__).resolve().parents[3]
JS_MAPA_DIR = REPO_ROOT / "static" / "src" / "js" / "mapa"
JS_CATALOGO = JS_MAPA_DIR / "desenho" / "catalogo.js"
JS_INIT = JS_MAPA_DIR / "init.js"
TEMPLATE_BASE = REPO_ROOT / "templates" / "base.html"

GLIFOS_DA_BANCADA = [
    "caixa-ferramentas",
    "ponto",
    "linha",
    "poligono",
    "retangulo",
    "circulo",
    "modificar",
    "vertices",
    "mover",
    "girar",
    "recortar",
    "apagar",
    "ima",
    "check",
    "x",
]
GLIFOS_DO_MAPA = ["camadas", "mapa-base", "satelite", "menos", "mais"]


# ---------------------------------------------------------------------------
# Renderização do partial e da home
# ---------------------------------------------------------------------------


def test_home_traz_a_bancada_de_desenho() -> None:
    resposta = Client().get(reverse("core:home"))
    assert resposta.status_code == 200
    soup = BeautifulSoup(resposta.content.decode("utf-8"), "html.parser")

    conjunto = soup.find(id="bancada-conjunto")
    assert conjunto is not None
    classes = conjunto.get("class", [])
    assert "bancada-conjunto" in classes
    assert "bancada-conjunto--fechada" in classes
    assert conjunto.get("data-dock") == "bottom"

    conteudo_init = JS_INIT.read_text(encoding="utf-8")
    assert 'from "./desenho/bancada.js"' in conteudo_init
    assert "inicializarBancadaDesenho(mapa)" in conteudo_init


def test_bancada_traz_as_categorias_de_geometria() -> None:
    html = render_to_string("mapping/_bancada_desenho.html")
    soup = BeautifulSoup(html, "html.parser")

    categorias = {el["data-categoria"] for el in soup.find_all(attrs={"data-categoria": True})}
    assert {"ponto", "linha", "poligono", "modificar"} <= categorias

    lapis = soup.find(id="btn-editar")
    assert lapis is not None
    assert lapis.get("data-categoria") == "modificar"


def test_poco_da_bancada_nasce_desarmado() -> None:
    html = render_to_string("mapping/_bancada_desenho.html")
    soup = BeautifulSoup(html, "html.parser")

    for id_botao in ("btn-apagar", "btn-concluir", "btn-cancelar"):
        botao = soup.find(id=id_botao)
        assert botao is not None
        assert botao.has_attr("disabled")

    btn_snap = soup.find(id="btn-snap")
    assert btn_snap is not None
    assert "bancada-desenho__controle--ligado" not in btn_snap.get("class", [])


def test_torre_do_encaixe_nasce_fechada_e_desligada() -> None:
    html = render_to_string("mapping/_bancada_desenho.html")
    soup = BeautifulSoup(html, "html.parser")

    torre = soup.find(id="torre-snap")
    assert torre is not None
    assert "torre-snap--fechada" in torre.get("class", [])

    btn_snap = soup.find(id="btn-snap")
    assert btn_snap.get("aria-controls") == "torre-snap"

    toggle = soup.find(id="snap-toggle")
    assert toggle is not None
    assert not toggle.has_attr("checked")


# ---------------------------------------------------------------------------
# Glifos SVG
# ---------------------------------------------------------------------------


def test_glifos_do_desenho_definem_os_simbolos_da_bancada() -> None:
    html = render_to_string("mapping/_glifos_desenho.html")
    soup = BeautifulSoup(html, "html.parser")

    for nome in GLIFOS_DA_BANCADA:
        assert soup.find(id=f"glifo-{nome}") is not None, f"glifo-{nome} não definido"

    for nome in GLIFOS_DO_MAPA:
        assert soup.find(id=f"glifo-{nome}") is None, f"glifo-{nome} redefinido (já é de _glifos_mapa.html)"


# ---------------------------------------------------------------------------
# Catálogo de ferramentas
# ---------------------------------------------------------------------------


def test_catalogo_cobre_as_categorias_do_partial() -> None:
    html = render_to_string("mapping/_bancada_desenho.html")
    soup = BeautifulSoup(html, "html.parser")
    categorias = {el["data-categoria"] for el in soup.find_all(attrs={"data-categoria": True})}

    conteudo_js = JS_CATALOGO.read_text(encoding="utf-8")
    bloco = re.search(r"export const GEOMETRIAS = \{(.*?)\n\};", conteudo_js, re.DOTALL)
    assert bloco is not None
    corpo_geometrias = bloco.group(1)

    for categoria in categorias:
        assert re.search(rf"^\s*{categoria}:", corpo_geometrias, re.MULTILINE), categoria
    assert "remove:" not in corpo_geometrias


# ---------------------------------------------------------------------------
# Toolbar nativa do Geoman desligada
# ---------------------------------------------------------------------------


def test_toolbar_nativa_do_geoman_nunca_e_ligada() -> None:
    for caminho in JS_MAPA_DIR.rglob("*.js"):
        linhas_ativas = [
            linha.strip() for linha in caminho.read_text(encoding="utf-8").splitlines() if not linha.strip().startswith("//")
        ]
        assert not any("addControls" in linha for linha in linhas_ativas), caminho


def test_geoman_carrega_depois_do_leaflet() -> None:
    conteudo = TEMPLATE_BASE.read_text(encoding="utf-8")
    indice_leaflet = conteudo.index('src="https://unpkg.com/leaflet@1.9/dist/leaflet.js"')
    indice_geoman = conteudo.index('src="https://unpkg.com/@geoman-io/leaflet-geoman-free@2.20/dist/leaflet-geoman.min.js"')
    assert indice_geoman > indice_leaflet


# ---------------------------------------------------------------------------
# A bancada não vaza para telas sem mapa
# ---------------------------------------------------------------------------


def test_tela_administrativa_nao_traz_a_bancada() -> None:
    resposta = Client().get(reverse("autenticacao:login"))
    assert resposta.status_code == 200
    soup = BeautifulSoup(resposta.content.decode("utf-8"), "html.parser")
    assert soup.find(id="bancada-conjunto") is None


# ---------------------------------------------------------------------------
# Styleguide
# ---------------------------------------------------------------------------


def test_styleguide_registra_as_pecas_da_bancada() -> None:
    resposta = Client().get(reverse("core:design_system"))
    assert resposta.status_code == 200
    soup = BeautifulSoup(resposta.content.decode("utf-8"), "html.parser")

    assert soup.find(class_="bancada-conjunto") is not None
    for classe in (
        "bancada-alca",
        "bancada-desenho__categoria",
        "bancada-desenho__controle",
        "bancada-submenu__tool",
    ):
        assert soup.find(class_=classe) is not None, classe
