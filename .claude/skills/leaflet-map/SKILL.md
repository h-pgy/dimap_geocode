---
name: leaflet-map
description: Como instanciar e configurar o mapa Leaflet do DIMAP GeoCoder — criar o mapa com centro/zoom corretos, configurar a camada base WMS (GeoSampa) e adicionar UMA camada de resultado (ponto, linha ou polígono) com popup, tooltip e cores de preenchimento/borda. Use SEMPRE que for escrever o partial do mapa (app `mapping`) ou qualquer JS que renderize geometria no Leaflet. NÃO cobre captura de eventos do mapa (skill futura).
---

# Leaflet — instanciar o mapa e renderizar uma camada

Referência para o **app `mapping`**: o partial do Leaflet recebe uma geometria do backend e a
renderiza sobre o WMS do GeoSampa. Leaflet **1.9** já está carregado no `templates/base.html`
(CSS no `<head>`, JS antes do `</body>`); a inicialização do mapa vai no `{% block scripts %}` da
página/partial.

## Escopo

Esta skill cobre **só** três coisas:
1. Instanciar o mapa com **centro e zoom** corretos.
2. Configurar a **camada base WMS** (GeoSampa).
3. Adicionar **uma camada** (ponto / linha / polígono) e configurá-la: **popup, tooltip, cor de
   preenchimento e cor de borda**.

**Fora do escopo (skill futura):** capturar eventos do mapa (`map.on('click'…)`, desenho, etc.).
Não escreva handlers de evento usando esta skill.

## Regras de fronteira (§11 do CLAUDE.md — não violar)

- **JS é só cola para o Leaflet.** Sem regra de negócio, sem estado, sem montar UI a partir de
  JSON. O JS recebe **geometria + config já prontos do servidor** e os entrega ao Leaflet.
- **Nada hardcoded no JS.** URL do WMS, nome das camadas WMS, centro, zoom e **cor da camada**
  vêm do **backend** (settings/contexto Django), nunca cravados no script. O Django injeta via
  `json_script` (ver "Passando dados do servidor").
- **Saída sempre em EPSG:4326.** O domínio reprojeta para 4326 antes de mandar (§7.3). O JS
  **nunca** reprojeta. A geometria chega como **GeoJSON** (coordenadas `[lng, lat]`).
- **GeoJSON pelo `L.geoJSON`.** Não faça parsing manual de coordenadas — `L.geoJSON` lê o GeoJSON
  direto e cuida da ordem `[lng, lat] → [lat, lng]`.

---

## 1. O container e o mapa

Leaflet exige um `div` com **altura explícita** (senão o mapa não aparece). Use uma classe
Tailwind de altura.

```html
<div id="map" class="h-[70vh] w-full rounded-lg"></div>
```

```javascript
// setView recebe [LAT, LNG] (atenção: ordem inversa do GeoJSON) e o zoom.
// Centro/zoom default vêm do servidor; abaixo, fallback em São Paulo.
const map = L.map("map", {
  minZoom: 10,
  maxZoom: 19,
}).setView([-23.55, -46.63], 12);
```

- `L.map("map")` → o id do `div`. Métodos do Leaflet encadeiam (retornam o próprio objeto).
- `setView([lat, lng], zoom)` define **centro e zoom** de uma vez.
- `minZoom` / `maxZoom` limitam o zoom do usuário.
- Para mover depois: `map.setZoom(z)`, `map.setView([lat,lng], z)`, `map.panTo([lat,lng])`.

### Enquadrar no resultado (o caso comum desta app)

Quase nunca queremos centro fixo: queremos **enquadrar a geometria retornada**. Use `fitBounds`
sobre os bounds da camada (ver §3). Para linha/polígono funciona direto; para **ponto** (bounds
degenerados) defina um zoom.

```javascript
// camada = a layer GeoJSON criada na seção 3
const bounds = camada.getBounds();
if (bounds.isValid()) {
  map.fitBounds(bounds, { maxZoom: 18, padding: [20, 20] });
} else {
  map.setView(camada.getBounds().getCenter(), 17); // ponto isolado
}
```

---

## 2. Camada base WMS (GeoSampa)

O fundo do mapa é o **WMS do GeoSampa** via `L.tileLayer.wms(url, opções)`. **URL e `layers`
vêm do servidor** (constante/settings → contexto), não do JS.

