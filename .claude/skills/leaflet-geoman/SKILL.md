---
name: leaflet-geoman
description: Use essa skill sempre que precisar utilizar ferramentas de desenho geoespacial no sistema. Aqui está contida a documentação do Leaflet-Geoman, o plugin de desenho que estamos usando no projeto (versão FREE). Cobre desenhar, editar, arrastar, cortar, girar e remover geometrias no mapa, snapping, toolbar de desenho, `map.pm`/`layer.pm`, text layer, layer groups, teclado e lazy loading. Use também ao extrair o GeoJSON desenhado para enviar ao backend. NÃO cobre renderizar geometria vinda do servidor (skill `leaflet-map`).
---

# Leaflet-Geoman — desenho e edição de geometrias

Plugin de desenho sobre o Leaflet 1.9 do projeto. Tudo que o usuário **cria ou altera** no mapa
passa por aqui; o que o servidor **manda renderizar** é a skill `leaflet-map`.

## Só a versão FREE

O projeto usa **`@geoman-io/leaflet-geoman-free`**. As referências locais já foram limpas do Pro,
mas **não complete de memória** — estes recursos **não existem** aqui e não devem aparecer em
código, SPEC ou sugestão:

- Modos: Split, Scale, Union, Difference, Copy Layer, Line Simplification, Custom Shapes, Lasso
  Select, Freehand Drawing.
- Recursos: Pinning, Measurement (`getMeasurements`), AutoTracing, Snap Guides, Geofencing.

**Snapping é free** e importa para o projeto (ver "Snapping" abaixo).

## Referências — abra só o arquivo que a tarefa pede

| Arquivo | Conteúdo | Abra quando |
|---|---|---|
| [`docs/introduction.md`](docs/introduction.md) | O que o plugin faz, tipos de geometria suportados | Precisa saber se um tipo de layer é editável |
| [`docs/toolbar.md`](docs/toolbar.md) | `addControls` / `removeControls` / `toggleControls`, cada botão e sua opção, posição, `oneBlock` | Vai ligar/desligar botões ou montar a toolbar |
| [`docs/modes.md`](docs/modes.md) | Modos free (Draw, Edit, Drag, Removal, Cut, Rotation) — só a visão geral | Precisa escolher qual modo usar |
| [`docs/options.md`](docs/options.md) | `setGlobalOptions` × opção por layer, `snappingOrder`, `layerGroup`, `panes`, `cutAsCircle`, `pm:globaloptionschanged` | Vai configurar comportamento global |
| [`docs/text-layer.md`](docs/text-layer.md) | Desenho e edição de texto, métodos e eventos `pm:text*` | Só se a SPEC pedir anotação de texto |
| [`docs/layer-groups.md`](docs/layer-groups.md) | `layergroup.pm.*`; exige `L.FeatureGroup`/`L.GeoJSON` | Vai editar várias layers juntas |
| [`docs/utils.md`](docs/utils.md) | `L.PM.Utils`: `circleToPolygon`, `findLayers`, `moveLayerTo`, `copyLayer`… | Precisa converter círculo ou manipular layer |
| [`docs/keyboard.md`](docs/keyboard.md) | `map.pm.Keyboard`, `exitModeOnEscape`, `finishOnEnter` | Vai configurar Esc/Enter ou teclas modificadoras |
| [`docs/lazy-loading.md`](docs/lazy-loading.md) | `L.PM.reInitLayer(map)` quando o plugin carrega depois do mapa | O `map.pm` está `undefined` |

Para localizar um termo sem abrir tudo: `rg -n "<termo>" .claude/skills/leaflet-geoman/docs/`.

### Lacunas conhecidas das referências

As referências são **resumos** das páginas oficiais, não o markdown integral, e **faltam
páginas**. Se a tarefa tocar nestes temas, **busque a página oficial** (WebFetch em `geoman.io`
está liberado) em vez de completar de memória:

- **Eventos de desenho/edição** (`pm:create`, `pm:edit`, `pm:remove`, `pm:drawstart`…) — não
  estão em nenhum arquivo local.
- **Opções de cada modo** (Draw Mode, Edit Mode…) — `modes.md` só lista os modos. Índice:
  `https://geoman.io/docs/leaflet/category/modes`.
- **Snapping** — `https://geoman.io/docs/leaflet/options/snapping`.
- **Instalação** — `https://geoman.io/docs/leaflet/getting-started/free-version`.
- **Customização da toolbar e do estilo do desenho** — `https://geoman.io/docs/leaflet/customize/toolbar`.

## Regras do projeto aplicadas ao Geoman (CLAUDE.md §3.1, §3.4, §7.2)

- **O plugin ainda não está instalado.** O Leaflet vem por `<script>` no `templates/base.html`.
  Adicionar o Geoman (CSS + JS, versão fixada, **depois** do `leaflet.js`) é decisão de SPEC —
  não instale por conta própria.
- **JS é só cola.** O JS habilita o modo, captura o evento e **serializa a geometria**. Nada de
  validar, corrigir ou decidir geometria no navegador; topologia, homogeneidade e regra de negócio
  são do domínio (`services/`), via DTO Pydantic.
- **Sai GeoJSON 4326 pelo `layer.toGeoJSON()`.** Nunca monte coordenadas à mão e nunca reprojete
  no JS — a reprojeção é centralizada no domínio (ver "CRS" abaixo).
- **Envio via HTMX, resposta em partial.** Nada de `fetch` consumindo JSON. URL, CSRF e alvo do
  swap vêm do template Django.
- **Configuração vem do servidor.** Modos liberados, cores e opções chegam por `json_script`,
  como na `leaflet-map`.
