---
spec: design/001
versao: v2
atualizado_em: 2026-07-06
implementado: true
changelog:
  - v1: versão inicial
  - v2: paleta do DS vira JSON em config/ consultado pelo settings; rolagem por seção de
    sugestões com altura máxima do painel; aderência explícita à skill componentes-frontend
    (tokens via @apply)
---

# SPEC design/001 — UX fullscreen "Onsen de Inverno": mapa como canvas + cores das camadas no DS

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como usuário do GeoCoder, quero interagir com um mapa em tela cheia que está sempre aberto —
com a busca flutuando sobre ele em vidro, como num aplicativo de mapa moderno — para pesquisar
e ver resultados georreferenciados sem trocar de página nem esperar o mapa "aparecer", com as
geometrias pintadas nas cores do design system.

## Critérios de aceite
- [ ] Ao abrir a home, o mapa Leaflet ocupa **100% da viewport** e já está instanciado com a base
      WMS do GeoSampa, com o tratamento "água límpida + lente leve" da skill
      `componentes-frontend` §6, **sem nenhum resultado ainda**.
- [ ] A **barra de busca flutua** sobre o mapa (gelo fosco, centro-topo, como em
      `.claude/skills/componentes-frontend/examples/mock_ui.html`), com ícone de lupa, dica de
      teclas e badges de contexto; as **sugestões aparecem num painel de vidro flutuante**
      logo abaixo da barra, sobre o mapa.
- [ ] Clicar numa sugestão **desenha a geometria no mapa já aberto** (o mapa não é recriado):
      o resultado anterior é removido, o novo entra e o mapa enquadra a geometria (`fitBounds`).
- [ ] Buscar um segundo item substitui a geometria do primeiro — nunca ficam dois resultados
      empilhados nem dois mapas na página.
- [ ] Quando o resultado não tem geometria, o **aviso aparece flutuando sobre o mapa** (alert
      semântico do DS), sem destruir o mapa nem a barra de busca.
- [ ] O **widget da área do usuário** flutua no canto superior direito (gelo fosco, avatar +
      "Projetos / Área do Usuário", como no mock), renderizado pelo `base.html`, **estático**
      (sem lógica de sessão) e com **id estável e explícito** para a lógica futura de
      autenticação se pendurar nele.
- [ ] A marca "DIMAP GeoCoder" aparece como chip de vidro no canto superior esquerdo (a navbar
      opaca de topo deixa de existir na home — nada cobre o mapa em faixa cheia).
- [ ] Os controles do Leaflet (zoom, seletor de bases) **não colidem** com a UI flutuante
      (reposicionados para o canto inferior direito).
- [ ] As **cores default das camadas** vêm do design system: linha `#0F766E` (accent), polígono
      `#9C6644` (madeira-500), ponto `#00B4D8` (agua-500) — conforme
      `componentes-frontend/references/paleta.json → geometrias`.
- [ ] O **lote condominial** deixa de usar o verde-limão hardcoded (`#76e60d` na view) e passa a
      usar uma cor **definida em settings** (nova constante, sobrescrevível por env), com default
      do DS: `#5E412F` (madeira-700 — mesma família do polígono, tom mais fundo = agregado).
- [ ] A **paleta do design system vive num JSON dentro de `config/`** e o `settings.py` **consulta
      esse JSON** para derivar os defaults das cores das camadas — nenhum hex de cor de camada
      digitado direto no `settings.py`. O JSON espelha
      `componentes-frontend/references/paleta.json` (que segue sendo a fonte da verdade do DS).
- [ ] O painel de sugestões tem **altura máxima definida** (não domina a tela; o mapa continua
      protagonista) e **cada seção de resultado rola de forma independente** (rolagem própria
      para a seção de codlog, outra para a de endereço, outra para a de contribuinte etc.),
      com o título da seção sempre visível dentro do painel.
- [ ] Rolagem da página não existe (viewport travada, como no mock); a página é o mapa.
- [ ] `mypy` e `ruff` limpos; fluxo completo validado por smoke test (busca → sugestão →
      geometria no mapa singleton).

