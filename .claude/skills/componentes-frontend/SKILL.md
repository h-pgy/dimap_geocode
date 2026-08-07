---
name: componentes-frontend
description: Design system "Onsen de Inverno" e padronização dos componentes de front-end do DIMAP GeoCoder (Atomic Design sobre Tailwind 4 + daisyUI 5 + HTMX). Sempre ative ao trabalhar na interface web, views ou templates HTML.
---

# Design System "Onsen de Inverno" — DIMAP GeoCoder

Esta skill define o design system do projeto e **como construir componentes com Atomic Design**.
A referência visual validada vive em `examples/design_system.html` (styleguide sobre mapa vivo) e
`examples/mock_ui.html` (aplicação mockada). Qualquer componente novo nasce seguindo o método do §2.

## 1. O Conceito: água límpida sob luz fria de inverno

O usuário observa a cidade através de uma **água límpida em tons ciano** (o mapa), sob a luz fria de
um dia claro de inverno. Sobre essa água flutuam **placas de gelo fosco** (os painéis de UI), com
arestas que capturam a luz. A tinta que escreve sobre o gelo é **escura**: azul-rocha para o corpo
de texto e **madeira quente para os títulos** — o único calor orgânico da cena.

- **O mapa (água límpida):** claro, banhado de ciano, sempre visível e legível. Nunca escurecido.
- **O vidro (gelo fosco):** branco translúcido, blur forte o bastante para separar figura do fundo.
- **A tinta (rocha + madeira):** escura sobre o gelo. Regra de ouro de leitura: **tinta escura
  sobre vidro claro**. O inverso (texto claro) só existe no material `glass-panel-deep` (§5).
- **O ciano (água/energia):** cor de ação e brilho — gradientes de botão, glows, focos, códigos.

## 2. Atomic Design — o método para criar componentes

O design system tem **quatro camadas**. Toda peça de UI pertence a exatamente uma delas:

```
TOKENS  →  ÁTOMOS  →  MOLÉCULAS  →  ORGANISMOS
(design)   (elementos) (combinações) (seções de domínio)
```

### 2.1 Tokens (a camada de design)
Valores e materiais compartilhados, definidos **uma única vez** no CSS de entrada:
- **Cores**: as escalas `agua-*`, `rocha-*`, `madeira-*` e os papéis do tema daisyUI (§3).
  Definidas via `@theme` (Tailwind 4) + tema daisyUI.
- **Tipografia**: Roboto + Roboto Mono e a hierarquia do §4.
- **Materiais de vidro**: classes `@apply` que agrupam utilities — `.glass-blur`, `.glass-bg`,
  `.glass-bg-deep`, `.glass-edge`, `.glass-shadow`, `.glass-glow` — e os **materiais compostos**
  `.glass-panel`, `.glass-panel-deep`, `.glass-drawer-panel`, `.card-well` (§5).
- **Gravação no gelo** (`.etched`, `.etched-lg`, `.etched-inked`, `.etched-deeper`,
  `.etched-rotulo`, SPEC user_admin/013): o registro **oposto** ao `.icon-glow` — onde ele acende,
  este **escava**. O relevo segue a silhueta da própria forma, via **filtro SVG**
  (`templates/partials/_filtros_gravacao.html`, incluído no `base.html`) — sem os `defs` no
  documento a classe existe e não desenha nada. Três restrições andam com ele: **nunca carrega
  informação**, só afordância; **só vale sobre vidro claro**; e quando o sulco precisa *nomear*
  algo, a tinta sobe (`.etched-rotulo`). Duas medidas só — acima de ~32px, `.etched-lg`.
- **Coreografia**: `.transition-glass`, `.glass-hide-up`, `.cinematic-blur-layer` (§7).

Regras dos tokens:
- Cor nova **entra numa escala existente** ou não entra. Proibido hex solto no HTML/CSS de componente.
- Material novo **compõe os tokens de vidro** existentes; não se inventa outro vocabulário de sombra/blur.
- Token é classe com `@apply` **apenas de utilities Tailwind**. **NUNCA faça `@apply` de classe do
  daisyUI** (`btn`, `input`, `badge`...): o build quebra e a folha inteira cai. A classe daisyUI fica
  no HTML, empilhada com o token (§2.2).

