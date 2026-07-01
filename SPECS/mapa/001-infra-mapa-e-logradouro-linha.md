---
spec: mapa/001
versao: v3
atualizado_em: 2026-07-01
implementado: false
changelog:
  - v1: versão inicial
  - v2: WMS base concretizado (URL/camada ortofoto/versão do GeoSampa) e versão do WMS injetada via settings (não hardcoded no JS); fronteira explícita — o fundo do Leaflet é um `L.tileLayer.wms` direto, NÃO o `services/integrations/wms` (esse puxa imagens GetMap server-side, outro caso de uso)
  - v3: duas camadas base (ortofoto `geoportal:ORTO_RGB_2020` + mapa base político `geoportal:MapaBase_Politico`) num `L.control.layers` (radio); config do WMS passa a carregar uma LISTA de bases nomeadas (a 1ª visível por padrão), com nomes vindos de settings (nada hardcoded no JS)
  - v4: URL por base — a ortofoto é servida por um WMS de RASTER em outro domínio (`WMS_RASTER_URL`), não pelo WMS geral. Cada entrada de `WMS_BASES` pode ter uma chave `url` própria; o JS resolve `b.url || wms.url` (patch 001)
  - v5: `minZoom` do `L.map` sobe de 10 para 13 — a base ortofoto não tem cobertura em zooms mais baixos (patch 002)
---

# SPEC mapa/001 — Infra do mapa + plotagem de logradouro (codlog → linha no Leaflet)

- [X] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como visitante da aplicação, quero que, ao escolher um logradouro nas sugestões da busca, a **linha**
do logradouro apareça desenhada num mapa Leaflet sobre o WMS do GeoSampa — com popup e rótulo —, para
que eu veja onde aquele logradouro está sem precisar de login.

## Critérios de aceite

### Infra de mapa (reusável por logradouro, lote e, no futuro, endereço)
- [ ] Existe um app fino **`mapping`** que **centraliza a renderização do mapa**: dono do *partial*
      Leaflet, de um **helper de contexto** que monta o que o partial precisa, e do **JS centralizado**
      em `static/`. `mapping` é **agnóstico de domínio** — não importa `logradouro_geocod`/`lote_geocod`
      nem conhece codlog/contribuinte; recebe **geometria já pronta (GeoJSON 4326) + cor** e devolve o
      partial. (§6 — app `mapping`.)
- [ ] O *partial* do `mapping` emite **apenas** o container `div#map` (com altura explícita via classe
      Tailwind) e os **dados do servidor** via `json_script` (config do WMS + payload do mapa:
      geometria, cor, centro/zoom de fallback). **Não** contém `<script>` inline com lógica — toda a
      lógica JS está centralizada em `static/` (ver abaixo).
- [ ] A **config do WMS** (URL + **versão** + **lista de bases nomeadas**) e o **centro/zoom default** são
      lidos de `settings` pelo app `mapping` (orquestração) e injetados no contexto — **nada hardcoded no
      JS**, **inclusive a `version` e os nomes das bases** (§11, skill `leaflet-map`). Valores do
      GeoSampa: `WMS_URL = "https://wms.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/ows"`,
      `WMS_VERSION = "1.3.0"` e **duas camadas base**: ortofoto `geoportal:ORTO_RGB_2020` e mapa base
      político `geoportal:MapaBase_Politico`.
- [ ] As duas bases entram num **`L.control.layers`** (controle de camadas do Leaflet; bases mutuamente
      exclusivas — *radio*), permitindo alternar entre ortofoto e mapa base. **A 1ª base da lista é a
      visível por padrão** (`addTo(map)`); a ordem (e portanto o default) vem de `settings`.
- [ ] O fundo do mapa é um **`L.tileLayer.wms` direto** (cliente Leaflet → WMS do GeoSampa), **um por
      base**, montado no JS a partir da config injetada. **NÃO** se usa aqui o `services/integrations/wms`
      (`WmsFetcher`):
      aquele integrador puxa **imagens** via GetMap **server-side** (outro caso de uso) e não tem papel
      no tile layer do Leaflet. A config do WMS para o Leaflet são **dados de `settings`**, não uma
      chamada ao integrador.
