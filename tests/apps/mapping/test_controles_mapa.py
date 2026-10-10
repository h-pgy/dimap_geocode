"""Testes automatizados da SPEC design/016: controles de mapa Onsen
(pílula de zoom no poço rebaixado e torrezinha vertical de camadas).
"""

from pathlib import Path
import re
import subprocess

from bs4 import BeautifulSoup
from django.template.loader import render_to_string
from django.test import Client
from django.urls import reverse

from apps.mapping.context import contexto_mapa_base
from apps.mapping.models import CamadaBaseItem

REPO_ROOT = Path(__file__).resolve().parents[3]
JS_CRIAR_MAPA = REPO_ROOT / "static" / "src" / "js" / "mapa" / "criar_mapa.js"
JS_CAMADA_BASE = REPO_ROOT / "static" / "src" / "js" / "mapa" / "camada_base.js"
JS_CONTROLES = REPO_ROOT / "static" / "src" / "js" / "mapa" / "controles_mapa.js"


# ---------------------------------------------------------------------------
# Contexto e Ontologia de Camadas
# ---------------------------------------------------------------------------


def test_contexto_mapa_base_inclui_glifos_definidos_em_settings() -> None:
    contexto = contexto_mapa_base()
    bases = contexto["wms"]["bases"]

    assert len(bases) >= 2
    for base in bases:
        item = CamadaBaseItem(**base)
        assert item.glifo != ""
        assert "glifo" in base

    nomes = [b["nome"] for b in bases]
    assert "Ortofoto" in nomes
    assert "Mapa base" in nomes

    ortofoto = next(b for b in bases if b["nome"] == "Ortofoto")
    assert ortofoto["glifo"] == "glifo-satelite"

    mapa_base = next(b for b in bases if b["nome"] == "Mapa base")
    assert mapa_base["glifo"] == "glifo-mapa-base"


# ---------------------------------------------------------------------------
# Inicialização Leaflet sem controles nativos
# ---------------------------------------------------------------------------


def test_mapa_inicializa_sem_controles_nativos_leaflet() -> None:
    conteudo_criar = JS_CRIAR_MAPA.read_text(encoding="utf-8")
    assert re.search(r"zoomControl:\s*false", conteudo_criar) is not None

    conteudo_base = JS_CAMADA_BASE.read_text(encoding="utf-8")
    # L.control.layers não pode ser chamado em camada_base.js (substituído pela torrezinha Onsen)
    linhas_ativas = [
        linha.strip()
        for linha in conteudo_base.splitlines()
        if not linha.strip().startswith("//")
    ]
    assert not any("L.control.layers" in linha for linha in linhas_ativas)


# ---------------------------------------------------------------------------
# Renderização do Partial de Controles
# ---------------------------------------------------------------------------


def test_partial_controles_mapa_renderiza_estrutura_completa() -> None:
    contexto = contexto_mapa_base()
    html = render_to_string("mapping/_controles_mapa.html", contexto)
    soup = BeautifulSoup(html, "html.parser")

    container = soup.find(id="controles-mapa")
    assert container is not None
    classes = container.get("class", [])
    assert "pilula-mapa" in classes
    assert "moldura-fixa" in classes
    assert "pointer-events-auto" in classes
    assert container.get("role") == "region"
    assert container.get("aria-label") == "Controles do mapa"


def test_poco_zoom_renderiza_botoes_menos_e_mais() -> None:
    contexto = contexto_mapa_base()
    html = render_to_string("mapping/_controles_mapa.html", contexto)
    soup = BeautifulSoup(html, "html.parser")

    poco = soup.find(class_="pilula-mapa__zoom")
    assert poco is not None
    assert "card-well" in poco.get("class", [])

    btn_out = poco.find(id="btn-mapa-zoom-out")
    assert btn_out is not None
    assert "pilula-mapa__btn-zoom" in btn_out.get("class", [])
    use_out = btn_out.find("use")
    assert use_out is not None
    assert use_out.get("href") == "#glifo-menos"

    btn_in = poco.find(id="btn-mapa-zoom-in")
    assert btn_in is not None
    assert "pilula-mapa__btn-zoom" in btn_in.get("class", [])
    use_in = btn_in.find("use")
    assert use_in is not None
    assert use_in.get("href") == "#glifo-mais"