### 2.2 Átomos (elementos mínimos)
O menor elemento com identidade própria: botão, input, badge, kbd, ícone, tooltip, toggle, loading.
**Um átomo = daisyUI (comportamento/estrutura) + token do DS (pele)**, empilhados no HTML:

```html
<button class="btn btn-onsen">Buscar</button>
<input  class="input input-glass pl-11" />
<span   class="badge badge-poligono badge-sm">Lote</span>
<label  class="btn btn-ghost btn-glass btn-circle">…</label>
```

Átomos existentes (ver todos renderizados em `examples/design_system.html`, seção 2):
| Átomo | Classe do DS | Sobre |
|---|---|---|
| Botão de energia (CTA) | `.btn-onsen` | gradiente `agua-300→500`, tinta escura, glow ciano |
| Botão de vidro | `.btn-glass` | gelo fosco circular/pill; ações secundárias e ícones |
| Botão de criação inline | `.btn-criar-inline` | círculo de gelo com `+` em tinta ciana ao lado de um campo: "criar agora o que falta no catálogo" |
| Input de vidro | `.input-glass` | fundo `white/45`, foco com anel ciano |
| Badges de geometria | `.badge-ponto` `.badge-linha` `.badge-poligono` | tipo do resultado/camada |
| Badges semânticos | `badge-{info,success,warning,error} badge-soft` | estado do sistema (daisyUI puro) |
| Ícone com brilho | `.icon-glow` | `agua-600` + drop-shadow ciano |
| Seta de ordenação | `.sort-etched` | a gravação com alvo próprio, à direita da célula; enche de água em `aria-sort` e gira 180° em `descending` |
| Botão gravado | `.btn-etched` | a gravação em corpo de botão (o "limpar filtros"); enche de água no hover |
| Ícone gravado em botão de vidro | `.icon-etched` | o glifo dentro de um `.btn-glass`, onde quem carrega a afordância é o botão |
| Ponto da unidade | `.dot-unidade` | o `.paint-well` em escala de marca; o hex chega em `--cor-unidade` |
| Overline | `.text-overline` | rótulo 11px caps `rocha-700` |
| Código | `.text-code` | Roboto Mono `agua-700` (SQL, codlog) |

Para criar um átomo novo: (1) confira se um componente daisyUI já resolve o comportamento;
(2) crie **uma** classe `@apply` de utilities com a pele do DS; (3) registre-o no styleguide.

### 2.3 Moléculas (combinações pequenas)
Grupo de átomos funcionando como uma unidade: o grupo de busca (input + botão), o item de sugestão
(`.suggestion-item` + `.icon-bubble` + badge de tipo), o stat tile (overline + valor num `.card-well`),
o item de layer (cor + nome + badge + toggle + lixeira). Moléculas ganham classe própria **só quando
têm layout interno recorrente** (`.suggestion-item`); caso contrário são apenas composição de átomos
com utilities de layout no HTML.

**Campo de seleção de vidro** (`.select-onsen`, SPEC user_admin/011): opt-in por
`data-select-onsen` no `<select>` renderizado pelo servidor. O `<select>` continua sendo o campo
(valor, envio, `change` nativo); `static/src/js/ui/select_onsen.js` monta o gatilho
(`.select-onsen-trigger`, o `.select-glass` de hoje) e a lista (`.select-onsen-panel`, gelo espesso
na top layer via `popover`). Carregue o módulo na página que usa o marcador — marcar o campo não
basta. Filtro por texto a partir de seis opções.

**Campo com criação inline** (`.form-field-inline-action`, SPEC user_admin/012): o `.form-field`
com o controle e o `.btn-criar-inline` na mesma linha — o controle estica, o botão não. O gatilho é
um `<label for>` do modal, e o modal fica **fora** do formulário (formulário aninhado é HTML
inválido).

**Tabela de vidro** (`.table-onsen`, `.table-onsen-wrap`, `.table-onsen-poco`, SPEC
user_admin/013): a **inversão dos materiais** — corpo em poço rebaixado (`.card-well`) e cabeçalho
em placa de gelo sobre ele. A caixa rola por conta própria (a viewport nunca rola na horizontal) e o
cabeçalho é grudento; a folga do poço é padding do `.card-well`, **fora** do rolador. Linhas
separadas **em luz**, sem zebra, e hover que **acende** o gelo.