- [ ] O **CRS de saída para o mapa é 4326** (constante única em `settings`, ex.: `MAP_OUTPUT_CRS`),
      injetado pela orquestração no DTO de entrada do geocoder de domínio. O JS **nunca** reprojeta
      (§7.3, §11).

### JavaScript centralizado e modular (`static/`)
- [ ] Todo o JS do mapa vive **centralizado em `static/`** (servido via *staticfiles*), **modularizado
      por responsabilidade única** e integrado por **composição** — espelhando os princípios que regem o
      Python (§10.1, §10.4). Cada módulo é uma função pequena com uma só responsabilidade; um módulo de
      entrada **compõe** os demais. Nada de um arquivão com tudo dentro.
- [ ] Os módulos cobrem, separadamente: **(a)** instanciar o mapa (centro/zoom), **(b)** adicionar a
      camada base WMS, **(c)** adicionar a camada de resultado (GeoJSON → estilo por cor, popup, tooltip,
      `fitBounds`) e **(d)** um módulo de **entrada/composição** que lê os `json_script` e chama (a)→(c).
- [ ] O JS respeita §11: **só cola para o Leaflet** — sem regra de negócio, sem estado, sem montar UI a
      partir de JSON. O `popup_html` e o `rotulo` chegam **prontos do servidor** dentro das `properties`
      de cada *feature*; o JS apenas os entrega a `bindPopup`/`bindTooltip`. A geometria é GeoJSON 4326 e
      renderiza via `L.geoJSON` (sem parsing manual de coordenadas).
- [ ] Como o mapa entra na página por **swap do HTMX** (a resposta é trocada em `#resultado-busca`), a
      inicialização do mapa é disparada por um **callback de evento do HTMX** (`htmx.onLoad`/
      `htmx:afterSwap`) — caso (1) de §11 — registrado **uma única vez** (carregado no `base.html`). O
      callback detecta um `div#map` recém-inserido e compõe o mapa a partir dos `json_script` daquele
      container. O *partial* não traz `<script>` de init.

### Serialização de geometria (centralizada no pacote de geometria)
- [ ] O pacote `services/domain/geometry/` ganha um **serializador genérico** que converte uma lista de
      `GeoFeature` numa **GeoJSON `FeatureCollection`** (formato de fronteira para o Leaflet). É
      **agnóstico ao tipo** (linha/polígono/ponto) e reusável por logradouro, lote e endereço — a
      representação de geometria continua **centralizada** no pacote, não espalhada pelos apps (§7.3).
- [ ] O serializador mantém a fronteira de responsabilidades: ele monta o **envelope GeoJSON**
      (`FeatureCollection`/`Feature`/`geometry`); as **`properties` de apresentação** (`popup_html`,
      `rotulo`) são fornecidas **pelo app** (presentation), via uma função injetada — o pacote de
      geometria não renderiza HTML.

### Consumo pelo domínio próprio (app `logradouro_geocoder`)
- [ ] Existe um app **`logradouro_geocoder`** (novo, **distinto** do `logradouro_matcher`) cuja view
      **orquestra** a plotagem do logradouro: recebe o `codlog` escolhido (POST), lê `settings`
      (conexão WFS + `WFS_LAYER_LOGRADOUROS` + `MAP_OUTPUT_CRS` + cor da linha), **constrói o
      `WfsFetcher`**, monta o DTO `LogradouroGeocodInput` e chama o domínio
      `services/domain/logradouro_geocod` por composição. **Nenhuma** regra de negócio na view (§3, §6).
- [ ] A view converte a saída do domínio (`list[SegmentoLogradouroFeature]`) em GeoJSON via o
      serializador do pacote de geometria, **renderiza o `popup_html` por *feature*** (template do
      próprio app, a partir dos `attributes` do segmento) e o `rotulo` (nome do logradouro), escolhe a
      **cor de linha** (de `settings`) e delega ao `mapping` a renderização do partial do mapa.
- [ ] A **sugestão de logradouro** (item da lista de resultados do `logradouro_matcher`) passa a
      **acionar o geocoder**: o `hx-post` do item aponta para a view do `logradouro_geocoder`
      (alvo `#resultado-busca`), substituindo o *stub* de seleção atual. O resultado renderizado é o
      mapa com a linha.
