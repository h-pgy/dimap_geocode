---
spec: design/016
versao: v1
atualizado_em: 2026-09-09
testes_tdd: true
implementado: true
markers_obrigatorios: []
changelog:
  - v1: versão inicial
---

# SPEC design/016 — Controles de mapa Onsen (pílula de zoom e torre de camadas)

## 1 · User story
Servidor da DIMAP opera os controles de navegação e visualização do mapa no contexto de consulta geográfica para ajustar níveis de zoom e alternar entre camadas base de satélite e mapa vetorial através de uma pílula tátil de vidro fosco com torre retrátil no canto inferior da tela, sem depender dos controles padrão cinzas do Leaflet.

## 2 · Condições de pronto
- [x] O mapa Leaflet **não exibe nenhum controle nativo** de zoom (`zoomControl`) nem de camadas (`L.control.layers`).
- [x] O canto inferior esquerdo do mapa exibe uma **pílula de vidro translúcido** (`.pilula-mapa`), alinhada simetricamente à pílula de atalho do canto direito e recolhida automaticamente sob modais abertos (`.moldura-fixa`).
- [x] O lado direito da pílula contém um **poço rebaixado** com o botão `&minus;` (zoom-out) à esquerda e o botão `+` (zoom-in) à direita.
- [x] Clicar no botão `&minus;` afasta o mapa (`zoomOut()`) e clicar no botão `+` aproxima o mapa (`zoomIn()`).
- [x] O JavaScript captura eventos de rolagem do mouse (`wheel` da bola/barra de rolagem) sobre o mapa: ao rolar para aproximar (zoom in), o glifo `+` no poço recebe temporariamente a classe `.pilula-mapa__btn-zoom--swell` (com expansão *swell* e destaque em brilho ciano no próprio glifo, sem desenhar círculo no botão); ao rolar para afastar (zoom out), o glifo `&minus;` recebe o mesmo efeito tátil.
- [x] Ao atingir o nível mínimo de zoom do mapa, o botão `&minus;` torna-se **visualmente atenuado e inoperante**; ao atingir o nível máximo, o botão `+` torna-se **visualmente atenuado e inoperante**.
- [x] O lado esquerdo da pílula contém um **botão de camadas com glifo estacado** que abre e fecha o submenu vertical ("torrezinha").
- [x] O submenu de camadas sobe em **animação vertical a partir do lado esquerdo da pílula**, assentando-se logo acima dela.
- [x] As opções e os glifos da torrezinha são **renderizados declarativamente a partir de `settings.WMS_BASES`**; em repouso o item exibe apenas o glifo e, ao expandir a torre ("gorda") no hover/foco, **todos os nomes de base aparecem simultaneamente**.
- [x] O seletor ciano e o tom de texto migram com **perfeita simetria bidirecional** (cima &harr; baixo): o item sob o cursor recebe o poço rebaixado, o anel/brilho ciano e o rótulo Madeira (`text-madeira-700 font-bold`), enquanto a opção desocupada assume o tom Rocha secundário (`text-rocha-700 font-medium`) e cede o seletor ciano; ao retirar o cursor da torre, o seletor descansa sobre a base ativa no Leaflet.
- [x] O design foi aprovado no **mock**, e as peças foram portadas para `static/src/tema-dimap.dev.css`, para o styleguide (`/design_system`) e para o partial do mapa.

## 3 · Domínio
Iteração de design system, ergonomia espacial e integração de controles Leaflet: nenhum model persistido em banco de dados e nenhuma migração. A ontologia modela a configuração declarativa das camadas de mapa definida em `settings.WMS_BASES`, transportada ao cliente por `contexto_mapa_base()` e renderizada como peças de apresentação correspondentes:

```python
class CamadaBaseItem(BaseModel):
    """Definição de uma camada base declarada em settings.WMS_BASES com metadados para a torrezinha."""

    nome: str
    glifo: str
    layers: str
    url: str | None = None
    zoom_nativo: int | None = None
```

A pergunta que esta SPEC faz às peças de UI e tokens existentes:

