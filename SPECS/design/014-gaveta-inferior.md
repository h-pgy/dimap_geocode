---
spec: design/014
versao: v1
atualizado_em: 2026-09-05
testes_tdd: false
implementado: true
markers_obrigatorios: []
changelog:
  - v1: versão inicial
---

# SPEC design/014 — Gaveta inferior (`.gaveta-inferior`)

## 1 · User story
Servidor da DIMAP lê o que a busca resolveu numa gaveta que sobe do rodapé, no contexto da tela do
mapa, para consultar a entidade territorial sem perder de vista a geometria dela.

## 2 · Condições de pronto
- [ ] Aberta, a gaveta ocupa a **largura inteira** da tela e **no máximo metade da altura** — a
      outra metade continua mapa visível e clicável.
- [ ] Abaixo de 768px a gaveta ocupa a **tela inteira**.
- [ ] O conteúdo se distribui em **até três colunas** lado a lado; abaixo de 768px elas empilham, na
      ordem em que estão escritas.
- [ ] Uma coluna que recebe a `.table-onsen` a mostra dentro da gaveta: quem rola é a tabela, e a
      gaveta não cresce nem transborda a viewport.
- [ ] Abrir e fechar **não usa JavaScript**: o gesto é um controle nativo e a placa desliza de baixo
      para cima.
- [ ] Cabeçalho e alça ficam parados enquanto o conteúdo das colunas rola.
- [ ] Gaveta sem informação a mostrar exibe o **estado de falta escrito**, não uma placa em branco.
- [ ] Nenhum poço, tabela ou placa dentro da gaveta se repinta — a pintura continua sendo uma por
      pilha.
- [ ] Design aprovado no mock e peças portadas para `static/src/tema-dimap.dev.css` e para
      `/design_system` antes de qualquer template da aplicação usar as classes.

## 3 · Domínio
Não há domínio novo. Esta SPEC entrega a **casca**: o material, a geometria e a coreografia da
gaveta que sobe do rodapé, com as colunas e os assentos em que o conteúdo será posto. Quem escolhe o
conteúdo — informações da ontologia e ações liberadas para o perfil (§3.5 do CLAUDE.md) — é o router
de gaveta, e a pergunta que esta SPEC faz a ele é nenhuma: a casca recebe de uma a três colunas de
marcação e não sabe de que entidade elas vieram.

**Mock:** [014-mock-gaveta-inferior.html](014-mock-gaveta-inferior.html) — leia a skill `mock`.

## 4 · Fora de escopo
- O conteúdo da gaveta por tipo de entidade territorial, e quais ações aparecem nela — SPEC do
  router de gaveta.
- Arrastar a alça para redimensionar ou fechar a gaveta — sem dono ainda.
- Ligar a `.cinematic-blur-layer` ao abrir: a gaveta inferior convive com o mapa em vez de
  substituí-lo, e desfocar meia tela de mapa que continua clicável não é foco, é véu — sem dono
  ainda.

## 5 · Peças de referência a compor
- `@static/src/tema-dimap.dev.css` → `.glass-drawer-panel`: a receita da gaveta lateral, que a
  inferior espelha girada.
- `@static/src/tema-dimap.dev.css` → `.card-well`, `--sombra-poco`, `--radius-placa`: poço, degrau e
  raio da placa assentada.
- `@static/src/tema-dimap.dev.css` → `.table-onsen`, `.table-onsen-poco`, `.table-onsen-wrap`: a
  tabela de vidro que a gaveta hospeda.
- `@static/src/tema-dimap.dev.css` → `.etched-line` / `.etched-line-inked`: o material do fio
  gravado, que a alça compõe.
- `@static/src/tema-dimap.dev.css` → `.stats-onsen`, `.text-overline`, `.valor-leitura`,
  `.badge-ponto`/`.badge-linha`/`.badge-poligono`: indicadores, rótulos e tipo de geometria.
- `@static/src/js/ui/scroll_etched.js` → a barra de rolagem gravada, para a coluna e a tabela que
  rolam.
- Skills: `mock`, `componentes-frontend`, `daisyui`.

## 6 · Snippets

Tudo desta SPEC é CSS, e mora na fonte única. Os comentários abaixo são didáticos — no porte vale o
§7.2 do CLAUDE.md.