- [ ] Visitante **anônimo** vê o mapa normalmente (a busca avulsa é pública — §1/§9); nenhuma exigência
      de login nesta SPEC.
- [ ] Tipagem estrita compatível com `mypy`; sem `from __future__`. Convenções de §10/§11 respeitadas.

## Contexto e decisões de arquitetura

Esta é a primeira SPEC do épico **`mapa`**: levar um resultado de geocodificação de domínio até a tela,
desenhado no Leaflet. Ela mexe nas **duas pontas Django** (views de orquestração + templates/partials +
JS estático) e acrescenta **uma peça de serialização** ao domínio de geometria — sem tocar em regra de
negócio de matching/geocodificação (essa já existe em `services/domain/*_geocod`).

**Três responsabilidades, três lugares (§10.1).**
1. **Renderizar o mapa** é responsabilidade do app `mapping` — partial + helper de contexto + JS
   centralizado. Ele é **agnóstico de domínio**: só sabe de geometria GeoJSON 4326, cor e WMS. É o
   "como desenhar", reusável por qualquer resultado (linha, polígono, ponto).
2. **Orquestrar a busca de logradouro → mapa** é do app `logradouro_geocoder` (novo). É quem lê
   `settings`, monta o `WfsFetcher`, chama o domínio `logradouro_geocod` e decide o que mandar pro
   `mapping`. Fica **separado do `logradouro_matcher`** (que cuida das sugestões/matching) porque são
   responsabilidades distintas: *sugerir* × *geocodificar e plotar*. O mesmo vale para lote (SPEC 002).
3. **A lógica de geocodificação** já está em `services/domain/logradouro_geocod` (geocodificacao/001) —
   aqui é só **composta**, não reescrita.

**Por que `mapping` não conhece domínio.** Se `mapping` importasse `logradouro_geocod`/`lote_geocod`, ele
cruzaria domínios (§10.1) e deixaria de ser reusável. A fronteira é: o app de domínio entrega ao
`mapping` uma **GeoJSON `FeatureCollection` 4326 + cor + (popup/rótulo já dentro das properties)**; o
`mapping` só envolve isso no partial e injeta a config do WMS. Assim, quando a SPEC 002 (lote) e a futura
de endereço chegarem, elas **reusam o mesmo `mapping`** sem alterá-lo.

**Serialização de geometria no pacote, não no app.** A conversão `GeoFeature → GeoJSON` é
**representação de geometria** e por isso mora no pacote centralizado `services/domain/geometry/`
(§7.3 — "não espalhar formatos de geometria pelo código"), genérica e reusável pelos três fluxos. O que
**não** é geometria — o `popup_html` (HTML renderizado) e o `rotulo` — é **apresentação** e fica no app,
injetado como `properties` via função. Assim o serializador não renderiza HTML e o app não remonta
envelope GeoJSON.

**JS centralizado e modular (decisão de §11 + pedido explícito).** Em vez do `<script>` inline da skill
`leaflet-map` (que serve a uma página única), aqui o JS é **um conjunto de módulos em `static/`**, cada
um com responsabilidade única e compostos por um módulo de entrada — o mesmo princípio do Python. Como o
mapa chega por **swap do HTMX**, a inicialização não pode ser um `<script type="module" src>` dentro do
partial (módulos só executam uma vez; o swap não re-dispararia). A solução alinhada a §11 é um
**callback `htmx.onLoad`** (categoria "callback que escuta evento do HTMX") registrado **uma vez** no
`base.html`: a cada conteúdo inserido, ele procura um `div#map` novo e monta o mapa lendo os
`json_script` daquele container. O partial fica **sem script**; só emite container + dados.

**Reprojeção a cargo do servidor (§7.3).** O domínio já pede ao WFS as feições no `output_crs` injetado;
aqui injetamos `MAP_OUTPUT_CRS = 4326`. O Leaflet recebe GeoJSON 4326 e **nunca** reprojeta no JS.

