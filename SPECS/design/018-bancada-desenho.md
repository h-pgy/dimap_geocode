---
spec: design/018
versao: v1
atualizado_em: 2026-09-12
testes_tdd: false
implementado: false
markers_obrigatorios: []
changelog:
  - v1: versão inicial
---

# SPEC design/018 — Bancada de desenho no mapa

## 1 · User story
O servidor da DIMAP desenha pontos, linhas e polígonos sobre a home no contexto da bancada de
ferramentas do Onsen para obter geometria própria sobre o território.

## 2 · Condições de pronto
- [ ] A toolbar nativa do Leaflet-Geoman **não aparece** em lugar nenhum: as ferramentas do plugin
      são acionadas exclusivamente pela bancada.
- [ ] Guardada, a bancada mostra **só a alça**; um clique nela abre o corpo, e outro o guarda de
      volta, largando a ferramenta que estiver na mão.
- [ ] **Ponto** e **linha** armam o desenho direto; **polígono** abre uma linha nova dentro do
      próprio corpo com polígono, retângulo e círculo, e o corpo cresce e encolhe junto.
- [ ] O traço nasce na **cor do seu tipo** — ponto em água, linha em accent, polígono em sakura.
- [ ] **Concluir** só se oferece quando a forma em desenho já tem vértices bastantes; **suspender**,
      só com ferramenta na mão; **editar** e **apagar**, só com geometria no mapa; **recortar**, só
      com área desenhada.
- [ ] O **cursor do mapa** diz o que está na mão: mira para desenhar, mão para modificar e um X em
      tinta de erro para apagar.
- [ ] **Arrastar pela alça** leva a bancada para onde o ponteiro soltar — perto de uma lateral ela
      encaixa **em pé**; perto do rodapé se deita e se guarda; no meio da tela fica deitada onde foi
      largada. O gesto **não arrasta o mapa** nem dá zoom.
- [ ] O **encaixe** (snap) nasce ligado, e a torrezinha da bancada o desliga e religa.
- [ ] Com um **modal aberto**, a bancada se recolhe junto com o resto da moldura fixa.
- [ ] O design foi aprovado no mock, e as peças estão em `static/src/tema-dimap.dev.css` e no
      styleguide **antes** de qualquer template da aplicação usar as classes.

## 3 · Domínio
Iteração de interface: nenhum model, nenhuma migração, nenhum domínio novo. A geometria desenhada
não sai do navegador nesta iteração — não há DTO, rota nem contrato de servidor.

O mapa é o canvas singleton de [mapa/001](../mapa/001-infra-mapa-e-logradouro-linha.md), e os
controles de mapa são os de [design/016](016-controles-mapa-onsen.md); a pergunta que esta SPEC faz
a eles é: **quem mais escreve sobre esse canvas, além do resultado da busca?**

O catálogo das ferramentas é a tabela que liga a categoria da bancada às formas do plugin:

| Categoria | Ferramentas do Geoman | Cor do traço |
|---|---|---|
| Ponto | `Marker` | `agua-500` |
| Linha | `Line` | `accent` |
| Polígono | `Polygon`, `Rectangle`, `Circle` | `sakura-500` |
| Modificar | `edit`, `drag`, `rotate`, `cut` | — |

Apagar (`remove`) fica fora do catálogo: destruir não é uma forma de modificar, e mora no poço da
bancada com os demais controles.