**Bandeja e célula de cabeçalho** (`.th-onsen-bandeja`, `.th-onsen`, `.th-onsen-campo`,
`.th-onsen-input`, `.th-onsen-gravado`): o cabeçalho é **uma superfície** e cada coluna é uma peça
assentada sobre ela — clicar a faz **afundar** e virar campo, porque campo aqui é sempre coisa
rebaixada. **Afundado = a coluna tem filtro**, não "alguém clicou": o CSS lê o valor com
`:has(input:not(:placeholder-shown))`, sem estado de UI em JavaScript. A régua **abre inteira** (o
campo de uma coluna abre o de todas). Coluna que não responde **não tem peça**: o rótulo é gravado
direto na bandeja — a ausência da peça é a mensagem, sem cinza de desabilitado.

**Barra de rolagem gravada** (`.scroll-etched`, `.scroll-etched-thumb`, `.scroll-etched-ativa`,
`.scroll-etched-ociosa`): trilho sulcado e polegar de água, para **qualquer** `.card-well` rolável.
Opt-in por `data-scroll-etched` no poço, com `[data-rolador]`, `[data-barra]`, `[data-polegar]` e
`[data-cabecalho]` (opcional) dentro dele; par com `static/src/js/ui/scroll_etched.js` — carregue o
módulo na página, marcar o markup não basta. É **elemento**, não `::-webkit-scrollbar`: o pseudo não
existe no Firefox, no Chrome troca a barra flutuante por uma clássica sempre visível, e em ambos
ocupa a altura inteira do rolador (correria ao lado da bandeja). Rolar continua sendo do navegador.

### 2.4 Organismos (seções de domínio)
Seções autônomas da interface: o painel de busca completo, a gaveta de detalhes do imóvel, o widget
de usuário, o painel de camadas do projeto. **Organismo = partial Django/HTMX** (`_gaveta_lote.html`,
`_painel_busca.html`): é aqui que o Atomic Design encontra a arquitetura do projeto —
**partials resolvem DOMÍNIO, classes `@apply` resolvem DESIGN**:
- Um partial por entidade de negócio. Não misture domínios com `if/else` no mesmo HTML.
- O "mesmo DNA" visual entre entidades vem das classes compartilhadas (átomos/materiais), nunca de
  copiar blocos de utilities.

### 2.5 Checklist para qualquer componente novo
1. Já existe no styleguide (`examples/design_system.html`)? **Reutilize.**
2. O daisyUI tem o comportamento? Use o componente dele como base.
3. Precisa de pele nova? Componha **tokens existentes**; se surgir cor/sombra nova, ela entra como
   token antes de aparecer em componente.
4. Classe nova só com `@apply` de utilities; classe daisyUI empilhada no HTML.
5. Renderize o novo componente no styleguide (é o contrato visual do projeto).

## 3. Paleta

Quatro escalas próprias (utilities `bg-agua-400`, `text-madeira-700`, `bg-sakura-500`, etc.) + papéis daisyUI.
Fonte da verdade dos valores: `references/paleta.json`.

### 3.1 Escalas
- **Água** (primária — energia, luz, ações, geometria de *ponto*):
  `100 #CAF0F8 · 200 #ADE8F4 · 300 #90E0EF · 400 #48CAE4 ★ · 500 #00B4D8 · 600 #0096C7 ✦ · 700 #0077B6 · 800 #023E8A · 900 #03045E`
  ★ tom de marca (preenchimentos, gradientes, brilhos). ✦ ciano de **texto/ação** sobre vidro claro
  (`agua-600`/`agua-700`). Os tons 100–400 são luz, **nunca texto sobre fundo claro**.
- **Rocha** (neutra — tinta, superfícies, profundidade):
  `100 #E0E1DD · 200 #C5CCD3 · 300 #A9BCD0 · 400 #8FA3BB · 500 #778DA9 · 600 #5B7290 · 700 #415A77 ✦ · 800 #2E4560 · 900 #1B263B · 950 #0D1B2A ★`
  ★ tinta padrão do corpo (`base-content`). ✦ rótulos secundários/overlines.