**`static/src/tema-dimap.dev.css`**
```css
/* ==================== 1 · TOKEN ==================== */

/* A mesma receita da gaveta lateral, girada 90°. Placa própria, e não modificador da lateral,
   porque o que muda no material é a DIREÇÃO: a aresta de luz, a queda do gradiente e a sombra
   projetada apontam todas para cima. */
.glass-drawer-bottom {
  @apply backdrop-blur-[12px] bg-gradient-to-b from-white/80 via-white/65 to-white/55;
  @apply border-t border-white/60;
  @apply shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_-12px_40px_rgba(7,58,84,0.3),0_0_40px_rgba(72,202,228,0.25)];
}

/* Vidro sobre vidro (SPEC design/009) alcança a placa nova: sem isto o poço e a tabela dentro da
   gaveta voltam a se pintar e a pilha chega ao papel. Vai no FIM do arquivo, depois de toda peça
   cuja tinta ela apaga — que é a mesma razão da posição da regra original. */
:where(.glass-drawer-bottom) .glass-panel:where(:not(.modal-box-glass)) { @apply bg-none; }
:where(.glass-drawer-bottom) :is(.card-well, .upload-well) { @apply bg-transparent; }
:where(.glass-drawer-bottom) .upload-well:where(:hover, :focus-within) { @apply bg-white/15; }

/* ==================== 2 · ÁTOMO ==================== */

/* Alça: a afordância de "isto se fecha", gravada no gelo. A área de toque é a faixa inteira porque
   o fio tem 6px de altura e ninguém acerta 6px com o dedo. */
.gaveta-alca { @apply w-full h-6 shrink-0 flex items-center justify-center cursor-pointer; }
.gaveta-alca .etched-line { @apply w-16 h-1.5 transition-all duration-300; }
/* O sulco enche de água sob o ponteiro, dito pelo CONTÊINER como na .lata-concessao: quem carrega
   a afordância é a alça, não o fio. */
.gaveta-alca:hover .etched-line,
.gaveta-alca:focus-visible .etched-line {
  @apply w-20;
  background-color: rgba(0, 119, 182, 0.5);
  filter: drop-shadow(0 0 6px rgba(72, 202, 228, 0.6));
}
.gaveta-alca:focus-visible { @apply outline-none; }

/* ==================== 3 · MOLÉCULAS ==================== */

/* Cabeçalho: fica parado enquanto as colunas rolam. A divisa é o par sombra-luz da linha da tabela
   — sozinha, a aresta branca não separa sobre gelo claro. */
.gaveta-cabecalho {
  @apply shrink-0 flex items-start justify-between gap-4 px-5 sm:px-8 pb-3 border-b border-white/65;
  box-shadow: inset 0 -2px 0 -1px rgba(7, 58, 84, 0.09);
}

/* Corpo: faixa única que NÃO rola em tela ampla — quem rola é a coluna. Empilhado, o eixo inverte e
   quem rola passa a ser o corpo, porque duas barras aninhadas num telefone disputam o mesmo gesto. */
.gaveta-corpo { @apply flex-1 min-h-0 flex flex-col overflow-y-auto overscroll-contain; }

/* Colunas em flex-1, e não em grid de três: o número de colunas é o que a gaveta recebe. Uma
   coluna ocupa a faixa inteira, três dividem em terços, sem modificador para cada caso. */
.gaveta-coluna { @apply min-h-0 flex flex-col gap-3 px-5 sm:px-8 py-4; }
/* Fio entre colunas: a mesma divisa do cabeçalho, deitada de lado. */
.gaveta-coluna + .gaveta-coluna {
  @apply border-t border-white/65;
  box-shadow: inset 0 2px 0 -1px rgba(7, 58, 84, 0.09);
}
@media (width >= 48rem) {
  .gaveta-corpo  { @apply flex-row overflow-hidden; }
  .gaveta-coluna { @apply flex-1 basis-0 overflow-y-auto overscroll-contain; }
  .gaveta-coluna + .gaveta-coluna {
    @apply border-t-0 border-l border-white/65;
    box-shadow: inset 2px 0 0 -1px rgba(7, 58, 84, 0.09);
  }
}
/* Coluna que hospeda a tabela não rola: quem rola é o poço dela, com a barra gravada. */
.gaveta-coluna:has(.table-onsen-poco) { @apply overflow-hidden; }

/* A tabela dentro da gaveta é limitada pela GAVETA, não pelas 32rem do rolador padrão: numa faixa
   de meia tela o teto fixo transborda a placa inteira. Em flex, e não em altura percentual:
   o poço tem folga própria e a porcentagem resolveria contra uma caixa que ainda não tem medida. */
.tabela-onsen-gaveta { @apply flex-1 min-h-0 max-h-none; }

/* Figura assentada: imagem em placa dentro de poço, no assento da .tarja-vinculo, e cedendo ao
   gelo como a imagem do .avatar-glass — crua, ela briga com o material em volta. */
.gaveta-figura {
  @apply overflow-hidden bg-white/25 border border-white/45;
  border-radius: var(--radius-placa);
  box-shadow: var(--sombra-poco);
}
.gaveta-figura > img { @apply w-full h-full object-cover opacity-[0.92]; }

/* Estado de falta: gaveta sem nada a mostrar é frase escrita — placa em branco se lê como "ainda
   não carregou". */
.gaveta-vazia {
  @apply flex-1 min-h-0 flex flex-col items-center justify-center gap-3;
  @apply px-8 py-6 text-center text-sm text-base-content/60;
}

/* ==================== 4 · ORGANISMO ==================== */

/* Metade da altura é TETO, não medida: a gaveta cresce com o conteúdo até ali. */
.gaveta-inferior {
  @apply fixed inset-x-0 bottom-0 z-30 flex flex-col pt-1.5 rounded-t-3xl max-h-[50dvh];
  @apply translate-y-full transition-transform duration-500 ease-in-out;
}
/* Fechada, ela está fora da tela. O gesto é um checkbox nativo, como o modal do sistema — nenhum
   estado de UI em JavaScript. Irmão IMEDIATO, e não :root:has() nem `~`: assim duas gavetas
   convivem no mesmo documento sem que marcar uma abra a outra. */
.gaveta-toggle { @apply sr-only; }
.gaveta-toggle:checked + .gaveta-inferior { @apply translate-y-0; }

/* Abaixo do tablet a gaveta é a tela: metade de 700px não comporta cabeçalho e conteúdo. Sem
   raio no topo — folha que cobre tudo e ainda arredonda a quina deixa dois furos de mapa no ponto
   mais alto da leitura. */
@media (width < 48rem) {
  .gaveta-inferior { @apply h-[100dvh] max-h-none rounded-t-none; }
}
```