**O WMS base do Leaflet ≠ o integrador `services/integrations/wms`.** Já existe um `WmsFetcher` em
`services/integrations/wms` que faz **GetMap server-side** e devolve **imagem** (`WmsImage`) — útil para
exportar/compor rasters no backend, mas **sem relação** com o mapa interativo. O fundo do Leaflet é um
**tile layer cliente** (`L.tileLayer.wms`) que fala **direto** com o WMS do GeoSampa; o backend só
fornece a **config** (URL, camada, versão) via `settings` → `json_script`. Mantemos o CRS **default** do
Leaflet (Web Mercator 3857) para os tiles e usamos **WMS 1.3.0**; a geometria de resultado é que vem em
4326 (GeoJSON). Cuidado conhecido (skill `leaflet-map`): WMS 1.3.0 + EPSG:4326 inverte eixos — por isso
os **tiles** ficam no 3857 default, sem passar `crs` ao `L.map`.

**Fluxo ponta a ponta.**
```
clique na sugestão (logradouro_matcher) ──hx-post──▶ logradouro_geocoder.geocodificar (view)
   • lê settings (WFS + layer + MAP_OUTPUT_CRS + cor linha) e monta WfsFetcher
   • LogradouroGeocodInput(codlog, layer_name, output_crs=4326)
   • LogradouroGeocoder(fetcher)(input) → list[SegmentoLogradouroFeature]   (domínio)
   • serializa → GeoJSON FeatureCollection (pacote geometry), com popup_html/rotulo por feature
   • escolhe cor de linha; chama o helper do mapping
   ▼
mapping._mapa (partial): div#map + json_script(wms) + json_script(payload)   ──swap──▶ #resultado-busca
   ▼
htmx.onLoad (JS centralizado): detecta #map → cria mapa → base WMS → camada GeoJSON (linha) → fitBounds
```

## Peças de referência a compor
- `@services/domain/logradouro_geocod` → `LogradouroGeocoder`, `LogradouroGeocodInput`,
  `SegmentoLogradouroFeature`: a geocodificação (codlog → linha) **já pronta**; compor, não reescrever.
- `@services/domain/geometry` → `GeoFeature`/`LineGeometry`: o envelope já existente; o serializador novo
  vive aqui e reusa o `geometry.model_dump()` das *features*.
- `@services/integrations/wfs` → `WfsFetcher`, `WfsConnectionConfig`, `WfsRetryPolicy`: a view monta o
  fetcher exatamente como os *management commands* já fazem
  (`apps/address_geocoder/management/commands/extrair_segmentos_logradouros.py` é o padrão de leitura de
  `settings.WFS_*` → `WfsConnectionConfig`/`WfsRetryPolicy` → `WfsFetcher`).
- `templates/base.html` → já carrega **Leaflet 1.9** (CSS no head, JS antes do `</body>`) e o **HTMX**;
  aqui só se acrescenta o `<script type="module">` do JS centralizado e o registro do `htmx.onLoad`.
- `templates/logradouro_matcher/partials/resultados_codlog.html` e `resultados_logradouro.html` → os
  itens de sugestão cujo `hx-post` passa a apontar para o `logradouro_geocoder` (alvo `#resultado-busca`).
- Skill **`leaflet-map`** → referência de `L.map`/`L.tileLayer.wms`/`L.geoJSON`/popup/tooltip/`fitBounds`
  e do padrão `json_script` (adaptado aqui para módulos + `htmx.onLoad`).
- `settings.WFS_*` / `WFS_LAYER_LOGRADOUROS` → já existem; **novas** constantes de `settings`: config do
  WMS para o Leaflet (`WMS_URL`, `WMS_VERSION = "1.3.0"` e as bases `WMS_LAYER_ORTOFOTO =
  "geoportal:ORTO_RGB_2020"` + `WMS_LAYER_MAPA_BASE = "geoportal:MapaBase_Politico"`, compostas em
  `WMS_BASES`), `MAP_OUTPUT_CRS`, centro/zoom default e cor(es) default por tipo de geometria.
- `@services/integrations/wms` → `WmsFetcher` (GetMap server-side, devolve imagem): **NÃO é usado** nesta
  SPEC. Listado aqui só para deixar explícita a fronteira — o fundo do Leaflet é `L.tileLayer.wms` direto,
  com config vinda de `settings`, sem passar por esse integrador.

## Snippets sugeridos

