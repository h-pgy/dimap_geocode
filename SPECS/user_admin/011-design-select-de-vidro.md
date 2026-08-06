---
spec: user_admin/011
versao: v2
atualizado_em: 2026-08-06
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: realce do item vira estado do componente (data-ativo), movido por mouse e seta, em tinta de água; teclado num ouvinte único na casca; explicitada a migração dos três selects do formulário de servidor, hoje nativos em criar e editar
---

# SPEC user_admin/011 — Campo de seleção de vidro e a segunda espessura do gelo

- [ ] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como usuário das telas administrativas, quero que a lista que um campo de seleção abre pertença ao
design system — e não seja a caixa branca quadrada do sistema operacional —, para que escolher unidade
ou cargo pareça parte do produto e não um remendo do navegador.

## Critérios de aceite

- [ ] O vidro passa a ter **duas espessuras**, escolhidas pelo que está atrás: a fina de hoje sobre o
      mapa e uma **espessa** (blur maior, gelo mais leitoso) para vidro sobre interface. Não é
      material novo — é a mesma receita em outro grau, com os primitivos correspondentes.
- [ ] Existe o **campo de seleção de vidro**: gatilho de vidro (como hoje) e **lista dentro do design
      system** — gelo espesso, cantos arredondados, **um único realce** que mouse e seta movem em
      conjunto, escolha atual marcada em água, e **filtro por texto** quando o catálogo é grande.
- [ ] O `<select>` **continua sendo o campo**: renderizado pelo servidor com suas `<option>`, é nele
      que o valor escolhido é escrito e é dele que sai um evento `change` nativo — quem escuta
      `change` (HTMX, hoje ou depois) não precisa saber que existe casca.
- [ ] A lista aberta **nunca é cortada pelo container nem coberta por outro elemento** — dentro de
      painel de vidro, de caixa com rolagem ou de modal —, acompanha o gatilho quando a página rola e
      **abre para cima** quando não há altura confortável abaixo.
- [ ] Funciona pelo **teclado**: abre pelo gatilho ou pelas setas, as setas movem o realce pela lista
      (dando a volta nas pontas), `Enter` escolhe o realçado **sem submeter o formulário**, `Esc` e
      clique fora fecham — e digitar no filtro continua funcionando depois de andar com as setas.
- [ ] Os três campos de seleção do formulário de servidor — **unidade, cargo base e cargo em
      comissão** — deixam de abrir a lista do sistema operacional e passam a usar o componente. Hoje
      **nenhum deles o usa**: são `<select>` nativos e a página não carrega utilitário de UI algum, de
      modo que a entrega inclui marcar os campos **e** carregar o módulo na página. Como criar e
      editar servidor são a mesma tela renderizada com e sem perfil, as duas passam a usá-lo na mesma
      mudança — nenhuma tela nova nesta iteração.
- [ ] O design foi **aprovado no mock** que acompanha esta SPEC antes de qualquer código de
      aplicação.
- [ ] Aprovado o mock, as peças novas estão nos **dois destinos obrigatórios** — tokens em
      `static/src/tema-dimap.dev.css` (fonte única) e componentes renderizados no styleguide
      `.claude/skills/componentes-frontend/examples/design_system.html` —, o utilitário mora em
      `static/src/js/ui/`, e **os templates da aplicação usam as classes**, sem utilities soltas
      resolvendo pele.

## Contexto e decisões de arquitetura

Iteração de **interface**, e só de interface: tokens, um utilitário de UI e o marcador nos `<select>`
que já existem. Nenhum model, nenhuma view, nenhuma rota.

**A espessura do gelo depende do que está atrás.** O vidro fino de 10px foi calibrado contra a água
clara do mapa; sobre interface — formulário com tinta escura, selects, poços — ele deixa passar demais
e a leitura sofre. Entra um segundo grau (blur 20px, gelo mais leitoso, sombra mais funda) na mesma
receita. A regra que fica: *fino sobre o mapa, espesso sobre interface*. A lista deste componente é o
primeiro consumidor.

**A lista nativa não é estilizável, e o caminho sem JavaScript só serve a um navegador.**
`appearance: base-select` + `::picker(select)` dariam a pele sem uma linha de script, mas só em
Chromium — foi tentado e reprovado no mock. O caminho aprovado **aprimora o `<select>` renderizado
pelo servidor**: o elemento nativo permanece no DOM como o campo do formulário, e o JavaScript
constrói gatilho e lista de vidro, filtra por texto e, na escolha, escreve `selectedIndex` e dispara
`change`.