| Peça / Parâmetro | Definição anterior | Pergunta desta SPEC |
|---|---|---|
| Controles de zoom | Caixa retangular cinza nativa do Leaflet (`L.control.zoom`, canto inferior esquerdo) | "Como transformar o zoom num gesto tátil coerente com o Onsen?"; o poço rebaixado (`.card-well`) em pílula com `-` à esquerda e `+` à direita afunda os botões no gelo, aproveitando a afordância táctil das outras pílulas do sistema. |
| Controle de camadas | Menu expansível nativo do Leaflet (`L.control.layers`) | "Como escolher o fundo do mapa sem quebrar a estética de vidro?"; um botão dedicado com glifo de camadas estacadas aciona uma torrezinha vertical de vidro fosco (`.glass-panel`) que repousa compacta e expande na horizontal em hover. |
| `.atalho-mapa` | Pílula isolada no canto inferior direito (`bottom-6 right-4 lg:right-6`) | "Onde os novos controles devem repousar?"; no canto inferior esquerdo (`bottom-6 left-4 lg:left-6`), estabelecendo simetria de piso e z-index (`z-20`) com o atalho de validação. |
| `.moldura-fixa` | Ocultamento sob modais (`opacity-0 -translate-y-5 scale-95`) | "Os controles do mapa devem sumir quando um modal abre?"; sim — a pílula de controles herda `.moldura-fixa`, liberando a cena sem concorrência visual. |