```python
# services/domain/geometry/serializers.py — serializador genérico (reusa o envelope existente)
from collections.abc import Callable, Sequence
from typing import Any

from .models import GeoFeature


def to_geojson_feature_collection(
    features: Sequence[GeoFeature[Any, Any]],
    properties: Callable[[GeoFeature[Any, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Converte features de domínio numa GeoJSON FeatureCollection 4326 (formato do Leaflet).
    Agnóstico ao tipo de geometria. O ENVELOPE é geometria (mora aqui); as PROPERTIES de
    apresentação (popup_html, rotulo) vêm do app via `properties` — este módulo não renderiza HTML."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": f.geometry.model_dump(),
                "properties": properties(f),
            }
            for f in features
        ],
    }
```

```python
# services/domain/geometry/__init__.py — só reexporta (§11)
from .models import GeoFeature, LineGeometry, PolygonGeometry
from .serializers import to_geojson_feature_collection

__all__ = [
    "GeoFeature",
    "LineGeometry",
    "PolygonGeometry",
    "to_geojson_feature_collection",
]
```

```python
# config/settings.py — novas constantes (lidas pela orquestração; nada disso vai pro JS hardcoded)
# (no bloco _Settings: aliases WMS_URL / WMS_LAYERS_BASE / WMS_VERSION / MAP_* via Field, como os WFS_*)
MAP_OUTPUT_CRS = 4326                   # CRS único de saída para a GEOMETRIA de resultado (§7.3)
WMS_URL = _env.wms_url                  # "https://wms.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/ows"
WMS_VERSION = _env.wms_version          # "1.3.0" — injetado no JS, não hardcoded
WMS_LAYER_ORTOFOTO = _env.wms_layer_ortofoto      # "geoportal:ORTO_RGB_2020"
WMS_LAYER_MAPA_BASE = _env.wms_layer_mapa_base     # "geoportal:MapaBase_Politico"
# Lista ordenada de bases nomeadas; a 1ª é a visível por padrão. Nomes (rótulos do control) vêm daqui.
WMS_BASES = [
    {"nome": "Ortofoto", "layers": WMS_LAYER_ORTOFOTO},
    {"nome": "Mapa base", "layers": WMS_LAYER_MAPA_BASE},
]
MAP_CENTRO_DEFAULT = [-23.55, -46.63]   # [lat, lng] — fallback (São Paulo)
MAP_ZOOM_DEFAULT = 12
MAP_COR_LINHA = _env.map_cor_linha      # cor default da linha de logradouro (avulsa)
MAP_COR_POLIGONO = _env.map_cor_poligono
# OBS.: estas constantes NÃO se confundem com as do integrador WMS server-side
# (services/integrations/wms / WmsConnectionConfig), que servem ao GetMap de imagens, não ao Leaflet.
```

```python
# apps/mapping/context.py — helper de contexto (orquestração do mapping; agnóstico de domínio)
from typing import Any

from django.conf import settings

WMS_URL: str = settings.WMS_URL
WMS_VERSION: str = settings.WMS_VERSION
WMS_BASES: list[dict[str, str]] = settings.WMS_BASES
MAP_CENTRO_DEFAULT: list[float] = settings.MAP_CENTRO_DEFAULT
MAP_ZOOM_DEFAULT: int = settings.MAP_ZOOM_DEFAULT


def contexto_mapa(geometria: dict[str, Any], cor: str) -> dict[str, Any]:
    """Monta o contexto do partial do mapa: geometria GeoJSON 4326 + cor + config de WMS/centro.
    Não conhece logradouro/lote — só geometria pronta."""
    return {
        "wms": {"url": WMS_URL, "version": WMS_VERSION, "bases": WMS_BASES},
        "payload": {
            "geometria": geometria,
            "cor": cor,
            "centro": MAP_CENTRO_DEFAULT,
            "zoom": MAP_ZOOM_DEFAULT,
        },
    }
```

```html
{# templates/mapping/_mapa.html — partial agnóstico de domínio: só container + dados (sem <script>) #}
<div id="map" class="h-[70vh] w-full rounded-lg"></div>
{{ wms|json_script:"mapa-wms" }}
{{ payload|json_script:"mapa-payload" }}
```