```javascript
const base = L.tileLayer.wms(WMS_CONFIG.url, {
  layers: WMS_CONFIG.layers,   // nomes das camadas WMS, separados por vírgula
  format: "image/png",
  transparent: false,          // base opaca; use true só para overlays sobre outra base
  version: "1.3.0",
  attribution: "GeoSampa — PMSP",
}).addTo(map);
```

Opções de `L.tileLayer.wms`:
- **`layers`** (obrigatório): nomes das camadas do GetCapabilities (CSV).
- `format`: `"image/png"` (use `"image/jpeg"` para base sem transparência → mais leve).
- `transparent`: `true` para overlays; `false` para a base.
- `version`: `"1.3.0"` (padrão moderno) ou `"1.1.1"`.
- `styles`, `attribution`: opcionais.

> **CRS / eixo:** mantenha o CRS **default** do Leaflet (`EPSG:3857`/Web Mercator) — não passe
> `crs` ao `L.map`. O GeoSampa serve tiles em Web Mercator para isso. Cuidado: WMS **1.3.0 +
> EPSG:4326** inverte a ordem dos eixos; ficando no 3857 default você evita esse problema.

### Múltiplas bases + controle de camadas (opcional)

Para alternar entre fundos (ex.: mapa vs. ortofoto), monte um `L.control.layers`:

```javascript
const baseMaps = {
  "Mapa": L.tileLayer.wms(WMS_CONFIG.url, { layers: WMS_CONFIG.mapa, version: "1.3.0" }),
  "Ortofoto": L.tileLayer.wms(WMS_CONFIG.url, { layers: WMS_CONFIG.ortofoto, version: "1.3.0" }),
};
baseMaps["Mapa"].addTo(map);             // a que começa visível
L.control.layers(baseMaps).addTo(map);   // 1º arg = bases (radio); 2º arg = overlays (checkbox)
```

`L.control.layers(baseLayers, overlays)`: bases são **mutuamente exclusivas** (radio); overlays
são **acumuláveis** (checkbox). Passe `null` no arg que não usar.

---

## 3. Adicionar UMA camada de resultado (ponto / linha / polígono)

A geometria chega como **GeoJSON 4326**. Use `L.geoJSON(geojson, opções)` — ele reconhece o tipo
(`Point` / `LineString` / `Polygon` / `Multi*`) sozinho. Três ganchos importam:

- **`style`** → cor/espessura/preenchimento de **linhas e polígonos**.
- **`pointToLayer(feature, latlng)`** → como desenhar **pontos** (default é `L.marker` com pino;
  para controlar cor use `L.circleMarker`).
- **`onEachFeature(feature, layer)`** → **popup e tooltip** (roda para cada feature).

A **cor** é do layer (cada layer do projeto tem `cor` de display — §1 do CLAUDE.md) e chega do
servidor; o JS só a aplica.

```javascript
// COR vem do servidor (ex.: data.cor). borda e preenchimento derivam dela.
const camada = L.geoJSON(data.geometria, {
  // Linhas e polígonos:
  style: (feature) => ({
    color: data.cor,        // COR DA BORDA / da linha
    weight: 3,              // espessura da borda/linha (px)
    opacity: 1,             // opacidade da borda/linha
    fillColor: data.cor,    // COR DE PREENCHIMENTO (polígono)
    fillOpacity: 0.3,       // opacidade do preenchimento
  }),

  // Pontos (use circleMarker para controlar cor; L.marker usa o pino padrão):
  pointToLayer: (feature, latlng) =>
    L.circleMarker(latlng, {
      radius: 7,
      color: data.cor,      // cor da borda do círculo
      weight: 2,
      fillColor: data.cor,  // cor de preenchimento do círculo
      fillOpacity: 0.85,
    }),

  // Popup (clique) e tooltip (hover) — ver seção 4:
  onEachFeature: (feature, layer) => {
    layer.bindPopup(data.popup_html);                       // HTML do servidor
    layer.bindTooltip(data.rotulo, { direction: "top", sticky: true });
  },
}).addTo(map);

// Enquadrar (seção 1):
const bounds = camada.getBounds();
if (bounds.isValid()) {
  map.fitBounds(bounds, { maxZoom: 18, padding: [20, 20] });
} else {
  map.setView(bounds.getCenter(), 17);
}
```

### Cores por tipo de geometria — resumo