def test_gatilho_camadas_possui_atributos_acessibilidade() -> None:
    contexto = contexto_mapa_base()
    html = render_to_string("mapping/_controles_mapa.html", contexto)
    soup = BeautifulSoup(html, "html.parser")

    btn = soup.find(id="btn-alternar-camadas")
    assert btn is not None
    assert "pilula-mapa__btn-camadas" in btn.get("class", [])
    assert btn.get("aria-expanded") == "false"
    assert btn.get("aria-haspopup") == "true"
    assert btn.get("aria-controls") == "torre-camadas"


def test_torre_camadas_renderiza_todas_as_bases_configuradas() -> None:
    contexto = contexto_mapa_base()
    html = render_to_string("mapping/_controles_mapa.html", contexto)
    soup = BeautifulSoup(html, "html.parser")

    torre = soup.find(id="torre-camadas")
    assert torre is not None
    assert "torre-camadas" in torre.get("class", [])
    assert "torre-camadas--fechada" in torre.get("class", [])
    assert torre.get("role") == "menu"

    itens = torre.find_all(class_="torre-camadas__item")
    assert len(itens) == len(contexto["wms"]["bases"])

    for item, base in zip(itens, contexto["wms"]["bases"]):
        assert item.get("data-camada-nome") == base["nome"]
        rotulo = item.find(class_="torre-camadas__rotulo")
        assert rotulo is not None
        assert base["nome"] in rotulo.get_text()
        glifo = item.find(class_="torre-camadas__glifo")
        assert glifo is not None
        use = glifo.find("use")
        assert use.get("href") == f"#{base.get('glifo', 'glifo-mapa-base')}"


def test_torre_camadas_marca_primeira_base_como_ativa_e_demais_como_secundaria() -> None:
    contexto = contexto_mapa_base()
    html = render_to_string("mapping/_controles_mapa.html", contexto)
    soup = BeautifulSoup(html, "html.parser")

    torre = soup.find(id="torre-camadas")
    assert torre is not None
    itens = torre.find_all(class_="torre-camadas__item")
    assert len(itens) >= 2

    # Primeira base é ativa
    primeiro = itens[0]
    assert "torre-camadas__item--ativo" in primeiro.get("class", [])
    assert primeiro.get("aria-checked") == "true"

    # Demais bases são inativas
    for item in itens[1:]:
        assert "torre-camadas__item--ativo" not in item.get("class", [])
        assert item.get("aria-checked") == "false"


# ---------------------------------------------------------------------------
# Glifos SVG e Home
# ---------------------------------------------------------------------------


def test_glifos_mapa_disponibilizam_icones_camadas_satelite_e_vetorial() -> None:
    html = render_to_string("mapping/_glifos_mapa.html")
    soup = BeautifulSoup(html, "html.parser")

    assert soup.find(id="glifo-camadas") is not None
    assert soup.find(id="glifo-mapa-base") is not None
    assert soup.find(id="glifo-satelite") is not None
    assert soup.find(id="glifo-menos") is not None


def test_home_inclui_partial_controles_mapa() -> None:
    client = Client()
    resposta = client.get(reverse("core:home"))
    assert resposta.status_code == 200

    html = resposta.content.decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")

    assert soup.find(id="controles-mapa") is not None
    assert soup.find(id="btn-alternar-camadas") is not None
    assert soup.find(id="btn-mapa-zoom-in") is not None
    assert soup.find(id="btn-mapa-zoom-out") is not None
    assert soup.find(id="torre-camadas") is not None
    assert soup.find(id="glifo-camadas") is not None


# ---------------------------------------------------------------------------
# Comportamentos JS validados via execução em Node
# ---------------------------------------------------------------------------