**Mock:** [018-mock-bancada-desenho.html](018-mock-bancada-desenho.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Envio da geometria desenhada ao servidor (GeoJSON, DTO, rota) — sem dono ainda.
- Uso do desenho como entrada de uma ação administrativa (recorte de amostragem, área de estudo) — sem dono ainda.
- Medida de área, perímetro e distância do que foi desenhado — sem dono ainda.
- Camada de texto do Geoman (`Text`) — sem dono ainda.
- Persistência do desenho, da posição e do encaixe da bancada entre recargas — sem dono ainda.

## 5 · Peças de referência a compor
- `@static/src/tema-dimap.dev.css` → `.glass-panel-thick`, `.card-well`: materiais do corpo e dos poços.
- `@static/src/tema-dimap.dev.css` → `.etched`, `.etched-line`: gravação do estojo e do fio da alça.
- `@static/src/tema-dimap.dev.css` → `.gaveta-alca`: o par repouso/entintado que o fio da alça repete.
- `@static/src/tema-dimap.dev.css` → `.torre-camadas`: coreografia da torrezinha que a `.torre-snap` espelha.
- `@static/src/tema-dimap.dev.css` → `.moldura-fixa`: recolhimento sob modal aberto.
- `@static/src/tema-dimap.dev.css` → `.toggle-onsen`: interruptor do encaixe.
- `@static/src/js/mapa/init.js` → `montarMapaBase`: ponto único onde o mapa é criado e os controles recebem a instância.
- `@templates/mapping/_glifos_mapa.html` → `#glifo-camadas`, `#glifo-menos`, `#glifo-mais`: glifos que já existem e não se redefinem.
- Skills: `mock`, `componentes-frontend`, `leaflet-geoman`, `leaflet-map`, `escrever-testes`.

## 6 · Snippets

O plugin entra ao lado do Leaflet, e a toolbar nativa nunca é ligada — `addControls` não é chamado
em lugar nenhum.

**`templates/base.html`**
```html
{# Leaflet-Geoman: depois do Leaflet, que ele estende. A toolbar nativa fica desligada. #}
<script src="https://unpkg.com/@geoman-io/leaflet-geoman-free@2.20/dist/leaflet-geoman.min.js"></script>
```

**`static/src/js/mapa/desenho/catalogo.js`** — a tabela do §3 em código, e mais nada.
```javascript
// A ordem aqui é a ordem dos glifos na linha: o catálogo é a fonte do submenu.
export const GEOMETRIAS = {
  ponto: [{ id: "Marker", rotulo: "Marcador", glifo: "#glifo-ponto" }],
  linha: [{ id: "Line", rotulo: "Linha", glifo: "#glifo-linha" }],
  poligono: [
    { id: "Polygon", rotulo: "Polígono", glifo: "#glifo-poligono" },
    { id: "Rectangle", rotulo: "Retângulo", glifo: "#glifo-retangulo" },
    { id: "Circle", rotulo: "Círculo", glifo: "#glifo-circulo" },
  ],
  modificar: [
    { id: "edit", rotulo: "Vértices", glifo: "#glifo-vertices" },
    { id: "drag", rotulo: "Mover", glifo: "#glifo-mover" },
    { id: "rotate", rotulo: "Girar", glifo: "#glifo-girar" },
    { id: "cut", rotulo: "Recortar", glifo: "#glifo-recortar" },
  ],
};

// Cada modo global do plugin e o trio de métodos que o liga, desliga e responde se está ligado.
export const MODOS_GLOBAIS = {
  edit: ["enableGlobalEditMode", "disableGlobalEditMode", "globalEditModeEnabled"],
  drag: ["enableGlobalDragMode", "disableGlobalDragMode", "globalDragModeEnabled"],
  rotate: ["enableGlobalRotateMode", "disableGlobalRotateMode", "globalRotateModeEnabled"],
  cut: ["enableGlobalCutMode", "disableGlobalCutMode", "globalCutModeEnabled"],
  remove: ["enableGlobalRemovalMode", "disableGlobalRemovalMode", "globalRemovalModeEnabled"],
};
```

**`static/src/js/mapa/desenho/ferramentas.js`** — o adaptador do plugin: quem está ligado, o que
ligar e quando o Ok se arma. O estado da bancada é **lido do plugin**, nunca guardado em paralelo.
```javascript
// Quem está na mão: no modo de desenho o plugin não diz a forma, então ela vem do evento
// pm:globaldrawmodetoggled, guardado pelo chamador.
export function ferramentaAtiva(mapa, formaEmDesenho) {
  if (mapa.pm.globalDrawModeEnabled()) return formaEmDesenho;
  return Object.keys(MODOS_GLOBAIS).find((id) => mapa.pm[MODOS_GLOBAIS[id][2]]()) || null;
}

// Só forma de múltiplos vértices tem o que concluir: marcador, retângulo e círculo terminam no
// próprio clique que os cria.
const VERTICES_MINIMOS = { Line: 2, Polygon: 3 };

export function podeConcluir(mapa, forma) {
  const minimo = VERTICES_MINIMOS[forma];
  if (!minimo || !mapa.pm.globalDrawModeEnabled()) return false;
  const desenho = mapa.pm.Draw[forma];
  if (!desenho || !desenho._layer) return false;
  const vertices = desenho._layer.getLatLngs();
  const traco = Array.isArray(vertices[0]) ? vertices[0] : vertices;
  return traco.length >= minimo;
}

// Clicar na ferramenta que já está na mão a devolve à bancada: o toggle é o mesmo gesto.
export function acionar(mapa, id, formaEmDesenho) {
  const jaAtiva = ferramentaAtiva(mapa, formaEmDesenho) === id;
  desligarTudo(mapa);
  if (jaAtiva) return;
  if (MODOS_GLOBAIS[id]) mapa.pm[MODOS_GLOBAIS[id][0]]();
  else mapa.pm.enableDraw(id, opcoesDesenho(id));
}
```

**`static/src/js/mapa/desenho/bancada.js`** — a entrada. Sai do ar sem o partial no DOM, como o
`inicializarControlesMapa`.
```javascript
export function inicializarBancadaDesenho(mapa) {
  const conjunto = document.getElementById("bancada-conjunto");
  if (!conjunto || !mapa) return;

  // Sem isto, arrastar a bancada arrasta o mapa e a roda sobre ela dá zoom.
  L.DomEvent.disableClickPropagation(conjunto);
  L.DomEvent.disableScrollPropagation(conjunto);
  ...
}
```

**`static/src/js/mapa/desenho/arrasto.js`** — a bancada que anda pela tela: limiar do clique, faixa
de captura das bordas e a transmutação de eixo.
```javascript
// Abaixo deste deslocamento o gesto ainda é clique: sem isso, todo toque na alça viraria arrasto
// de um pixel e a bancada nunca abriria.
const LIMIAR_ARRASTO = 4;
// Faixa de captura das bordas, generosa de propósito: errar por pouco deixaria a bancada boiando
// colada na borda, que é o pior dos dois mundos.
const MARGEM_ENCAIXE = 110;

// Quem decide o encaixe é o PONTEIRO, não o centro da bancada: presa dentro do mapa, a caixa nunca
// leva o próprio centro até a margem, e o encaixe lateral não dispararia.
export function encaixarNaBorda(ponteiroX, ponteiroY) { ... }
```

**`static/src/js/mapa/init.js`**
```javascript
function montarMapaBase() {
  ...
  inicializarControlesMapa(mapa, baseMaps);
  inicializarBancadaDesenho(mapa);   // NOVO nesta SPEC
}
```

**`templates/mapping/_bancada_desenho.html`** — o organismo, incluído pela home. Estático: nenhum
contexto de view, nenhum HTMX (o submenu é a linha que o JS monta a partir do catálogo).

**`templates/mapping/_glifos_desenho.html`** — os `defs` dos glifos da bancada, no mesmo formato do
`_glifos_mapa.html`.

**`static/src/tema-dimap.dev.css`** — as peças do mock portadas tal e qual: os átomos
`.bancada-alca`, `.bancada-desenho__categoria`, `.bancada-desenho__controle` e
`.bancada-submenu__tool`; as moléculas `.bancada-desenho` e `.bancada-submenu`; e o organismo
`.bancada-conjunto` com a `.torre-snap`. Os cursores do mapa ficam **fora** do `@layer components`:
```css
/* O CSS do Leaflet e do Geoman entra por <link>, sem camada, e regra sem camada vence regra em
   camada — dentro do layer estas eram silenciosamente ignoradas. */
.mapa-cursor--desenhar,
.mapa-cursor--desenhar .leaflet-interactive {
  cursor: crosshair;
}
```

## 7 · Caveats
O Geoman entra no `base.html`, ao lado do Leaflet, e chega a toda página. Carregá-lo só na home
dependeria da ordem entre script clássico e módulo adiado — sutil demais para o ganho, e o Leaflet
já é global pelo mesmo motivo. Custo: ~200 KB de JS descem em telas administrativas que não têm
mapa.

O botão **Concluir** lê `mapa.pm.Draw[forma]._layer` e chama `_finishShape()`, API privada do
plugin. Não há caminho público para saber quantos vértices a forma em desenho já tem nem para
encerrá-la de fora. Custo: uma atualização do Geoman pode calar o botão sem quebrar mais nada.

O bloco de cursores vive fora do `@layer components`, contra a organização do `input.css`. Regra sem
camada vence regra em camada independentemente de especificidade, e o CSS do plugin entra por
`<link>` sem camada. Custo: essas regras não obedecem à ordem declarada no `input.css` e só podem
ser vencidas por outra regra sem camada.

O estado da bancada — ferramenta na mão, onde ela está encaixada, o que foi desenhado — vive no
navegador. É estado visual de controle e geometria ainda não submetida, não estado de domínio
(CLAUDE.md §3.1). Custo: nada disso sobrevive a uma recarga da página.

Os testes do §8 não cobrem comportamento de JavaScript: o projeto não tem infraestrutura de teste de
JS nem de render, como já registrado em design/017. Custo: o que se fixa é que as peças chegam ao
HTML e que os módulos existem — o encaixe, a transmutação e o armar dos botões só têm prova no
smoke test manual.

## 8 · Testes (TDD)
- `test_home_traz_a_bancada_de_desenho` — a home traz `#bancada-conjunto` guardado
  (`bancada-conjunto--fechada`, `data-dock="bottom"`) e carrega `desenho/bancada.js` como módulo.
- `test_bancada_traz_as_categorias_de_geometria` — o partial traz um `[data-categoria]` para ponto,
  linha e polígono, e o lápis do poço declara `data-categoria="modificar"`.
- `test_poco_da_bancada_nasce_desarmado` — apagar, concluir e suspender nascem `disabled`, e o
  encaixe nasce com `.bancada-desenho__controle--ligado`.
- `test_torre_do_encaixe_nasce_fechada_e_ligada` — `#torre-snap` nasce com `torre-snap--fechada`, o
  botão que a abre aponta para ela por `aria-controls`, e o `.toggle-onsen` vem marcado.
- `test_glifos_do_desenho_definem_os_simbolos_da_bancada` — `_glifos_desenho.html` define todos os
  `id` de glifo citados pelo partial e pelo catálogo, sem redefinir os do `_glifos_mapa.html`.
- `test_catalogo_cobre_as_categorias_do_partial` — toda categoria do partial tem entrada em
  `GEOMETRIAS`, e `remove` não está no catálogo.
- `test_toolbar_nativa_do_geoman_nunca_e_ligada` — nenhum módulo de `js/mapa/` chama `addControls`.
- `test_geoman_carrega_depois_do_leaflet` — no `base.html`, o script do plugin vem depois do script
  do Leaflet.
- `test_tela_administrativa_nao_traz_a_bancada` — uma tela sem mapa não traz `#bancada-conjunto`.
- `test_styleguide_registra_as_pecas_da_bancada` — `/design_system` renderiza a `.bancada-conjunto`
  e os quatro átomos novos.