| Tipo     | Onde aplica a cor                | Borda            | Preenchimento              |
|----------|----------------------------------|------------------|----------------------------|
| Ponto    | `pointToLayer` → `L.circleMarker`| `color`+`weight` | `fillColor`+`fillOpacity`  |
| Linha    | `style`                          | `color`+`weight` | — (linha não preenche)     |
| Polígono | `style`                          | `color`+`weight` | `fillColor`+`fillOpacity`  |

`color` é **sempre a borda/o traço**; `fillColor` é **o miolo**. Para um polígono só com
contorno, use `fillOpacity: 0`.

---

## 4. Popup e Tooltip

Ambos são vinculados a uma `layer` (dentro de `onEachFeature`, ou direto numa camada simples).

```javascript
// POPUP — abre no CLIQUE, fecha no X. Conteúdo HTML montado pelo SERVIDOR.
layer.bindPopup("<b>Rua Direita, 123</b><br>codlog 12345678");
// layer.openPopup(); // abrir já aberto (opcional)

// TOOLTIP — aparece no HOVER (ou permanente). Texto curto / rótulo.
layer.bindTooltip("Rua Direita", {
  direction: "top",   // top | bottom | left | right | center | auto
  sticky: true,        // segue o cursor sobre a geometria
  permanent: false,    // true = rótulo fixo sempre visível
  opacity: 0.9,
});
```

- **Popup** = informação detalhada sob demanda (clique). O HTML vem pronto do backend.
- **Tooltip** = rótulo leve no hover (ou fixo com `permanent: true`).
- Não monte o HTML do popup no JS a partir de campos soltos — o **servidor** entrega o
  `popup_html` já renderizado (§11: JS não monta UI).

---

## Passando dados do servidor para o JS (padrão do projeto)

O JS **não** carrega config nem geometria embutida. O Django injeta tudo via `json_script`, e o
script lê pelo id. Assim respeitamos "nada hardcoded / sem regra no JS".

```html
{# partial do mapping: templates/mapping/_map.html #}
<div id="map" class="h-[70vh] w-full rounded-lg"></div>

{{ wms_config|json_script:"wms-config" }}
{{ resultado|json_script:"map-data" }}

{% block scripts %}
<script>
  const WMS_CONFIG = JSON.parse(document.getElementById("wms-config").textContent);
  const data       = JSON.parse(document.getElementById("map-data").textContent);

  const map = L.map("map", { minZoom: 10, maxZoom: 19 })
    .setView(data.centro, data.zoom);                 // [lat, lng], zoom — do servidor

  L.tileLayer.wms(WMS_CONFIG.url, {
    layers: WMS_CONFIG.layers, format: "image/png",
    version: "1.3.0", attribution: "GeoSampa — PMSP",
  }).addTo(map);

  const camada = L.geoJSON(data.geometria, {
    style: () => ({ color: data.cor, weight: 3, fillColor: data.cor, fillOpacity: 0.3 }),
    pointToLayer: (f, latlng) =>
      L.circleMarker(latlng, { radius: 7, color: data.cor, weight: 2,
                               fillColor: data.cor, fillOpacity: 0.85 }),
    onEachFeature: (f, layer) => {
      layer.bindPopup(data.popup_html);
      layer.bindTooltip(data.rotulo, { direction: "top", sticky: true });
    },
  }).addTo(map);

  const b = camada.getBounds();
  b.isValid() ? map.fitBounds(b, { maxZoom: 18, padding: [20, 20] })
              : map.setView(b.getCenter(), 17);
</script>
{% endblock %}
```

`json_script` escapa o conteúdo com segurança (evita XSS / quebra de aspas) — é a forma correta
de levar dados do contexto Django para o JS.

## Checklist antes de fechar o partial do mapa

- [ ] O `div#map` tem **altura explícita** (classe Tailwind).
- [ ] **Centro, zoom, URL/layers do WMS e cor** vêm do **servidor** (nada cravado no JS).
- [ ] A geometria é **GeoJSON 4326** e renderiza via **`L.geoJSON`** (sem parsing manual).
- [ ] Cores: `color` = borda/traço, `fillColor` = preenchimento; ponto via `circleMarker`.
- [ ] Popup (clique, HTML do servidor) e tooltip (hover/rótulo) vinculados em `onEachFeature`.
- [ ] Mapa **enquadra o resultado** (`fitBounds`/`setView`), não fica num centro fixo arbitrário.
- [ ] **Nenhum** handler de evento do mapa aqui (isso é a próxima skill).