- **A toolbar nativa do Geoman está fora do design system.** Não a restilize com CSS ad hoc nem
  `!important`. O caminho natural é um controle do design system (como o zoom da SPEC
  `design/016`) chamando a API (`map.pm.enableDraw(...)`), com a toolbar nativa desligada. Se a
  SPEC quiser a nativa, **pergunte** — é peça visual nova (skill `mock`).

## CRS: desenha em 4326, guarda/calcula em 31983

O projeto usa **31983** (SIRGAS 2000 / UTM 23S, nativo do GeoSampa, métrico) para armazenar e
calcular, e **4326** só como formato de trânsito com o navegador — `MAP_INTERPOLATION_CRS` e
`MAP_OUTPUT_CRS` em `config/settings.py`.

- **Desenhar direto em 31983 não existe.** O Leaflet trabalha em `LatLng` e o `toGeoJSON()` segue
  a RFC 7946, que é 4326 por definição. Trocar o CRS do mapa (Proj4Leaflet + WMS do GeoSampa em
  31983) muda apenas a projeção de tiles e canvas: o Geoman continua devolvendo graus. Além de não
  mudar o dado, mexeria em peça já implementada (a `leaflet-map` fixa o default 3857) — só com
  SPEC e aval do usuário.
- **A geometria desenhada chega em 4326 e o domínio reprojeta** para o SRID vindo da orquestração
  antes de persistir ou calcular. Toda ação que guarda geometria precisa dessa etapa explícita.
- **Nada de conta métrica em graus nem no JS.** Área, comprimento, buffer e distância são feitos
  no domínio, em 31983.
- **Reprojetar não perde precisão** relevante: a transformação é determinística e WGS84 ≈ SIRGAS
  2000 (centímetros). Quem limita o traço é o pixel do zoom em que o usuário desenhou (~0,3 m/px
  no zoom 19) — **precisão vem do snapping**, não do CRS.

## Padrão: desenhar e enviar ao backend

O `pm:create` não está nas referências locais — confira o payload na doc oficial antes de
depender de algo além de `e.layer`.

```html
<form id="form-desenho"
      hx-post="{% url 'app:rota' %}"
      hx-trigger="geometria-desenhada"
      hx-target="#resultado-desenho">
  {% csrf_token %}
  <input type="hidden" name="geometria" id="input-geometria">
</form>
```

```javascript
// Botão a botão explícito: o default de addControls liga quase tudo.
map.pm.addControls({
  position: "topleft",
  drawMarker: false,
  drawCircleMarker: false,
  drawPolyline: false,
  drawRectangle: false,
  drawPolygon: true,
  drawCircle: false,
  drawText: false,
  editMode: true,
  dragMode: false,
  cutPolygon: false,
  removalMode: true,
  rotateMode: false,
});

map.on("pm:create", (e) => {
  const geometria = e.layer.toGeoJSON().geometry;
  document.getElementById("input-geometria").value = JSON.stringify(geometria);
  htmx.trigger("#form-desenho", "geometria-desenhada");
});
```

A view monta o DTO a partir de `geometria` e o domínio valida — nunca o JS.

## Armadilhas

- **Círculo não existe em GeoJSON.** `Circle`/`CircleMarker` viram `Point` no `toGeoJSON()` e o
  raio se perde. Desligue esses botões ou converta com `L.PM.Utils.circleToPolygon` (`utils.md`).
- **Retângulo sai como `Polygon`** — é o esperado, o backend não recebe "retângulo".
- **Text layer é um `L.marker`**: sai como `Point`. Desligue `drawText` se a SPEC não pedir texto.
- **Defaults ligados.** `addControls` sem opções mostra quase todos os botões — declare cada um.
- **Um modo por vez.** Habilitar um modo desliga o anterior (`modes.md`).
- **Edição em grupo exige `L.FeatureGroup`/`L.GeoJSON`**; `L.LayerGroup` puro não dispara os
  eventos que o plugin usa (`layer-groups.md`).
- **Partial do mapa re-renderizado por HTMX.** Se o Geoman carregar depois do mapa já existir,
  chame `L.PM.reInitLayer(map)` (`lazy-loading.md`). Cuide para não empilhar handlers `pm:*` a
  cada swap.
- **Opção global × pontual.** `setGlobalOptions` persiste entre modos; opções passadas a
  `enableDraw`/`layer.pm.enable` valem só naquela ativação (`options.md`, `toolbar.md`).

## Snapping

Liga-se por opção global e opcionalmente ganha botão na toolbar:

```javascript
map.pm.setGlobalOptions({
  snappable: true,
});
map.pm.addControls({
  snappingOption: true,
});
```

- Ordem de prioridade entre tipos de layer: `snappingOrder` (`options.md`).
- Ignorar uma layer específica: `snapIgnore: true` nas opções dela.
- O usuário desliga temporariamente segurando **ALT**.
- Para distância de snap e demais opções, busque a página de snapping (ver "Lacunas").

## Checklist

- [ ] Nenhum recurso Pro (lista acima) no código, na SPEC ou na sugestão.
- [ ] Cada botão da toolbar declarado explicitamente — ou toolbar nativa desligada e modos
      chamados por controle do design system.
- [ ] Geometria sai por `layer.toGeoJSON()`, em 4326, sem coordenada montada à mão.
- [ ] Se a geometria vai ser persistida ou medida: o domínio reprojeta para 31983 (SRID vindo da
      orquestração), e nenhuma conta métrica ficou em graus ou no JS.
- [ ] Envio por HTMX para rota Django; resposta em partial; validação no domínio via DTO.
- [ ] Círculo/texto desligados ou convertidos antes do envio.
- [ ] O que não está nas referências locais foi conferido na doc oficial, não inventado.