**Este é um caso autorizado de JavaScript além do §7.2.** A restrição existe para impedir regra de
negócio e estado de aplicação no navegador; aqui não há nem um nem outro — o valor mora no `<select>`,
o catálogo vem do servidor, a validação é do POST, e o que o JavaScript faz é pele, geometria e
teclado, exatamente como os utilitários do Leaflet. O módulo segue o padrão do JS do mapa: funções
puras e registro único de callback do HTMX, idempotente para conteúdo trocado por swap (o `<select>`
já aprimorado fica `hidden`, e é isso que impede casca duplicada).

**O realce do item é estado do componente, não foco do navegador.** Desenhar o item sob o cursor com
`:focus-visible` não funciona: o navegador não acende `:focus-visible` em foco programático depois de
um clique, e a seta andava sem que a tela mudasse. Quem anda é um marcador próprio (`data-ativo`) que
mouse e teclado movem em conjunto — realce é **um só** —, enquanto o foco permanece no campo de filtro,
para que navegar e continuar digitando não disputem. Pelo mesmo motivo o realce é tinta de água e não
branco: sobre gelo espesso, branco sobre branco não se lê. E a marca da escolha (✓ em água) fica
separada do realce, senão o item selecionado parece estar sob o cursor.

**A lista abre na top layer, não dentro do container.** Como popover ela sai do fluxo e de qualquer
contexto de empilhamento: painel absoluto era cortado pelo `overflow` da casca administrativa e ficava
atrás de irmãos por causa do contexto que todo `backdrop-filter` cria — sintoma que o mock mostrou, e
que `z-index` não resolve. A troca: quem posiciona é o JavaScript, a partir do retângulo do gatilho,
reposicionando enquanto a lista está aberta. Em compensação, `popover=auto` dá `Esc` e clique-fora de
graça.

**O componente nasce aplicado.** Registrá-lo no styleguide e deixar a aplicação com a lista do sistema
operacional seria entregar metade: os três campos de seleção da tela de servidor já existem e passam a
usá-lo nesta mesma entrega, o que também é o que torna a iteração verificável no `runserver`. São duas
mudanças no template: o marcador nos `<select>` da seção de lotação e o módulo carregado no bloco de
scripts da página do formulário, ao lado do fundo administrativo — mesmo lugar, mesmo padrão.

## Mock de validação

`SPECS/user_admin/011-mock-select-de-vidro.html` — a SPEC só é aprovável com ele: lista de vidro
descrita em prosa não é validável. O mock roda o fundo administrativo à deriva, declara os tokens
propostos num `script[type="text/css"]` inerte que o loader concatena ao tema **no mesmo bloco**
`text/tailwindcss`, e traz o utilitário funcionando de verdade. Exige servidor com root na raiz do
projeto (Live Server).

Está organizado em Atomic Design (tokens → átomos → moléculas → organismos) e mostra os estados que
importam: gelo fino × espesso sobre cor forte, os quatro estados do item (repouso, escolhido, sob o
cursor, e as duas coisas juntas), lista fechada × aberta, catálogo pequeno (sem filtro) ×
grande (com filtro), lista vazia depois do filtro, e os três casos que quebravam — dentro de painel de
vidro, dentro de caixa com rolagem e junto ao rodapé, abrindo para cima. O JS do mock é o módulo que
vai para `static/src/js/ui/`, inline apenas porque o mock não passa pelo Django.

## Peças de referência a compor

- `@static/src/tema-dimap.dev.css` → os primitivos de vidro (`.glass-blur`, `.glass-bg`,
  `.glass-edge`, `.glass-shadow`) e `.select-glass`, `.input-glass`, `.form-field`: a espessura nova
  entra como grau desse vocabulário e o gatilho continua sendo o `.select-glass` de hoje.
- `templates/user_admin/partials/_secao_lotacao.html` → os três campos de seleção que passam a usar o
  componente, hoje `<select>` nativos.
- `templates/user_admin/perfil_form.html` → a tela única de criar e editar servidor, e o
  `{% block scripts %}` por onde o módulo entra, ao lado do fundo administrativo.