def _executar_js_controles(snippet: str) -> str:
    codigo_js = JS_CONTROLES.read_text(encoding="utf-8")
    # Wrap with minimal mock DOM environment in node
    script = f"""
    const jsSource = {repr(codigo_js)};

    // Mock DOM environment
    class Element {{
      constructor(id = '', tag = 'div') {{
        this.id = id;
        this.tagName = tag.toUpperCase();
        this.classList = new Set();
        const self = this;
        this.classList.add = function(c) {{ Set.prototype.add.call(self.classList, c); }};
        this.classList.remove = function(c) {{ Set.prototype.delete.call(self.classList, c); }};
        this.classList.contains = function(c) {{ return Set.prototype.has.call(self.classList, c); }};
        this.classList.toggle = function(c, val) {{
          if (val === undefined) val = !self.classList.contains(c);
          if (val) self.classList.add(c); else self.classList.remove(c);
          return val;
        }};
        this.attributes = {{}};
        this.listeners = {{}};
        this.disabled = false;
        this.dataset = {{}};
      }}
      setAttribute(k, v) {{ this.attributes[k] = String(v); }}
      getAttribute(k) {{ return this.attributes[k]; }}
      addEventListener(evt, fn) {{
        if (!this.listeners[evt]) this.listeners[evt] = [];
        this.listeners[evt].push(fn);
      }}
      dispatchEvent(evt) {{
        if (this.listeners[evt.type]) {{
          this.listeners[evt.type].forEach(fn => fn(evt));
        }}
      }}
      contains(target) {{ return false; }}
    }}

    const elements = {{}};
    function getElementById(id) {{
      return elements[id] || null;
    }}

    elements['controles-mapa'] = new Element('controles-mapa');
    elements['btn-mapa-zoom-in'] = new Element('btn-mapa-zoom-in', 'button');
    elements['btn-mapa-zoom-out'] = new Element('btn-mapa-zoom-out', 'button');
    elements['btn-alternar-camadas'] = new Element('btn-alternar-camadas', 'button');
    elements['torre-camadas'] = new Element('torre-camadas');

    const item1 = new Element('item1', 'button');
    item1.dataset.camadaNome = 'Ortofoto';
    item1.classList.add('torre-camadas__item');
    item1.classList.add('torre-camadas__item--ativo');

    const item2 = new Element('item2', 'button');
    item2.dataset.camadaNome = 'Mapa base';
    item2.classList.add('torre-camadas__item');

    elements['torre-camadas'].querySelectorAll = (sel) => [item1, item2];

    const documentListeners = {{}};
    const doc = {{
      getElementById,
      addEventListener: (evt, fn) => {{
        if (!documentListeners[evt]) documentListeners[evt] = [];
        documentListeners[evt].push(fn);
      }},
      dispatchEvent: (evt) => {{
        if (documentListeners[evt.type]) {{
          documentListeners[evt.type].forEach(fn => fn(evt));
        }}
      }}
    }};

    // Mock mapa Leaflet
    let currentZoom = 14;
    const mapListeners = {{}};
    const mapContainer = new Element('map-container');
    const mapa = {{
      getZoom: () => currentZoom,
      setZoom: (z) => {{ currentZoom = z; if (mapListeners['zoomend']) mapListeners['zoomend'].forEach(f => f()); }},
      getMinZoom: () => 13,
      getMaxZoom: () => 18,
      zoomIn: () => {{ currentZoom++; if (mapListeners['zoomend']) mapListeners['zoomend'].forEach(f => f()); }},
      zoomOut: () => {{ currentZoom--; if (mapListeners['zoomend']) mapListeners['zoomend'].forEach(f => f()); }},
      getContainer: () => mapContainer,
      on: (evt, fn) => {{
        if (!mapListeners[evt]) mapListeners[evt] = [];
        mapListeners[evt].push(fn);
      }},
      hasLayer: () => true,
      removeLayer: () => {{}},
      addLayer: () => {{}}
    }};

    const baseMaps = {{
      'Ortofoto': {{ addTo: () => {{}} }},
      'Mapa base': {{ addTo: () => {{}} }}
    }};

    // Avaliar módulo
    const timers = [];
    const evalEnv = {{
      document: doc,
      clearTimeout: (id) => {{
        const idx = timers.findIndex(t => t.id === id);
        if (idx !== -1) timers.splice(idx, 1);
      }},
      setTimeout: (fn, delay) => {{
        const id = timers.length + 1;
        timers.push({{ id, fn }});
        return id;
      }},
      rodarTimers: () => {{
        const pendentes = timers.slice();
        timers.length = 0;
        pendentes.forEach(t => t.fn());
      }}
    }};

    // Extrair função inicializarControlesMapa
    const moduleCode = jsSource.replace('export function inicializarControlesMapa', 'function inicializarControlesMapa');
    const fnRunner = new Function('document', 'clearTimeout', 'setTimeout', 'mapa', 'baseMaps', 'elements', 'item1', 'item2', 'mapContainer', 'evalEnv',
      moduleCode + "\\ninicializarControlesMapa(mapa, baseMaps);\\n" + {repr(snippet)}
    );

    const result = fnRunner(doc, evalEnv.clearTimeout, evalEnv.setTimeout, mapa, baseMaps, elements, item1, item2, mapContainer, evalEnv);
    console.log(JSON.stringify(result));
    """
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    return res.stdout.strip()


