---
name: componentes-frontend
description: Design system "Onsen de Inverno" e padronização dos componentes de front-end do DIMAP GeoCoder (Atomic Design sobre Tailwind 4 + daisyUI 5 + HTMX). Sempre ative ao trabalhar na interface web, views ou templates HTML.
---

# Design System "Onsen de Inverno" — DIMAP GeoCoder

Esta skill define o design system do projeto e **como construir componentes com Atomic Design**.
Ela não lista o que existe — quem lista é a aplicação.

**A cadeia tem um único ponto editável:**

> átomo novo → `static/src/tema-dimap.dev.css` → o build emite → **`/design_system`** mostra.

`tema-dimap.dev.css` é a fonte única (SPEC design/004); `static/dist/output.css` é o artefato que o
build produz dela; e a rota `/design_system` é uma página da aplicação que carrega **esse mesmo
arquivo**. Ninguém consegue registrar peça que a aplicação não tem, nem esquecer de registrar peça
que ela tem.

Consulte, sob demanda:
- **`/design_system`** — o catálogo visual do que existe (é o contrato visual do projeto).
- **`references/pecas.md`** — as armadilhas de uso de cada peça, que a tela não mostra.
- **`references/paleta.json`** — os valores das escalas.

Componente novo nasce seguindo o método do §2.

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
- **Coreografia**: `.transition-glass`, `.glass-hide-up`, `.cinematic-blur-layer`, `.moldura-fixa` (§7).

Regras dos tokens:
- Cor nova **entra numa escala existente** ou não entra. Proibido hex solto no HTML/CSS de componente.
- Material novo **compõe os tokens de vidro** existentes; não se inventa outro vocabulário de sombra/blur.
- Token é classe com `@apply` **apenas de utilities Tailwind**. **NUNCA faça `@apply` de classe do
  daisyUI** (`btn`, `input`, `badge`...). Atenção à armadilha: no build da aplicação isso **compila
  sem erro**, porque o daisyUI entra como `@plugin` e vira utility resolvível — mas nos mocks de
  SPEC, onde ele é folha separada servida por CDN, a mesma linha derruba a folha inteira. A falha é
  assimétrica: passa na aplicação e mata o mock. A classe daisyUI fica no HTML, empilhada com o
  token (§2.2).

### 2.2 Átomos (elementos mínimos)
O menor elemento com identidade própria: botão, input, badge, kbd, ícone, tooltip, toggle, loading.
**Um átomo = daisyUI (comportamento/estrutura) + token do DS (pele)**, empilhados no HTML:

```html
<button class="btn btn-onsen">Buscar</button>
<input  class="input input-glass pl-11" />
<span   class="badge badge-poligono badge-sm">Lote</span>
<label  class="btn btn-ghost btn-glass btn-circle">…</label>
```

Os átomos que existem estão renderizados em **`/design_system`**; as armadilhas de uso de
cada um, em `references/pecas.md`.

### 2.3 Moléculas (combinações pequenas)
Grupo de átomos funcionando como uma unidade: o grupo de busca (input + botão), o item de sugestão
(`.suggestion-item` + `.icon-bubble` + badge de tipo), o stat tile (overline + valor num `.card-well`),
o item de layer (cor + nome + badge + toggle + lixeira). Moléculas ganham classe própria **só quando
têm layout interno recorrente** (`.suggestion-item`); caso contrário são apenas composição de átomos
com utilities de layout no HTML.

As peças que existem estão em **`/design_system`**; como cada uma é acionada e o que já
quebrou nela, em `references/pecas.md` — leia antes de compor com uma delas.

### 2.4 Organismos (seções de domínio)
Seções autônomas da interface: o painel de busca completo, a gaveta de detalhes do imóvel, o widget
de usuário, o painel de camadas do projeto. **Organismo = partial Django/HTMX** (`_gaveta_lote.html`,
`_painel_busca.html`): é aqui que o Atomic Design encontra a arquitetura do projeto —
**partials resolvem DOMÍNIO, classes `@apply` resolvem DESIGN**:
- Um partial por entidade de negócio. Não misture domínios com `if/else` no mesmo HTML.
- O "mesmo DNA" visual entre entidades vem das classes compartilhadas (átomos/materiais), nunca de
  copiar blocos de utilities.