```javascript
// static/src/js/mapa/criar_mapa.js — (a) instanciar o mapa
export function criarMapa(elId, centro, zoom) {
  return L.map(elId, { minZoom: 10, maxZoom: 19 }).setView(centro, zoom);
}
```

```javascript
// static/src/js/mapa/camada_base.js — (b) camadas base WMS + controle de camadas
// TODA a config (url, versão, bases nomeadas) vem do servidor. Tile layers cliente direto ao WMS
// do GeoSampa — não passam pelo integrador server-side. A 1ª base da lista é a visível por padrão.
export function adicionarBaseWms(map, wms) {
  const baseMaps = {};
  wms.bases.forEach((b, i) => {
    const layer = L.tileLayer.wms(wms.url, {
      layers: b.layers, version: wms.version, format: "image/png",
      transparent: false, attribution: "GeoSampa — PMSP",
    });
    baseMaps[b.nome] = layer;
    if (i === 0) layer.addTo(map);          // base default (primeira da lista)
  });
  L.control.layers(baseMaps).addTo(map);    // bases mutuamente exclusivas (radio)
  return baseMaps;
}
```

```javascript
// static/src/js/mapa/camada_resultado.js — (c) camada de resultado + enquadrar
// popup_html e rotulo já vêm prontos nas properties (servidor); o JS só os entrega ao Leaflet.
export function adicionarResultado(map, geometria, cor) {
  const camada = L.geoJSON(geometria, {
    style: () => ({ color: cor, weight: 3, opacity: 1, fillColor: cor, fillOpacity: 0.3 }),
    pointToLayer: (f, latlng) =>
      L.circleMarker(latlng, { radius: 7, color: cor, weight: 2, fillColor: cor, fillOpacity: 0.85 }),
    onEachFeature: (f, layer) => {
      const p = f.properties || {};
      if (p.popup_html) layer.bindPopup(p.popup_html);
      if (p.rotulo) layer.bindTooltip(p.rotulo, { direction: "top", sticky: true });
    },
  }).addTo(map);
  const b = camada.getBounds();
  b.isValid() ? map.fitBounds(b, { maxZoom: 18, padding: [20, 20] }) : map.setView(b.getCenter(), 17);
  return camada;
}
```

```javascript
// static/src/js/mapa/init.js — (d) entrada: COMPÕE (a)→(c), disparada pelo HTMX (uma vez)
import { criarMapa } from "./criar_mapa.js";
import { adicionarBaseWms } from "./camada_base.js";
import { adicionarResultado } from "./camada_resultado.js";

function lerJson(id) {
  const el = document.getElementById(id);
  return el ? JSON.parse(el.textContent) : null;
}

function montarMapa() {
  const div = document.getElementById("map");
  if (!div || div.dataset.pronto) return;     // só monta um #map novo, uma vez
  const wms = lerJson("mapa-wms");
  const data = lerJson("mapa-payload");
  if (!wms || !data) return;
  const map = criarMapa("map", data.centro, data.zoom);
  adicionarBaseWms(map, wms);
  adicionarResultado(map, data.geometria, data.cor);
  div.dataset.pronto = "1";
}

// §11 caso (1): callback de evento do HTMX, registrado uma única vez (carregado no base.html).
htmx.onLoad(montarMapa);
```

```html
{# templates/base.html — incluir o JS centralizado UMA vez (antes do fechamento do body) #}
<script type="module" src="{% load static %}{% static 'js/mapa/init.js' %}"></script>
```