## Contexto e decisões de arquitetura

Hoje o mapa nasce **dentro do resultado**: cada geocodificação renderiza `mapping/_mapa.html`
com um `<div id="map">` novo + `json_script`s, e o `init.js` instancia um Leaflet por swap
(`div.dataset.pronto`). Isso funcionava para a página vertical, mas é incompatível com a UX
validada no mock (mapa sempre aberto). A mudança central é **inverter a posse do mapa**:

1. **O mapa vira singleton da home (interface/orquestração).** A view da home passa a fornecer
   o contexto do mapa base (WMS/centro/zoom — sem geometria), e o partial fullscreen do
   `mapping` renderiza o canvas + overlays de água límpida. O `init.js` cria o mapa **uma vez**
   no carregamento.
2. **Resultados viram payload, não página.** As views de geocodificação
   (`logradouro_geocoder`, `lote_geocoder`, `address_geocoder`) deixam de renderizar um mapa e
   passam a responder um partial **só de dados** (`json_script` com a geometria + cor). O
   handler `htmx.onLoad` já existente detecta o payload novo, **remove a camada de resultado
   anterior** e adiciona a nova no mapa singleton (JS utilitário do Leaflet — §11, caso 2).
   O partial de aviso segue igual, só que renderizado num alvo flutuante.
3. **Camadas continuam respeitando papéis.** As views seguem orquestrando (montam DTO, chamam
   domínio, escolhem partial); o domínio não muda; o `mapping` continua agnóstico (recebe
   geometria pronta + cor). Só muda **qual partial** responde e **onde** o HTML dele aterrissa.
4. **Cores são configuração de interface** (Pydantic Settings → constantes `UPPER_CASE`,
   §10.3), e **a paleta é dado, não código**: um JSON de paleta entra em `config/` (espelho de
   `componentes-frontend/references/paleta.json`) e o `settings.py` o carrega para derivar os
   defaults de `MAP_COR_*` — inclusive a condominial, que **sai da view** (hardcode de cor em
   view viola o DS e o §10.3). Env vars continuam podendo sobrescrever cada cor.
5. **Layout flutuante é CSS puro do DS** (tokens `glass-panel`, `input-glass`, `btn-onsen`,
   `.suggestion-item` — já nos templates re-skinados): a home passa a usar o padrão do mock
   (`pointer-events-none` no layer de UI, `pointer-events-auto` nos painéis), sem JS de layout.
6. **A skill `componentes-frontend` é normativa para esta SPEC.** A implementação deve ativá-la
   e permanecer aderente: todo estilo recorrente novo entra como **token/classe `@apply`** (no
   `input.css` e no espelho dev do `base.html`, seguindo §2 da skill — `@apply` só de utilities,
   classe daisyUI empilhada no HTML), **nunca** como fileira de utilities repetida em template.
   Se a rolagem por seção pedir classe própria (ex.: molécula de seção de sugestões), ela nasce
   como token da skill e é registrada no styleguide (`examples/design_system.html`).

Fluxo resumido: home → mapa fullscreen instanciado (base WMS + água límpida) → usuário digita
na barra flutuante → sugestões em vidro (fluxo HTMX atual intocado) → clique → view do
geocoder responde payload → `htmx.onLoad` troca a camada de resultado no mapa aberto →
`fitBounds`. Aviso sem geometria → alert flutuante no mesmo alvo do payload.

## Peças de referência a compor
- `@apps/mapping/context.py` → `contexto_mapa` / `contexto_aviso`: base para derivar o contexto
  do mapa singleton (WMS/centro/zoom sem geometria) e o contexto de payload (geometria + cor,
  sem WMS) — compor, não duplicar as constantes.
- `@static/src/js/mapa/criar_mapa.js`, `camada_base.js`, `camada_resultado.js`: reutilizar como
  estão (criação, base WMS, estilo/popup/tooltip/fitBounds); a novidade fica no orquestrador
  `init.js` (singleton + troca de camada de resultado).