- **Madeira** (quente — tinta de títulos, acentos orgânicos):
  `100 #EDE0D4 · 200 #E6CCB2 · 300 #DDB892 · 400 #B08968 · 500 #9C6644 · 600 #7F5539 · 700 #5E412F ★ · 800 #46301F · 900 #2E1F16`
  ★ a tinta quente dos títulos sobre o gelo. Tons claros (200–300) só sobre `glass-panel-deep`.
- **Sakura** (rosa/magenta — o rubor dos macacos no onsen; **geometria de *polígono*** e destaque
  sobre a ortofoto, ref. `referencia_original_ui_3.jpg`):
  `100 #FBE3E9 · 200 #F6C4D2 · 300 #EFA0B8 · 400 #E5749B · 500 #D84F7F ★ · 600 #BC3A67 ✦ · 700 #97294F · 800 #6E1C3A · 900 #471226`
  ★ traço da geometria de polígono (lote), preenchimento na mesma cor a ~35%; variante condominial
  `sakura-700`. O rosa não tem contraparte na ortofoto (verdes/cinzas/marrons) e devolve a leitura
  que a madeira perdia ali. ✦ **texto/ação** sobre vidro claro (`sakura-600`/`sakura-700`). Os tons
  100–300 são luz, **nunca texto sobre fundo claro**.