### 2.5 Checklist para qualquer componente novo
1. Já existe em `/design_system`? **Reutilize.**
2. O daisyUI tem o comportamento? Use o componente dele como base.
3. Precisa de pele nova? Componha **tokens existentes**; se surgir cor/sombra nova, ela entra como
   token antes de aparecer em componente.
4. Classe nova só com `@apply` de utilities; classe daisyUI empilhada no HTML.
5. Renderize o novo componente em `templates/core/design_system.html` (é o contrato visual).

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
brilho de gelo na quina: `inset 0 1px 0 white/80`. CSS pronto em `static/src/tema-dimap.dev.css` (§8).

| Material | Uso | Tinta |
|---|---|---|
| `.glass-panel` | painel flutuante padrão (fino, 10px — **sobre o mapa**) | escura |
| `.glass-panel-thick` | segunda espessura (blur 28px, 88%→76%, aresta `white/70`) — **vidro sobre interface**, onde o fino deixa passar demais. Primitivos `.glass-blur-thick` / `.glass-bg-thick`. Quem esconde o fundo é o **blur**: acima de ~90% de branco o material deixa de ler como gelo (SPEC design/008 v2) | escura |
| `.glass-drawer-panel` | gaveta lateral (texto denso; blur 12px, mais opaco) | escura |
| `.card-well` | poço rebaixado: sub-cards dentro de painéis (stats, metadados) | escura |
| **empilhado** | vidro sobre vidro **não se repinta** (SPEC design/009): `.glass-panel`, `.card-well` e `.upload-well` dentro de outro material de vidro ficam só com desfoque, aresta e sombra — a pintura acontece uma vez por pilha. Regra de descendência no tema: **nenhum markup muda**, e a peça volta a pintar sozinha quando renderizada fora. Única exceção: `.modal-box-glass` | escura |
| `.glass-panel-deep` | variante escura **pontual**: tooltips, contraste invertido | clara (`rocha-100`, acentos `agua-300`/`madeira-300`) |
| `.th-onsen-bandeja` | bandeja do cabeçalho de tabela: `94%→86%` sobre blur 56px — a **única** densidade fora das três, e só porque ela separa um cabeçalho grudento das linhas que correm por trás (§2.3) | escura |
| `.modal-glass` + `.modal-box-glass` | modal: a cena **embaça** o fundo a 16px (nunca escurece) e a caixa é a **terceira densidade** — 97%→88%, blur 28px, aresta `white/80` —, escrita no próprio `.modal-box-glass` (SPEC design/008 v2). O modal não flutua sobre a interface: ele a substitui enquanto está aberto, e é o único lugar em que a opacidade alta é o acerto. O `.glass-panel-thick` empilhado no markup continua ali e é vencido por ordem. Abre/fecha por `checkbox` nativo | escura |

Regras:
- **A pintura é uma por pilha** (SPEC design/009). Peça nova não precisa saber onde vai ser
  renderizada: quem lê a profundidade é o CSS, no DOM. Não crie variante "aninhada" de peça alguma.
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
- **O snippet acima é da home** — é a única tela com Leaflet no fundo. Toda tela que não é a home
  roda sobre o **fundo da área administrativa** — a mesma lente sobre a ortofoto **pré-gerada** em
  tons de cinza, à deriva (SPEC design/010) —, e ele já existe pronto: `{% include
  "mapping/_mapa_admin.html" %}`, que traz o canvas, a lente e o `.fundo-controle`. O `.fundo-controle`
  tem posicionamento responsivo governado no CSS: em telas amplas (`xl:`), repousa fixo no canto
  inferior direito (`xl:fixed xl:bottom-6 xl:right-6 xl:z-20`); em telas estreitas (< xl), entra no
  fluxo como nova linha abaixo do conteúdo alinhado à direita (`self-end ml-auto mt-4`), e sob modais
  abertos recolhe via `:root:has(.modal-toggle:checked)`. Página nova não recopia camada nenhuma — inclusive
  `/design_system`, que faz `{% include "mapping/_mapa_admin.html" %}` como qualquer outra. Os mocks
  de SPEC montam o mesmo conjunto por `examples/fundo-admin.js` da skill `mock`.

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
arquivo. Dois consumidores, com mecanismos diferentes:

1. **A aplicação, por build** (SPEC infraestrutura/004). `static/src/input.css` é a entrada —
   ordem das camadas, `source(none)`, `@import` do tema, `@plugin "daisyui"` e os `@source` — e o
   serviço `tailwind` do `docker compose` compila em watch para `static/dist/output.css`. Toda
   página, `/design_system` inclusive, carrega esse arquivo por `{% static 'output.css' %}`. Não há
   CDN: a aplicação não busca Tailwind nem daisyUI na rede.
2. **Os mocks de SPEC**, por compilador de browser (`@tailwindcss/browser` + daisyUI por CDN):
   fazem `fetch` do tema e o injetam num `<style type="text/tailwindcss">`, no mesmo bloco em que
   escrevem as peças **novas** da SPEC. Precisam disso porque renderizam CSS que ainda não existe
   em lugar nenhum — e por isso **exigem servidor com root na raiz** (Live Server); não abrem via
   `file://`. Ver skill `mock`.

Consequência do (1) para quem cria peça: só entra no CSS o que o `@source` descobre como literal em
`templates/`, `apps/`, `static/src/js` ou `services/utils/erros_formulario`. Peça portada para o
tema é imune a isso — vira `@layer components` e sai sempre.

Cuidados que já quebraram build/render:
- **A ordem das camadas é declarada no `input.css`, não herdada do `@import`.** O daisyUI emite os
  componentes dele dentro de `utilities` e o design system vive em `components`; na ordem padrão do
  Tailwind (`theme, base, components, utilities`) o daisyUI **vence** o tema, e o resultado é modal
  opaco, foco sem halo e avisos sem cor — sem erro nenhum no build. Por isso a primeira linha é
  `@layer properties, theme, base, utilities, components;`.
- `@apply` **só de utilities** (nunca classes daisyUI) — ver §2.1.
- `shadow-inner` não existe no Tailwind 4; use `shadow-[inset_...]` arbitrária.
- **`!important` no CSS é proibido** (CLAUDE.md §3.4) — salvo se pré-aprovado e estritamente necessário. Nunca use em `style` inline.
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

1. **Styleguide vivo:** a rota **`/design_system`** (`templates/core/design_system.html`) — tokens,
   átomos, moléculas e organismos renderizados sobre o fundo oficial da área administrativa, com o
   CSS compilado da própria aplicação. **É o contrato visual**; componente novo é registrado aqui.
2. **Armadilhas de uso das peças:** `references/pecas.md` — como cada peça é acionada e o que já
   quebrou nela. O que a tela não mostra.
3. **CSS dos tokens:** `static/src/tema-dimap.dev.css` — a **fonte única** (§8). O espelho
   `references/design_system.css` foi **apagado**: era órfão (ninguém o importava) e mostrava a
   receita anterior à SPEC design/006. Não recriar.
4. **Paleta:** `references/paleta.json` — escalas e papéis em JSON (fonte da verdade dos valores).
5. **Referências visuais:** `references/onsen_inverno_moodboard.jpg`,
   `references/referencia_original_ui_1.jpg`, `references/referencia_original_ui_2.jpg` — a água
   límpida ciano, a luz fria e o nível de polimento esperado do vidro;
   `references/referencia_original_ui_3.jpg` — os macacos no onsen, origem do rosa da escala
   **sakura** (§3.1); `references/referencia_etched_glass.jpg` — cristal gravado a ácido, onde o
   traço tem gradação interna em vez de contorno: a leitura que o token `.etched` persegue (§2.1).