**Mock:** [016-mock-controles-mapa-onsen.html](016-mock-controles-mapa-onsen.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Camadas vetoriais adicionais sobrepostas (overlays acumuláveis com checkbox) — sem dono ainda.
- Controle de opacidade contínua das camadas base via slider deslizante — sem dono ainda.
- Persistência da camada base predileta do usuário no perfil do servidor no banco — volátil em sessão no cliente.
- Troca de camada ou zoom por atalhos globais de teclado (`+`, `-`, `L`) — sem dono ainda.

## 5 · Peças de referência a compor
- `@config/settings.py` → `WMS_BASES`: catálogo declarativo das camadas base WMS (nome, glifo, layers, url e zoom nativo).
- `@apps/mapping/context.py` → `contexto_mapa_base`: transporte do catálogo de bases para o template e para o JSON do cliente.
- `@static/src/tema-dimap.dev.css` → `.glass-panel`: receita de gelo fosco para a casca da pílula e para a torrezinha.
- `@static/src/tema-dimap.dev.css` → `.card-well`: poço rebaixado utilizado no controle de zoom e no hover dos itens de camada.
- `@static/src/tema-dimap.dev.css` → `.moldura-fixa`: mecanismo CSS de recolhimento suave durante abertura de modais.
- `@templates/documentos/partials/_atalho_validar.html` → pílula gêmea do canto inferior direito que define a cota de piso.
- `@static/src/js/mapa/criar_mapa.js` → `criarMapa`: inicialização do Leaflet onde a inibição dos controles nativos é consolidada.
- `@static/src/js/mapa/camada_base.js` → `adicionarBaseWms`: registro das instâncias WMS do GeoSampa sem invocar `L.control.layers`.
- Skills: `componentes-frontend`, `leaflet-map`, `mock`, `escrever-testes`.

## 6 · Snippets

**`config/settings.py`**
```python
# Lista declarativa de bases WMS com o glifo de apresentação associado para a torrezinha.
WMS_BASES: list[dict[str, str | int]] = [
    {
        "nome": "Ortofoto",
        "glifo": "glifo-satelite",
        "layers": WMS_LAYER_ORTOFOTO,
        "url": WMS_RASTER_URL,
        "zoom_nativo": WMS_ZOOM_NATIVO_ORTOFOTO,
    },
    {
        "nome": "Mapa base",
        "glifo": "glifo-mapa-base",
        "layers": WMS_LAYER_MAPA_BASE,
    },
]
```

**`templates/mapping/_glifos_mapa.html`**
```xml
{# Glifos dos controles de mapa do Onsen: camadas estacadas, mapa base e satélite/ortofoto. #}
<svg width="0" height="0" class="absolute" aria-hidden="true">
  <defs>
    <!-- Glifo de camadas estacadas: 3 lâminas sobrepostas em perspectiva isométrica -->
    <g id="glifo-camadas">
      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    <!-- Glifo de mapa base vetorial: mapa dobrado com traçados -->
    <g id="glifo-mapa-base">
      <path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3V6z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M9 3v15M15 6v15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    <!-- Glifo de satélite / ortofoto: globo com órbita e sinal de sensoriamento -->
    <g id="glifo-satelite">
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/>
      <path d="M3.6 9h16.8M3.6 15h16.8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <ellipse cx="12" cy="12" rx="4.5" ry="9" fill="none" stroke="currentColor" stroke-width="1.8"/>
    </g>
    <!-- Glifo menos para zoom-out -->
    <g id="glifo-menos">
      <path d="M5 12h14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>
    </g>
  </defs>
</svg>
```

**`templates/mapping/_controles_mapa.html`**
```html
{# Partial dos controles de mapa do Onsen: canto inferior esquerdo do canvas. #}
<div id="controles-mapa" class="pilula-mapa moldura-fixa pointer-events-auto" role="region" aria-label="Controles do mapa">
  <!-- Torrezinha de camadas: sobe animada acima do botão esquerdo da pílula -->
  <div id="torre-camadas" class="torre-camadas torre-camadas--fechada" role="menu" aria-label="Camadas base disponíveis">
    {% for base in wms.bases %}
      <button
        type="button"
        class="torre-camadas__item {% if forloop.first %}torre-camadas__item--ativo{% endif %}"
        data-camada-nome="{{ base.nome }}"
        role="menuitemradio"
        aria-checked="{% if forloop.first %}true{% else %}false{% endif %}"
        title="{{ base.nome }}"
      >
        <span class="torre-camadas__glifo">
          <svg class="w-4 h-4" viewBox="0 0 24 24">
            <use href="#{{ base.glifo|default:'glifo-mapa-base' }}"/>
          </svg>
        </span>
        <span class="torre-camadas__rotulo">{{ base.nome }}</span>
      </button>
    {% endfor %}
  </div>

  <!-- Botão disparador do submenu de camadas -->
  <button
    type="button"
    id="btn-alternar-camadas"
    class="pilula-mapa__btn-camadas"
    aria-expanded="false"
    aria-haspopup="true"
    aria-controls="torre-camadas"
    title="Alternar camadas do mapa"
  >
    <svg class="w-5 h-5 text-agua-700" viewBox="0 0 24 24">
      <use href="#glifo-camadas"/>
    </svg>
  </button>

  <!-- Poço rebaixado de controle de zoom -->
  <div class="pilula-mapa__zoom card-well" role="group" aria-label="Controle de aproximação">
    <button
      type="button"
      id="btn-mapa-zoom-out"
      class="pilula-mapa__btn-zoom"
      title="Afastar mapa (Zoom out)"
      aria-label="Afastar mapa"
    >
      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24"><use href="#glifo-menos"/></svg>
    </button>
    <button
      type="button"
      id="btn-mapa-zoom-in"
      class="pilula-mapa__btn-zoom"
      title="Aproximar mapa (Zoom in)"
      aria-label="Aproximar mapa"
    >
      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24"><use href="#glifo-mais"/></svg>
    </button>
  </div>
</div>
```

**`static/src/tema-dimap.dev.css`**
```css
  /* ==================== MOLÉCULAS · CONTROLES DE MAPA (SPEC design/016) ==================== */
  /* Pílula no canto inferior esquerdo do mapa, simétrica ao atalho de documentos à direita. */
  .pilula-mapa {
    @apply absolute bottom-6 left-4 lg:left-6 z-20 flex items-center gap-1.5 p-1 rounded-full backdrop-blur-[10px] bg-white/40 border border-white/60 text-base-content shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_2px_8px_rgba(7,58,84,0.38)] transition-all duration-300;
  }

  /* Botão disparador do seletor de camadas */
  .pilula-mapa__btn-camadas {
    @apply w-9 h-9 rounded-full flex items-center justify-center text-madeira-700 transition-all duration-200 hover:bg-white/60 hover:shadow-[0_0_12px_rgba(72,202,228,0.35)] active:scale-95 cursor-pointer;
  }
  .pilula-mapa__btn-camadas[aria-expanded="true"] {
    @apply bg-white/70 shadow-[0_0_14px_rgba(72,202,228,0.5)] text-agua-800;
  }

  /* Poço rebaixado contendo o par de botões de zoom */
  .pilula-mapa__zoom {
    @apply flex items-center gap-0.5 px-1 py-0.5 rounded-full;
  }
  .pilula-mapa__btn-zoom {
    @apply w-7 h-7 rounded-full flex items-center justify-center font-bold text-madeira-700 transition-all duration-200 hover:bg-white/70 active:scale-90 cursor-pointer disabled:opacity-30 disabled:pointer-events-none;
  }
  .pilula-mapa__btn-zoom svg {
    @apply transition-all duration-200 origin-center;
  }
  /* Feedback tátil na rolagem do mouse: sem círculo em volta, swell e brilho exclusivamente no próprio glifo */
  .pilula-mapa__btn-zoom--swell svg {
    @apply scale-[1.38] text-agua-600;
    filter: drop-shadow(0 0 6px rgba(72, 202, 228, 0.95)) drop-shadow(0 0 10px rgba(0, 150, 199, 0.6));
  }

  /* Torrezinha vertical de camadas que ascende a partir da esquerda da pílula */
  .torre-camadas {
    @apply absolute bottom-full left-0 mb-2.5 flex flex-col gap-1 p-1 rounded-2xl backdrop-blur-[18px] bg-gradient-to-br from-white/65 via-white/50 to-white/40 border border-white/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_8px_24px_rgba(7,58,84,0.3),0_0_20px_rgba(72,202,228,0.2)] transition-all duration-300 ease-out origin-bottom-left;
  }
  .torre-camadas--fechada {
    @apply opacity-0 translate-y-3 scale-95 pointer-events-none;
  }
  .torre-camadas--aberta {
    @apply opacity-100 translate-y-0 scale-100 pointer-events-auto;
  }

  /* Item de camada da torrezinha: em repouso mostra só o glifo; em hover/foco vira poço com rótulo */
  .torre-camadas__item {
    @apply flex items-center gap-2 p-1.5 rounded-xl text-madeira-700 transition-all duration-200 cursor-pointer border border-transparent whitespace-nowrap;
  }
  .torre-camadas__glifo {
    @apply w-7 h-7 flex items-center justify-center shrink-0 rounded-lg text-agua-700 transition-colors;
  }
  .torre-camadas__rotulo {
    @apply text-xs pr-1.5 opacity-0 max-w-0 overflow-hidden transition-all duration-300 ease-out whitespace-nowrap;
  }

  /* Ao passar o cursor na torre (torre 'gorda'), todos os rótulos aparecem juntos */
  .torre-camadas:hover .torre-camadas__rotulo,
  .torre-camadas:focus-within .torre-camadas__rotulo {
    @apply opacity-100 max-w-xs;
  }

  /* Rótulo de camada: padrão em tom Rocha secundário */
  .torre-camadas__rotulo {
    @apply text-rocha-700 font-medium;
    filter: none;
  }

  /* Estado ativo em repouso (quando nenhum item da torre está sob o cursor):
     a camada ativa exibe anel seletor ciano, iluminação e rótulo Madeira */
  .torre-camadas__item--ativo {
    @apply ring-1 ring-agua-500/70 bg-white/20;
  }
  .torre-camadas__item--ativo .torre-camadas__glifo {
    @apply text-agua-700;
    filter: drop-shadow(0 0 6px rgba(72, 202, 228, 0.75));
  }
  .torre-camadas__item--ativo .torre-camadas__rotulo {
    @apply text-madeira-700 font-bold;
    filter: none;
  }

  /* Hover/Foco sobre qualquer item da torre (cima->baixo ou baixo->cima):
     Escavação em poço rebaixado (.card-well) + seletor ciano luminoso + rótulo Madeira */
  .torre-camadas__item:hover,
  .torre-camadas__item:focus-visible {
    @apply rounded-xl bg-white/35 border-white/50 ring-1 ring-agua-500/70;
    box-shadow: var(--sombra-poco), 0 0 0 1px rgba(72, 202, 228, 0.7);
  }
  .torre-camadas__item:hover .torre-camadas__glifo,
  .torre-camadas__item:focus-visible .torre-camadas__glifo {
    @apply text-agua-600;
    filter: drop-shadow(0 0 6px rgba(72, 202, 228, 0.75));
  }
  .torre-camadas__item:hover .torre-camadas__rotulo,
  .torre-camadas__item:focus-visible .torre-camadas__rotulo {
    @apply text-madeira-700 font-bold;
    filter: none;
  }

  /* Quando a torre tem algum item sob o cursor:
     O item ativo que NÃO estiver sob o cursor cede temporariamente o seletor ciano
     e volta ao tom Rocha secundário, permitindo que o seletor migre com total
     simetria em qualquer direção (cima->baixo ou baixo->cima) */
  .torre-camadas:has(.torre-camadas__item:hover) .torre-camadas__item--ativo:not(:hover),
  .torre-camadas:has(.torre-camadas__item:focus-visible) .torre-camadas__item--ativo:not(:focus-visible),
  .torre-camadas.has-item-hover .torre-camadas__item--ativo:not(:hover) {
    @apply ring-0 bg-transparent;
    box-shadow: none !important;
  }
  .torre-camadas:has(.torre-camadas__item:hover) .torre-camadas__item--ativo:not(:hover) .torre-camadas__glifo,
  .torre-camadas:has(.torre-camadas__item:focus-visible) .torre-camadas__item--ativo:not(:focus-visible) .torre-camadas__glifo,
  .torre-camadas.has-item-hover .torre-camadas__item--ativo:not(:hover) .torre-camadas__glifo {
    filter: none;
  }
  .torre-camadas:has(.torre-camadas__item:hover) .torre-camadas__item--ativo:not(:hover) .torre-camadas__rotulo,
  .torre-camadas:has(.torre-camadas__item:focus-visible) .torre-camadas__item--ativo:not(:focus-visible) .torre-camadas__rotulo,
  .torre-camadas.has-item-hover .torre-camadas__item--ativo:not(:hover) .torre-camadas__rotulo {
    @apply text-rocha-700 font-medium;
    filter: none;
  }
```

**`static/src/js/mapa/controles_mapa.js`**
```javascript
// Orquestrador JS de cola entre a UI dos controles Onsen e o mapa Leaflet.
export function inicializarControlesMapa(mapa, baseMaps) {
  const container = document.getElementById("controles-mapa");
  if (!container || !mapa) return;

  const btnZoomIn = document.getElementById("btn-mapa-zoom-in");
  const btnZoomOut = document.getElementById("btn-mapa-zoom-out");
  const btnAlternar = document.getElementById("btn-alternar-camadas");
  const torre = document.getElementById("torre-camadas");
  const itensCamada = torre ? torre.querySelectorAll(".torre-camadas__item") : [];

  // 1. Atualização dos limites de zoom
  function atualizarBotoesZoom() {
    const z = mapa.getZoom();
    if (btnZoomIn) btnZoomIn.disabled = z >= mapa.getMaxZoom();
    if (btnZoomOut) btnZoomOut.disabled = z <= mapa.getMinZoom();
  }
  mapa.on("zoomend", atualizarBotoesZoom);
  atualizarBotoesZoom();

  // 2. Disparos de zoom e feedback de rolagem do mouse
  function dispararSwell(btn) {
    if (!btn || btn.disabled) return;
    btn.classList.add("pilula-mapa__btn-zoom--swell");
    clearTimeout(btn._swellTimer);
    btn._swellTimer = setTimeout(() => {
      btn.classList.remove("pilula-mapa__btn-zoom--swell");
    }, 350);
  }

  if (btnZoomIn) btnZoomIn.addEventListener("click", () => { mapa.zoomIn(); dispararSwell(btnZoomIn); });
  if (btnZoomOut) btnZoomOut.addEventListener("click", () => { mapa.zoomOut(); dispararSwell(btnZoomOut); });

  // Captura eventos de rolagem (wheel / scroll) da bola do mouse sobre o mapa
  const mapContainer = mapa.getContainer ? mapa.getContainer() : mapa;
  if (mapContainer && mapContainer.addEventListener) {
    mapContainer.addEventListener("wheel", (e) => {
      if (e.deltaY < 0) {
        dispararSwell(btnZoomIn);
      } else if (e.deltaY > 0) {
        dispararSwell(btnZoomOut);
      }
    }, { passive: true });
  }

  // Sincronia complementar com qualquer variação de zoom do Leaflet
  let zoomAnterior = mapa.getZoom();
  mapa.on("zoomstart", () => { zoomAnterior = mapa.getZoom(); });
  mapa.on("zoom", () => {
    const z = mapa.getZoom();
    if (z > zoomAnterior) dispararSwell(btnZoomIn);
    else if (z < zoomAnterior) dispararSwell(btnZoomOut);
    zoomAnterior = z;
  });

  // 3. Abertura e fechamento da torrezinha
  function fecharTorre() {
    if (!torre) return;
    torre.classList.add("torre-camadas--fechada");
    torre.classList.remove("torre-camadas--aberta");
    if (btnAlternar) btnAlternar.setAttribute("aria-expanded", "false");
  }

  function alternarTorre(e) {
    e.stopPropagation();
    if (!torre) return;
    const abrindo = torre.classList.contains("torre-camadas--fechada");
    if (abrindo) {
      torre.classList.remove("torre-camadas--fechada");
      torre.classList.add("torre-camadas--aberta");
      if (btnAlternar) btnAlternar.setAttribute("aria-expanded", "true");
    } else {
      fecharTorre();
    }
  }

  if (btnAlternar) btnAlternar.addEventListener("click", alternarTorre);
  document.addEventListener("click", (e) => {
    if (container && !container.contains(e.target)) fecharTorre();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") fecharTorre();
  });

  // 4. Alternância de camadas base
  itensCamada.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const nomeCamada = btn.dataset.camadaNome;
      const layerAlvo = baseMaps[nomeCamada];
      if (!layerAlvo) return;

      Object.values(baseMaps).forEach((layer) => {
        if (mapa.hasLayer(layer)) mapa.removeLayer(layer);
      });
      layerAlvo.addTo(mapa);

      itensCamada.forEach((b) => {
        const ativo = b === btn;
        b.classList.toggle("torre-camadas__item--ativo", ativo);
        b.setAttribute("aria-checked", ativo ? "true" : "false");
      });
      fecharTorre();
    });
  });

  // 5. Sincronização do hover na torre (reforço cross-browser para migração imediata do seletor)
  itensCamada.forEach((item) => {
    item.addEventListener("mouseenter", () => torre && torre.classList.add("has-item-hover"));
    item.addEventListener("mouseleave", () => torre && torre.classList.remove("has-item-hover"));
  });
}
```

**`static/src/js/mapa/criar_mapa.js`**
```javascript
// Criação do Leaflet sem controles visuais legados.
export function criarMapa(elId, centro, zoom) {
  return L.map(elId, {
    minZoom: MIN_ZOOM,
    maxZoom: MAX_ZOOM,
    zoomControl: false,          // Controles de zoom do Leaflet inibidos
    attributionControl: false,
    zoomAnimationThreshold: MAX_ZOOM - MIN_ZOOM,
  }).setView(centro, zoom);
}
// export function adicionarZoom(mapa) -> REMOVIDA: substituída pela pilula-mapa__zoom
```

**`static/src/js/mapa/camada_base.js`**
```javascript
// Retorna o dicionário de camadas base sem invocar o L.control.layers legado.
export function adicionarBaseWms(map, wms) {
  const baseMaps = {};
  wms.bases.forEach((b, i) => {
    const layer = L.tileLayer.wms(b.url || wms.url, {
      layers: b.layers,
      version: wms.version,
      format: "image/png",
      transparent: false,
      maxZoom: map.getMaxZoom(),
      maxNativeZoom: b.zoom_nativo,
    });
    baseMaps[b.nome] = layer;
    if (i === 0) layer.addTo(map);
  });
  // L.control.layers(baseMaps, null, ...).addTo(map); -> REMOVIDA: substituída pela torre-camadas
  return baseMaps;
}
```

## 7 · Caveats
**O Leaflet é comandado por JavaScript imperativo atrelado ao DOM da pílula.** O controle de zoom e de camadas exige chamadas diretas às funções `zoomIn()`, `zoomOut()`, `addLayer()` e `removeLayer()` do Leaflet, sem ciclo de request HTMX. Custo: esse trecho de código assume manutenção explícita do sincronismo visual entre a camada ativada no Leaflet e o highlight dos botões na interface.

**A expansão horizontal da torrezinha em hover utiliza transição de `max-width` e `opacity`.** O layout compacto exibe apenas glifos verticais e alarga suavemente ao pousar o ponteiro sobre qualquer opção, gerando o poço com o rótulo da base. Custo: navegadores com renderização lenta de `backdrop-filter` podem apresentar leve queda de taxa de quadros durante o redimensionamento dinâmico do container vítreo.

**A seleção de camada base é mantida estritamente na memória da sessão do navegador.** O usuário pode alternar entre mapa e satélite quantas vezes desejar sem gravar a escolha em tabela de perfil de usuário. Custo: recarregar a página por completo (F5) restaura a base padrão inicial configurada nas settings do backend.

## 8 · Testes (TDD)
- `test_contexto_mapa_base_inclui_glifos_definidos_em_settings` — confirma que `contexto_mapa_base` entrega `wms.bases` com o campo `glifo` originado de `settings.WMS_BASES`.
- `test_mapa_inicializa_sem_controles_nativos_leaflet` — valida que `criarMapa` define `zoomControl: false` e `camada_base` não instancia `L.control.layers`.
- `test_partial_controles_mapa_renderiza_estrutura_completa` — garante a presença do container `.pilula-mapa` com atributos de acessibilidade e classes `.moldura-fixa`.
- `test_poco_zoom_renderiza_botoes_menos_e_mais` — verifica a existência dos botões `#btn-mapa-zoom-out` e `#btn-mapa-zoom-in` aninhados dentro do `.card-well`.
- `test_gatilho_camadas_possui_atributos_acessibilidade` — confirma que o botão de camadas declara `aria-expanded`, `aria-haspopup` e aponta para a torrezinha.
- `test_torre_camadas_renderiza_todas_as_bases_configuradas` — assegura a emissão de um botão com data attribute e glifo para cada entrada em `wms.bases`.
- `test_torre_camadas_marca_primeira_base_como_ativa_e_demais_como_secundaria` — comprova que a primeira base recebe a classe de ativação (`torre-camadas__item--ativo`) e `aria-checked="true"`, enquanto as opções inativas recebem o estilo secundário em tom Rocha (`text-rocha-700`).
- `test_glifos_mapa_disponibilizam_icones_camadas_satelite_e_vetorial` — atesta que o template `_glifos_mapa.html` define os IDs `#glifo-camadas`, `#glifo-mapa-base` e `#glifo-satelite`.
- `test_home_inclui_partial_controles_mapa` — confirma que a view principal (`templates/core/home.html`) inclui os controles customizados sobre o canvas.
- `test_botoes_zoom_refletem_teto_e_piso_do_mapa` — comprova que a função JS ajusta o atributo `disabled` nos limites mínimo e máximo de zoom.
- `test_rolagem_mouse_sobre_mapa_aciona_classe_swell_no_zoom_correspondente` — comprova que disparos de rolagem (`wheel`) sobre o container do mapa aplicam a classe de feedback tátil `.pilula-mapa__btn-zoom--swell` no botão `+` (deltaY negativo) e no botão `-` (deltaY positivo), removendo-a após o intervalo de transição.
- `test_torre_camadas_sincroniza_hover_bidirecional` — comprova que os listeners de `mouseenter` e `mouseleave` nos itens da torre comutam a classe de transição de seletor (`has-item-hover`) no container da torre, garantindo migração imediata do seletor ciano e das cores de texto.