- `@static/src/js/mapa/init.js` → o padrão de JS do projeto: módulo ES de funções puras e registro
  único de callback do HTMX.
- `@.claude/skills/componentes-frontend/examples/design_system.html` → styleguide onde a peça se
  registra (seções de tokens e de moléculas).

## Snippets sugeridos

```css
/* tema-dimap.dev.css — tokens novos. @apply só de utilities; important é sufixo no Tailwind 4. */

/* Material: gelo espesso — para vidro sobre interface, onde o fino de 10px deixa passar demais. */
.glass-blur-thick { @apply backdrop-blur-[20px]; }
.glass-bg-thick   { @apply bg-gradient-to-br from-white/85 via-white/75 to-white/65; }
.glass-panel-thick {
  @apply rounded-2xl backdrop-blur-[20px] bg-gradient-to-br from-white/85 via-white/75 to-white/65 border border-white/70 shadow-[inset_0_1px_0_rgba(255,255,255,0.9),0_12px_40px_rgba(7,58,84,0.3),0_0_28px_rgba(72,202,228,0.28)];
}

/* Molécula: campo de seleção de vidro — a casca que o JS monta em volta do <select> do servidor. */
.select-onsen { @apply w-full; }
/* flex! porque o .select do daisyUI define o próprio display e as duas regras empatam. */
.select-onsen-trigger { @apply flex! w-full items-center justify-between text-left font-normal; }
/* Popover: a lista vive na top layer, então nenhum overflow a corta e nenhum contexto de
   empilhamento a soterra. O inset: auto derruba o inset: 0 que o navegador dá a todo popover;
   posição, largura e altura máxima vêm do gatilho, escritas pelo JS. */
.select-onsen-panel {
  @apply fixed m-0 p-2 overflow-hidden rounded-2xl backdrop-blur-[20px] bg-transparent bg-gradient-to-br from-white/85 via-white/75 to-white/65 border border-white/70 text-base-content shadow-[inset_0_1px_0_rgba(255,255,255,0.9),0_12px_40px_rgba(7,58,84,0.3),0_0_28px_rgba(72,202,228,0.28)];
  inset: auto;
}
.select-onsen-panel:popover-open { @apply flex flex-col gap-2; }
.select-onsen-busca { @apply h-9 text-sm shrink-0; }
.select-onsen-list  { @apply flex flex-col gap-1 min-h-0 max-h-60 overflow-y-auto overscroll-contain; }
.select-onsen-option {
  @apply flex items-center gap-2 w-full text-left px-3 py-2 rounded-xl text-sm cursor-pointer transition-all duration-200 text-base-content;
}
/* A marca da escolha é tinta de água. A coluna existe em todo item: sem ela o rótulo dança de linha
   para linha. */
.select-onsen-option::before {
  @apply w-4 shrink-0 text-center text-agua-700 font-bold opacity-0;
  content: "✓";
}
.select-onsen-option[aria-selected="true"] { @apply font-medium text-agua-800; }
.select-onsen-option[aria-selected="true"]::before { @apply opacity-100; }
/* Realce do cursor: um só marcador, movido pelo hover E pela seta — não :focus-visible, que não
   acende em foco programático, e não branco, que sobre gelo espesso não se lê. */
.select-onsen-option[data-ativo="true"] {
  @apply bg-agua-400/45 text-rocha-950 outline-none shadow-[inset_0_0_0_1px_rgba(0,150,199,0.5),0_2px_10px_rgba(0,150,199,0.25)];
}
.select-onsen-vazio { @apply px-3 py-2 text-xs text-base-content/60; }
```

```html
<!-- _secao_lotacao.html — o campo continua sendo o select: o componente é opt-in por atributo. -->
<label class="form-field">
  <span class="text-overline">Unidade</span>
  <select name="unidade" class="select select-glass" data-select-onsen>
    {% for unidade in unidades %}
      <option value="{{ unidade.pk }}" {% if unidade.pk == perfil.unidade_id %}selected{% endif %}>{{ unidade.sigla }} · {{ unidade.nome }}</option>
    {% endfor %}
  </select>
</label>
```

```html
{# perfil_form.html — sem isto os selects seguem nativos: marcar o campo não carrega o módulo. #}
{% block scripts %}
  <script type="module" src="{% static 'js/mapa/fundo_admin.js' %}"></script>
  <script type="module" src="{% static 'js/ui/select_onsen.js' %}"></script>
{% endblock %}
```