```python
# apps/logradouro_geocoder/views.py — orquestração (sem regra de negócio)
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.mapping.context import contexto_mapa
from services.domain.geometry import GeoFeature, to_geojson_feature_collection
from services.domain.logradouro_geocod import LogradouroGeocoder, LogradouroGeocodInput
from services.integrations.wfs import WfsConnectionConfig, WfsFetcher, WfsRetryPolicy

MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
WFS_LAYER_LOGRADOUROS: str = settings.WFS_LAYER_LOGRADOUROS
MAP_COR_LINHA: str = settings.MAP_COR_LINHA


def _fetcher() -> WfsFetcher:
    config = WfsConnectionConfig(
        domain=settings.WFS_DOMAIN, endpoint=settings.WFS_ENDPOINT,
        namespace=settings.WFS_NAMESPACE, service=settings.WFS_SERVICE, version=settings.WFS_VERSION,
    )
    retry = WfsRetryPolicy(
        request_timeout_seconds=settings.WFS_REQUEST_TIMEOUT_SECONDS,
        max_retries=settings.WFS_MAX_RETRIES,
        retry_wait_min_seconds=settings.WFS_RETRY_WAIT_MIN_SECONDS,
        retry_wait_max_seconds=settings.WFS_RETRY_WAIT_MAX_SECONDS,
    )
    return WfsFetcher(config, retry_policy=retry)


def _properties(f: GeoFeature[Any, Any]) -> dict[str, Any]:
    # apresentação (HTML do popup + rótulo) — fica no app, não no serializador de geometria
    return {
        "popup_html": render_to_string(
            "logradouro_geocoder/partials/_popup_segmento.html", {"a": f.attributes}
        ),
        "rotulo": f.attributes.nome_logradouro,
    }


@require_POST
def geocodificar(request: HttpRequest) -> HttpResponse:
    entrada = LogradouroGeocodInput(
        codlog=request.POST.get("codlog", ""),
        layer_name=WFS_LAYER_LOGRADOUROS,
        output_crs=MAP_OUTPUT_CRS,
    )
    features = LogradouroGeocoder(_fetcher())(entrada)
    geojson = to_geojson_feature_collection(features, _properties)
    return render(request, "mapping/_mapa.html", contexto_mapa(geojson, MAP_COR_LINHA))
```

```html
{# templates/logradouro_geocoder/partials/_popup_segmento.html — popup por feature (apresentação) #}
<b>{{ a.nome_logradouro }}</b><br>
codlog {{ a.codlog }}{% if a.titulo %} · {{ a.titulo }}{% endif %}
```

```html
{# alteração no item de sugestão do logradouro_matcher: hx-post passa a acionar o geocoder #}
<li hx-post="{% url 'logradouro_geocoder:geocodificar' %}"
    hx-vals='{"codlog": "{{ r.codlog }}", "digito_verificador": "{{ r.dv }}"}'
    hx-target="#resultado-busca" hx-swap="innerHTML">…</li>
```

## Fora de escopo
- **Lote → polígono no mapa** (`lote_geocoder`): é a SPEC **mapa/002**, que **reusa** todo o `mapping`,
  o JS centralizado e o serializador entregues aqui.
- **Endereço → ponto** no mapa e o **pop-up endereço fiscal exato** (ponto vs. polígono): SPECs futuras.
- **Captura de eventos do mapa** (clique, desenho, digitalização manual) — fora da skill `leaflet-map` e
  desta SPEC (fase 2).
- **Salvar no projeto / autenticação / layers / cor por layer**: a busca avulsa é pública e a cor aqui é
  um default de `settings`. Projetos/layers (com cor própria) são fase 1 itens 5–6, SPECs próprias.
- **Persistência** das geometrias (GeoDjango/`GeometryField`), CRS canônico de armazenamento e **export**:
  aqui a geometria só é repassada para renderização, sem gravação.
- **Pipeline de build/minificação** do JS para produção: o JS é servido como asset estático; otimização
  de deploy (bundling/minify) fica para a fase de deploy (§2 menciona compilar/minificar no deploy).
- **Múltiplos mapas simultâneos** na mesma página / controle de camadas (ortofoto vs. mapa): um único
  mapa de resultado por vez.

## Notas de teste
- **Serializador** (`to_geojson_feature_collection`): com uma lista de `SegmentoLogradouroFeature` fake,
  produz `{"type":"FeatureCollection","features":[...]}` com `geometry` = `model_dump()` da geometria e
  `properties` = o que a função injetada devolve; lista vazia → `features: []`. Confirmar que é agnóstico
  ao tipo (funciona igual para `PolygonGeometry`).