Composição no markup — material e geometria empilhados, como `.card-well.table-onsen-poco`:

```html
<input type="checkbox" id="gaveta-lote" class="gaveta-toggle" />
<aside class="glass-drawer-bottom gaveta-inferior" role="dialog" aria-label="Lote">
  <label for="gaveta-lote" class="gaveta-alca" aria-label="Fechar"><span class="etched-line"></span></label>
  <header class="gaveta-cabecalho">…</header>
  <div class="gaveta-corpo">
    <section class="gaveta-coluna">…</section>
    <section class="gaveta-coluna">…</section>
    <section class="gaveta-coluna">…</section>
  </div>
</aside>
```

## 7 · Caveats

A regra de descendência do vidro sobre vidro (SPEC design/009) passa a existir em dois lugares: a
lista original e a cópia escopada em `.glass-drawer-bottom`. Estender a lista de `:where()` da
regra original seria tocar uma peça implementada, e a cópia é aditiva. O custo é que uma peça nova
que entre naquela lista amanhã pode não entrar nesta, e o poço dentro da gaveta volta a se pintar
sem erro nenhum.

A gaveta aberta não desfoca o mapa, contra a coreografia de foco do §7 do design system. Ela ocupa
meia tela e a outra metade segue sendo mapa clicável — desfocar interface que
continua em uso não é foco. O custo é que a gaveta inferior e o modal deixam de responder ao mesmo
vocabulário de profundidade.

O teto de `50dvh` é medida de tela, não de conteúdo: numa janela baixa cabem três linhas de tabela.
A alternativa — altura mínima em `rem` — quebraria a promessa da metade livre justamente na
tela em que ela mais importa. O custo é que a coluna com tabela pode abrir mostrando pouco mais que
o cabeçalho dela.

Esta SPEC não traz teste automatizado, contra o §9 do CLAUDE.md. O que ela entrega é material e
geometria, sem regra de domínio nem contrato HTTP a fixar, e o projeto não tem stack de teste de
navegador. O custo é que uma regressão na casca só aparece em uso, e o gate de `testes_tdd` fica
levantado aqui por decisão explícita.

## 8 · Testes (TDD)
_Sem teste automatizado._ O que aprova esta SPEC é o mock do §3, percorrido nos estados que ele
mostra — ver o caveat do §7.