```js
// static/src/js/ui/select_onsen.js — pele, geometria e teclado, nada mais. Versão completa no mock.

// Escolher é escrever no campo de verdade: o `change` nativo é o que mantém HTMX e POST alheios
// à existência da casca.
function escolher(select, indice, rotulo, itens) {
  select.selectedIndex = indice;
  rotulo.textContent = select.options[indice].textContent;
  itens.forEach((item, i) => item.setAttribute("aria-selected", String(i === indice)));
  select.dispatchEvent(new Event("change", { bubbles: true }));
}

// O realce é estado do componente: seta e mouse movem o MESMO marcador, e o foco fica no filtro.
function realcar(item) {
  ativo?.removeAttribute("data-ativo");
  ativo = item ?? null;
  if (!ativo) return focado().removeAttribute("aria-activedescendant");
  ativo.setAttribute("data-ativo", "true");
  ativo.scrollIntoView({ block: "nearest" });
  focado().setAttribute("aria-activedescendant", ativo.id);
}

// Um ouvinte só: o painel é popover (top layer), mas continua filho da casca no DOM, então o evento
// sobe até aqui venha ele do gatilho ou do campo de filtro.
casca.addEventListener("keydown", (evento) => {
  if (!painel.matches(":popover-open")) { /* seta abre a lista */ }
  if (Object.hasOwn(PASSO_DA_SETA, evento.key)) { /* anda o realce, dando a volta nas pontas */ }
  // Sem o preventDefault do Enter, o filtro submeteria o formulário (submissão implícita) e o
  // gatilho reabriria a lista pelo clique sintético do invoker.
});

// A lista está na top layer: quem diz onde ela fica é o gatilho. Abre para cima quando não há
// altura confortável abaixo.
function posicionar(painel, trigger) {
  const caixa = trigger.getBoundingClientRect();
  const abaixo = window.innerHeight - caixa.bottom - FOLGA_PX;
  const acima = caixa.top - FOLGA_PX;
  const paraCima = abaixo < ALTURA_CONFORTAVEL_PX && acima > abaixo;
  painel.style.left = `${caixa.left}px`;
  painel.style.width = `${caixa.width}px`;
  painel.style.maxHeight = `${paraCima ? acima : abaixo}px`;
  painel.style.top = paraCima ? "" : `${caixa.bottom + FOLGA_PX}px`;
  painel.style.bottom = paraCima ? `${window.innerHeight - caixa.top + FOLGA_PX}px` : "";
}

// O [hidden] marca o que já foi aprimorado: swap de HTMX reexecuta isto sem duplicar casca.
export function aprimorarSelects() {
  document.querySelectorAll("select[data-select-onsen]:not([hidden])").forEach(aprimorar);
}
```

## Fora de escopo

- Seleção múltipla, criação de opção pela própria lista ("digitou e não achou, cria") e busca no
  servidor: o catálogo já vem inteiro no HTML, e criar unidade é assunto da SPEC seguinte.
- Aplicar o componente fora das telas administrativas de servidor.
- Reapresentar as demais peças de vidro do sistema (painéis, gaveta, sugestões) na espessura nova — o
  espesso nasce aqui só onde há interface atrás.
- Teste automatizado do comportamento de navegador (abrir, filtrar, teclado): não há infraestrutura
  de teste de JavaScript no projeto, e criá-la é decisão de outra SPEC.

## Testes (TDD)

O entregável é pele e comportamento de navegador — o que se valida no mock e no smoke test da página
(skill `test-django-views`). Os dois testes abaixo fixam o que **pode** regredir sem ninguém ver: o
contrato de que o servidor continua entregando um `<select>` de verdade, marcado para o componente, com
o módulo carregado. Ambos tocam o banco (a página monta os selects a partir das tabelas) e levam o
marker `banco`, declarado no front-matter.

- `test_selects_da_lotacao_usam_o_componente_de_vidro` — a página de criar servidor entrega os três
  campos como `<select ... data-select-onsen>` com suas `<option>`, e carrega o módulo do componente.
- `test_select_de_unidade_mantem_a_opcao_selecionada_na_edicao` — na edição, a `<option>` da unidade do
  servidor vem `selected`: é dela que a casca lê o rótulo inicial.

## Patches

_Nenhum patch registrado até o momento._