- **View `geocodificar`** (logradouro): injetar um `WfsFetcher`/geocoder fake (sem rede) e verificar que
  o DTO carrega `output_crs = MAP_OUTPUT_CRS` e `layer_name = WFS_LAYER_LOGRADOUROS`; que o partial
  `mapping/_mapa.html` é renderizado com `wms` e `payload` no contexto; e que cada `properties` traz
  `popup_html` e `rotulo`. `codlog` ausente/ inválido → tratado pela validação do DTO (§Pydantic).
- **Helper `contexto_mapa`**: devolve `wms` (url+layers de settings) e `payload` (geometria, cor, centro,
  zoom) — sem nada de domínio.
- **Partial do mapa**: contém `div#map` com altura, dois `json_script` (`mapa-wms`, `mapa-payload`) e
  **nenhum** `<script>` de lógica.
- **Smoke manual**: digitar um logradouro, clicar na sugestão, ver a **linha** desenhada sobre o WMS, com
  popup no clique e tooltip no hover; reenviar outra sugestão e confirmar que o mapa re-monta no swap
  (o `htmx.onLoad` redetecta o novo `#map`).

## Patches

### Patch 001 (v4) — URL por base: ortofoto vem de um WMS de raster em outro domínio

**Sintoma.** O mapa base político (`geoportal:MapaBase_Politico`) e a plotagem dos segmentos de
linha do codlog funcionam normalmente, mas a **base ortofoto não retorna nada**. Motivo: a ortofoto
**não é servida pelo WMS geral** (`WMS_URL`, `.../geoserver/geoportal/ows`) e sim por um **WMS de
raster** hospedado em outro domínio:

```
WMS_RASTER_URL = "http://raster.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wms"
```

A configuração do serviço é a mesma (WMS 1.3.0, mesma camada `geoportal:ORTO_RGB_2020`), só muda a
**URL** do endpoint.

**Decisão.** Mantida toda a arquitetura da SPEC (config de WMS vinda de `settings` → `json_script`,
tile layer cliente direto, nada hardcoded no JS). A única mudança é que **cada base pode ter sua
própria `url`**: `WMS_BASES` ganha a chave opcional `url` por entrada. Quem não define `url` cai no
`WMS_URL` geral; a ortofoto passa a apontar para `WMS_RASTER_URL`.

**Ajustes.**

- `config/settings.py`: nova env `wms_raster_url` (alias `WMS_RASTER_URL`, default acima) e constante
  `WMS_RASTER_URL`. A entrada da ortofoto em `WMS_BASES` recebe `"url": WMS_RASTER_URL`:

  ```python
  WMS_BASES: list[dict[str, str]] = [
      {"nome": "Ortofoto", "layers": WMS_LAYER_ORTOFOTO, "url": WMS_RASTER_URL},
      {"nome": "Mapa base", "layers": WMS_LAYER_MAPA_BASE},
  ]
  ```

- `static/src/js/mapa/camada_base.js`: o tile layer resolve a URL por base, com fallback ao WMS
  geral — continua **sem hardcode** (a URL vem do servidor):

  ```javascript
  const layer = L.tileLayer.wms(b.url || wms.url, { ... });
  ```

Nenhuma mudança no partial, no `contexto_mapa` (já repassa `bases` inteiro) nem no fluxo de
logradouro → linha.

### Patch 002 (v4) — zoom mínimo mais alto (ortofoto não tem cobertura em zoom baixo)

**Sintoma.** Com `minZoom: 10` (`static/src/js/mapa/criar_mapa.js`), o usuário consegue afastar o
mapa até um nível em que a camada base **ortofoto** (`ORTO_RGB_2020`, servida pelo `WMS_RASTER_URL`
— patch 001) não tem dados naquele zoom e aparece em branco/quebrada.

**Decisão.** Subir o `minZoom` do `L.map` de `10` para `13`, nível em que a ortofoto tem cobertura
garantida. Sem mudança de arquitetura — o valor continua fixo no módulo `criar_mapa.js` (não é
config de `settings`, então não passa por `json_script`).

**Ajuste.**

- `static/src/js/mapa/criar_mapa.js`:

  ```javascript
  export function criarMapa(elId, centro, zoom) {
    return L.map(elId, { minZoom: 13, maxZoom: 19 }).setView(centro, zoom);
  }
  ```

Nenhuma mudança no `contexto_mapa`, no partial ou nas demais camadas base.