- `@static/src/js/mapa/init.js` → `lerJson`/`htmx.onLoad`: padrão existente de leitura de
  `json_script` e registro único de callback — evoluir, não recriar.
- Tokens do DS já em `static/src/input.css` e `templates/base.html` (dev/CDN): `glass-panel`,
  `input-glass`, `btn-onsen`, `badge-*`, `suggestion-item`, `text-overline`, `icon-glow` e o
  tratamento de mapa da skill `componentes-frontend` §6.
- Referência visual e de layout: `.claude/skills/componentes-frontend/examples/mock_ui.html`
  (posicionamento da barra, do widget e camadas de overlay) — replicar o layout, exceto gaveta.
- Partials re-skinados de sugestão/resultado (`search/partials/_sugestoes.html`, listas dos
  matchers): intocados — só mudam de "onde aparecem" (contêiner flutuante da home).
- `@config/settings.py` → `_Settings` (Pydantic Settings) e bloco `MAP_*`: onde os defaults de
  cor trocam e onde entra a constante condominial.
- `componentes-frontend/references/paleta.json` → estrutura pronta da paleta (escalas +
  `geometrias` + tema): base para o JSON de `config/` — copiar a estrutura, não inventar outra.
- Skill `componentes-frontend` (SKILL.md §2, §5, §6): método Atomic Design, tokens `@apply` e o
  tratamento do mapa — **normativa** durante toda a implementação.

## Snippets sugeridos

Settings — paleta do DS como JSON em `config/`, consultado para os defaults (env ainda
sobrescreve cada cor; direção — adaptar sem violar §10.3):
```python
# config/settings.py
_PALETA_DS: dict[str, Any] = json.loads((Path(__file__).parent / "paleta_ds.json").read_text())
_GEOMETRIAS: dict[str, str] = _PALETA_DS["geometrias"]
_ESCALAS: dict[str, dict[str, str]] = _PALETA_DS["escalas"]

class _Settings(BaseSettings):
    ...
    map_cor_linha: str = Field(default=_GEOMETRIAS["linha"], alias="MAP_COR_LINHA")
    map_cor_poligono: str = Field(default=_GEOMETRIAS["poligono"], alias="MAP_COR_POLIGONO")
    map_cor_ponto: str = Field(default=_GEOMETRIAS["ponto"], alias="MAP_COR_PONTO")
    map_cor_poligono_condominio: str = Field(
        default=_ESCALAS["madeira"]["700"], alias="MAP_COR_POLIGONO_CONDOMINIO"
    )

# ... e no bloco de constantes:
MAP_COR_POLIGONO_CONDOMINIO = _env.map_cor_poligono_condominio
```
O `config/paleta_ds.json` espelha a estrutura de
`componentes-frontend/references/paleta.json` (escalas + `geometrias` + tema daisyUI).

View do lote — condominial sem hardcode:
```python
# apps/lote_geocoder/views.py
MAP_COR_POLIGONO_CONDOMINIO: str = settings.MAP_COR_POLIGONO_CONDOMINIO

def _properties(f: GeoFeature[Any, Any]) -> GeoJsonProperties:
    cor_condominio = (
        MAP_COR_POLIGONO_CONDOMINIO if getattr(f.attributes, "is_condominio", False) else None
    )
    ...
```

`init.js` — singleton + troca da camada de resultado (JS utilitário Leaflet, §11 caso 2):
```javascript
let mapa = null;
let camadaResultado = null;

function montarMapaBase() {
  const wms = lerJson("mapa-wms");
  const cfg = lerJson("mapa-config");           // centro/zoom, sem geometria
  if (!wms || !cfg || mapa) return;
  mapa = criarMapa("map", cfg.centro, cfg.zoom); // controles: bottomright
  adicionarBaseWms(mapa, wms);
}

function aplicarResultado(el) {
  const data = lerJson("mapa-payload");          // chega via swap HTMX
  if (!data || !mapa) return;
  if (camadaResultado) mapa.removeLayer(camadaResultado);
  camadaResultado = adicionarResultado(mapa, data.geometria, data.cor);
}

document.addEventListener("DOMContentLoaded", montarMapaBase);
htmx.onLoad(aplicarResultado);
```