def test_botoes_zoom_refletem_teto_e_piso_do_mapa() -> None:
    res = _executar_js_controles("""
      // No início zoom=14: nenhum disabled
      const inicio = { in: elements['btn-mapa-zoom-in'].disabled, out: elements['btn-mapa-zoom-out'].disabled };

      // Vai ao teto: zoom=18
      mapa.setZoom(18);
      const noTeto = { in: elements['btn-mapa-zoom-in'].disabled, out: elements['btn-mapa-zoom-out'].disabled };

      // Vai ao piso: zoom=13
      mapa.setZoom(13);
      const noPiso = { in: elements['btn-mapa-zoom-in'].disabled, out: elements['btn-mapa-zoom-out'].disabled };

      return { inicio, noTeto, noPiso };
    """)
    import json
    dados = json.loads(res)
    assert dados["inicio"] == {"in": False, "out": False}
    assert dados["noTeto"] == {"in": True, "out": False}
    assert dados["noPiso"] == {"in": False, "out": True}


def test_rolagem_mouse_sobre_mapa_aciona_classe_swell_no_zoom_correspondente() -> None:
    res = _executar_js_controles("""
      // Simula wheel deltaY < 0 (aproximação)
      mapContainer.dispatchEvent({ type: 'wheel', deltaY: -100 });
      const swellIn = elements['btn-mapa-zoom-in'].classList.contains('pilula-mapa__btn-zoom--swell');
      evalEnv.rodarTimers();
      const swellInApos = elements['btn-mapa-zoom-in'].classList.contains('pilula-mapa__btn-zoom--swell');

      // Simula wheel deltaY > 0 (afastamento)
      mapContainer.dispatchEvent({ type: 'wheel', deltaY: 100 });
      const swellOut = elements['btn-mapa-zoom-out'].classList.contains('pilula-mapa__btn-zoom--swell');
      evalEnv.rodarTimers();
      const swellOutApos = elements['btn-mapa-zoom-out'].classList.contains('pilula-mapa__btn-zoom--swell');

      return { swellIn, swellInApos, swellOut, swellOutApos };
    """)
    import json
    dados = json.loads(res)
    assert dados["swellIn"] is True
    assert dados["swellInApos"] is False
    assert dados["swellOut"] is True
    assert dados["swellOutApos"] is False


def test_torre_camadas_sincroniza_hover_bidirecional() -> None:
    res = _executar_js_controles("""
      item1.dispatchEvent({ type: 'mouseenter' });
      const comHover1 = elements['torre-camadas'].classList.contains('has-item-hover');

      item1.dispatchEvent({ type: 'mouseleave' });
      const semHover1 = elements['torre-camadas'].classList.contains('has-item-hover');

      item2.dispatchEvent({ type: 'mouseenter' });
      const comHover2 = elements['torre-camadas'].classList.contains('has-item-hover');

      item2.dispatchEvent({ type: 'mouseleave' });
      const semHover2 = elements['torre-camadas'].classList.contains('has-item-hover');

      return { comHover1, semHover1, comHover2, semHover2 };
    """)
    import json
    dados = json.loads(res)
    assert dados["comHover1"] is True
    assert dados["semHover1"] is False
    assert dados["comHover2"] is True
    assert dados["semHover2"] is False