### 3.2 Papéis do tema daisyUI (tema `dimap`, claro)
```
base-100 #F2F8FB · base-200 #E3EFF5 · base-300 #CFE2EB · base-content #0D1B2A
primary #0096C7 (content #F2FBFF) · secondary #5E412F (content #F6EEE6)
accent #0F766E (content #ECFDF9) · neutral #1B263B (content #E0E1DD)
info #0284C7 · success #059669 · warning #B45309 · error #DC2626 (contents claros)
radius: selector 1rem · field 0.5rem · box 1rem
```
**Cores semânticas são obrigatórias para estado do sistema** (Nielsen #1): sucesso de salvamento,
erro de busca, avisos (ex.: "Tombado" = `badge-warning badge-soft`). Nunca improvise verde/vermelho.

### 3.3 Cores por geometria (default das camadas do mapa)
Ponto = `agua-500` · Linha = `accent #0F766E` · Polígono = `sakura-500` (lote condominial =
`sakura-700`). Badges correspondentes: `.badge-ponto`, `.badge-linha`, `.badge-poligono`.
Se ponto/linha também perderem leitura sobre a **ortofoto**, o caminho de destaque é a mesma
escala **sakura** (§3.1) — nunca uma cor solta.

## 4. Tipografia

**Roboto** (UI/texto, pesos 400/500/700/900) + **Roboto Mono** (códigos). Hierarquia:
| Papel | Spec | Cor |
|---|---|---|
| Display | Roboto 900 · 30px · tracking-tight | `madeira-700` |
| Título de painel | Roboto 700 · 24px | `madeira-700` |
| Subtítulo | Roboto 700 · 18px | `rocha-950` |
| Corpo | Roboto 400 · 15px | `base-content/90` |
| Legenda | Roboto 400 · 13px | `base-content/70` |
| Overline (`.text-overline`) | Roboto 500 · 11px · caps · tracking 0.14em | `rocha-700` |
| Código (`.text-code`) | Roboto Mono 500 | `agua-700` |

Hierarquia se faz por **peso e tamanho**, nunca reduzindo contraste abaixo do legível.
Título flutuando direto sobre o mapa recebe halo frio: `drop-shadow-[0_1px_3px_rgba(255,255,255,0.8)]`.

## 5. Materiais de vidro (o gelo fosco)

Receita: **blur 10px** + gradiente branco translúcido + aresta `white/60` + **sombra em duas
camadas** — azul-fria `rgba(7,58,84,.25)` (separação) + ciana `rgba(72,202,228,.25)` (vida) — e o
brilho de gelo na quina: `inset 0 1px 0 white/80`. CSS pronto em `references/design_system.css`.

| Material | Uso | Tinta |
|---|---|---|
| `.glass-panel` | painel flutuante padrão (fino, 10px — **sobre o mapa**) | escura |
| `.glass-panel-thick` | segunda espessura (blur 20px, gelo mais leitoso) — **vidro sobre interface**, onde o fino deixa passar demais. Primitivos `.glass-blur-thick` / `.glass-bg-thick` | escura |
| `.glass-drawer-panel` | gaveta lateral (texto denso; blur 12px, mais opaco) | escura |
| `.card-well` | poço rebaixado: sub-cards dentro de painéis (stats, metadados) | escura |
| `.glass-panel-deep` | variante escura **pontual**: tooltips, contraste invertido | clara (`rocha-100`, acentos `agua-300`/`madeira-300`) |
| `.modal-glass` + `.modal-box-glass` | modal: a cena **embaça** o fundo (nunca escurece) e a caixa compõe `.glass-panel-thick`. Abre/fecha por `checkbox` nativo | escura |

Regras:
- Blur fraco (2px) é proibido: não separa figura do fundo. O mapa continua legível com 10px.
- Sombra preta pura é proibida; sombra **apenas ciana** também (não separa). Sempre as duas camadas.
- Nunca borda branca opaca contínua; a aresta é translúcida (`white/60`) + inset highlight.
- Hover de vidro **acende** o gelo (`hover:bg-white/60`/`white/70`), não muda de cor.

## 6. O mapa como canvas (água límpida)

O Leaflet é a tela inteira, atrás de tudo (`z-0`), **claro e legível**:
```html
<div id="map" class="absolute inset-0 z-0 saturate-[0.8] brightness-[1.05] contrast-[0.95]"></div>
<!-- tinta de água límpida -->
<div class="absolute inset-0 z-[1] pointer-events-none mix-blend-multiply bg-[#bfeaf5]/60"></div>
<!-- lente (efeito globo LEVE): vinheta ciana + desfoque de borda + luz fria central -->
<div class="absolute inset-0 z-[1] pointer-events-none bg-[radial-gradient(ellipse_at_center,transparent_55%,rgba(0,119,182,0.25)_100%)]"></div>
<div class="absolute inset-0 z-[1] pointer-events-none backdrop-blur-[1.5px] [mask-image:radial-gradient(ellipse_at_center,transparent_45%,black_95%)]"></div>
<div class="absolute inset-0 z-[1] pointer-events-none bg-[radial-gradient(ellipse_at_50%_38%,rgba(255,255,255,0.18),transparent_60%)]"></div>
```
- **Nunca escureça o mapa** nem aplique overlay preto/`bg-black/*` para dar foco.
- **Foco por desfoque**: ao abrir gaveta/modal, ligue a `.cinematic-blur-layer` (blur dinâmico em
  ~500ms) entre o mapa e o painel. O mapa embaça; nada escurece.
- A "lente" é óptica simulada por overlays `pointer-events-none`. **Proibido distorcer o mapa
  geometricamente** (transforms/SVG displacement): desalinha os cliques do Leaflet.

## 7. Coreografia, micro-interações e HTMX

- **Direções**: dados/busca (gavetas de lote, logradouro, inspeção) nascem **da esquerda**;
  sistema/gestão (conta, projetos, camadas) nasce **da direita**. Modais críticos: scale-up no centro.
- **UI concorrente se recolhe**: quando a gaveta abre, a barra de busca sai de cena via CSS de estado
  (`#lote-drawer:checked ~ .drawer-content #search-bar-container { opacity-0 -translate-y-5 scale-95
  pointer-events-none }`) — sem JavaScript imperativo.
- **Navbar compacta em tela estreita (< lg, SPEC design/005)**: com resultado no DOM, a barra de
  busca recolhida vira um pill de 3rem alinhado em `top-6` entre o chip da marca (monograma "D",
  `w-12 h-12`) e o widget de usuário (avatar `w-9 h-9`) — três placas de gelo independentes, nada
  de barra opaca. Tokens `.search-panel` (dono de largura/padding do painel — utility no markup
  venceria a regra de componente) e `.search-hints` (linha de dicas, some no compacto) +
  `@media (width < 64rem)` no `tema-dimap.dev.css`. Mesmo gatilho HATEOAS da `.search-hero`.
  Abaixo de lg os chips são sempre compactos, em `left-4`/`right-4`.
- **Todo interativo reage** a `hover:`/`focus:`/`active:`; transições `duration-300`–`500`.
- **HTMX é a SPA**: sem full page reload após a carga do mapa. Swaps com `.htmx-indicator` +
  `.loading` do daisyUI (a UI de vidro nunca bloqueia sem feedback). Use `.htmx-added`/`.htmx-swapping`
  para amarrar animações de entrada/saída dos partials.
- **JS restrito** (regra do projeto): callbacks de eventos HTMX e utilitários do Leaflet, nada mais.

## 8. Setup técnico (Tailwind 4 + daisyUI 5)

**`static/src/tema-dimap.dev.css` é a FONTE ÚNICA do design system** (SPEC design/004): tema
daisyUI como variáveis planas em `html[data-theme="dimap"]`, `@theme` (escalas do §3.1 + papéis
do §3.2) e `@layer components` (tokens/átomos/moléculas). Editar o design system = editar esse
arquivo. Três consumidores:

1. **Aplicação (dev/CDN):** `base.html` inclui o arquivo server-side —
   `<style type="text/tailwindcss">{% include "tema-dimap.dev.css" %}</style>`
   (`static/src` está nos `DIRS` do template engine só para isso).
2. **Mocks desta skill** (`examples/*.html`): loader JS faz fetch do arquivo e injeta o
   `<style>`. **Exigem servidor com root na raiz do projeto** (ex.: Live Server) — não abrem
   mais via `file://`.
3. **Build de prod (futuro):** `static/src/input.css` é só o esqueleto
   (`@import "tailwindcss"; @import "./tema-dimap.dev.css"; @plugin "daisyui"; @source ...`).

Cuidados que já quebraram build/render:
- `@apply` **só de utilities** (nunca classes daisyUI) — ver §2.1.
- `shadow-inner` não existe no Tailwind 4; use `shadow-[inset_...]` arbitrária.
- Sintaxe de important no Tailwind 4 é sufixo: `bg-transparent!` (não `!bg-transparent`).
- O CDN `@tailwindcss/browser` só processa `<style type="text/tailwindcss">` **inline** (não
  suporta `<link>`) — por isso o include (aplicação) e o fetch+inject (mocks). CSS de mock que
  use `@apply` precisa estar num bloco com esse `type`.
- **A string `@import` é PROIBIDA em qualquer bloco `text/tailwindcss` — inclusive dentro de
  comentário.** O CDN concatena todos os blocos e decide injetar o core do Tailwind com um
  `css.includes("@import")` ingênuo: se a string aparecer em qualquer lugar, ele assume que você
  importou tudo manualmente, pula a injeção e **todo** `@apply` falha com
  `Cannot apply unknown utility class` (o CSS inteiro cai). Já derrubou o tema em 2026-07-08:
  um comentário no cabeçalho do `tema-dimap.dev.css` mencionava "@import". Diagnóstico rápido:
  esse erro no console + tema morto ⇒ `grep '@import'` no `tema-dimap.dev.css` e nos mocks.

## 9. Arquivos de referência (ordem de consulta)

1. **Styleguide vivo:** `examples/design_system.html` — tokens, átomos, moléculas e organismos
   renderizados sobre o mapa real. **É o contrato visual**; componente novo é registrado aqui.
2. **Aplicação mockada:** `examples/mock_ui.html` — o design system aplicado na UX completa
   (barra única, gaveta, coreografia de foco).
3. **CSS dos tokens:** `static/src/tema-dimap.dev.css` — a **fonte única** (§8). O espelho
   `references/design_system.css` está **aposentado** pela SPEC design/004: não portar peça nova
   para lá.
4. **Paleta:** `references/paleta.json` — escalas e papéis em JSON (fonte da verdade dos valores).
5. **Referências visuais:** `references/onsen_inverno_moodboard.jpg`,
   `references/referencia_original_ui_1.jpg`, `references/referencia_original_ui_2.jpg` — a água
   límpida ciano, a luz fria e o nível de polimento esperado do vidro;
   `references/referencia_original_ui_3.jpg` — os macacos no onsen, origem do rosa da escala
   **sakura** (§3.1); `references/referencia_etched_glass.jpg` — cristal gravado a ácido, onde o
   traço tem gradação interna em vez de contorno: a leitura que o token `.etched` persegue (§2.1).