Home — esqueleto do layout flutuante (padrão do mock; classes já existem no DS):
```html
<div class="relative h-screen w-screen overflow-hidden">
  <div id="map" class="absolute inset-0 z-0 saturate-[0.8] brightness-[1.05] contrast-[0.95]"></div>
  {# overlays de água límpida + lente — skill componentes-frontend §6 #}
  <div class="absolute inset-0 z-10 pointer-events-none flex flex-col items-center pt-[12vh]">
    <div class="pointer-events-auto w-11/12 max-w-2xl glass-panel p-4">…barra + hints…</div>
    <div id="sugestoes-busca" class="pointer-events-auto w-11/12 max-w-2xl mt-3"></div>
    <div id="resultado-busca" class="pointer-events-auto w-11/12 max-w-2xl mt-3"></div>
  </div>
</div>
```

Sugestões — painel com altura máxima e rolagem independente por seção (as classes nascem como
tokens `@apply` na skill, aqui só a direção do comportamento):
```html
{# _sugestoes.html — painel limitado; cada seção rola sozinha, título sempre visível #}
<div class="glass-panel p-3 space-y-3 max-h-[45vh] overflow-hidden flex flex-col">
  {% for secao in secoes %}
    <section class="min-h-0 flex flex-col">
      <h3 class="text-overline px-2 mb-1 shrink-0">{{ secao.titulo }}</h3>
      <div class="overflow-y-auto max-h-40">{{ secao.html|safe }}</div>
    </section>
  {% endfor %}
</div>
```

Widget do usuário no `base.html` — estático, com id estável para a lógica futura:
```html
<div id="widget-area-usuario"
     class="fixed top-6 right-6 z-20 glass-panel rounded-full! p-1.5 flex items-center sm:gap-3
            cursor-pointer transition-glass hover:bg-white/60">
  …avatar + "Projetos / Área do Usuário" (copiar do mock)…
</div>
```

## Fora de escopo
- **Gaveta lateral de detalhes** (drawer "Imóvel Fiscal" do mock) e a **coreografia de foco**
  (`cinematic-blur-layer`, ocultação da barra): dependem de uma feature real de "detalhes do
  resultado" que ainda não existe — ficam para a SPEC dessa feature.
- **Lógica do widget do usuário** (login/logout/registro, dropdown, estado de sessão): o widget
  entra **estático**; a lógica é do épico de autenticação (Roadmap fase 1, item 5).
- Compilação/minificação do CSS para deploy (segue o modo dev via CDN).
- Atalho de teclado real (Ctrl+K focar a busca) — a dica visual entra; o comportamento fica
  para depois.
- Qualquer mudança no domínio (`services/`) — esta SPEC é 100% interface/orquestração.

## Notas de teste
- View da home: 200, contém `id="map"`, `mapa-wms` e `mapa-config` (sem `mapa-payload`).
- Views de geocodificação: caminho feliz responde o partial de payload (com `mapa-payload` e a
  cor certa por tipo); lote condominial traz `cor == settings.MAP_COR_POLIGONO_CONDOMINIO`;
  caminho sem geometria responde o alert de aviso.
- Payload de lote não-condominial: `cor` das properties é `None` (cai no default da camada).
- Regressão: dois cliques seguidos em sugestões diferentes → um único conjunto de camadas de
  resultado (verificável só no browser; em teste, garantir que o partial de payload não traz
  markup de mapa).
- Widget: presente em qualquer página que estenda `base.html`, com `id="widget-area-usuario"`.
- Settings: `MAP_COR_*` iguais aos valores do JSON de `config/` quando não há env; env var
  sobrescreve; JSON ausente/malformado falha alto no boot (não silenciosamente).
- Sugestões com muitas seções/itens: painel não passa da altura máxima; cada seção mantém a
  própria rolagem (verificação visual no browser).

## Patches

_Nenhum patch registrado até o momento._
