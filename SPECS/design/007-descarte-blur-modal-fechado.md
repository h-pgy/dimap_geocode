---
spec: design/007
versao: v2
atualizado_em: 2026-08-31
testes_tdd: true
implementado: true
markers_obrigatorios: []
changelog:
  - v1: versão inicial
  - v2: o modal aberto mantém o desfoque de fundo, e a moldura fixa do topo cede o lugar a ele
---

# SPEC design/007 — O desfoque do modal e a moldura fixa

## 1 · User story
O servidor da DIMAP abre um ato administrativo em modal no contexto do painel e das telas de gestão para obter a tela inteira dedicada ao ato, com o que ficou atrás dissolvido e sem resíduo de desfoque ao fechar.

## 2 · Condições de pronto
- [x] Com o modal aberto, tudo que está atrás dele aparece desfocado — o conteúdo da página, o fundo à deriva e as placas de vidro.
- [x] Um modal cujo `.modal-toggle` é irmão marcado conta como aberto: é o padrão de todos os modais do projeto, e ele mantém o desfoque de fundo e o da própria caixa.
- [x] Com o modal fechado, nem ele nem seus descendentes mantêm `backdrop-filter` ativo, e a tela não exibe retângulos ou manchas de desfoque sobre a placa administrativa ou sobre o mapa.
- [x] Com um modal aberto, o chip da marca e o widget da área do usuário somem da tela e deixam de receber ponteiro; ao fechar o modal, os dois voltam.
- [x] Em nenhum momento da abertura ou do fechamento a foto de perfil do widget aparece como mancha da cor da unidade.
- [x] Fora o desfoque do modal e a saída da moldura, nada muda de aparência: nenhuma cor, medida, posição ou tempo de peça existente é alterado, e nenhuma classe sai do markup.
- [x] O design foi aprovado no mock e as peças foram portadas para o tema e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
Iteração de design system e folha de estilos: nenhum model, nenhuma migração, nenhum DTO. A pergunta que esta SPEC faz às peças existentes:

- `.modal-glass` e `.modal-box-glass` ([`SPEC user_admin/012`](../user_admin/012-design-formulario-unidade.md), [`SPEC design/008`](008-opacidade-gelo-espesso.md)): "quando o modal está fechado, os dois retêm filtro de desfoque?"; sim — o daisyUI 5 oculta `.modal` com `visibility: hidden` e `opacity: 0`, e os nós com `backdrop-filter` seguem no layout, retendo textura na GPU.
- As mesmas duas peças, na outra ponta: "o que conta como modal aberto?"; as quatro portas são `.modal-open`, `[open]`, um `.modal-toggle:checked` descendente e um `.modal-toggle:checked` **irmão imediato** — e é por esta última que os vinte modais do projeto abrem.
- `.glass-hide-up` e `.transition-glass`: "existe peça para uma placa ceder o lugar quando outra entra em cena?"; sim, e é ela que a moldura fixa passa a usar quando há modal aberto.
- Chip da marca e `#widget-area-usuario` de `base.html`: "há como alcançar as duas placas fixas do topo por seletor?"; não — nesta SPEC as duas recebem `.moldura-fixa`, que é só o nome por onde a coreografia as alcança e não declara pele, medida nem posição.

**Mock:** [007-mock-descarte-blur-modal-fechado.html](007-mock-descarte-blur-modal-fechado.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Substituição do daisyUI ou refatoração dos diálogos para a tag nativa `<dialog>` — sem dono ainda.
- Retirada do foco por teclado (Tab) da moldura escondida — sem dono ainda.
- Uso da `.cinematic-blur-layer` como camada de foco do modal, no lugar do `backdrop-filter` da própria peça — sem dono ainda.

## 5 · Peças de referência a compor
- `@static/src/tema-dimap.dev.css` → `.glass-hide-up`: como uma peça cede o lugar quando outra entra em cena.
- `@static/src/tema-dimap.dev.css` → `.transition-glass`: o tempo do material, 500ms.
- `@static/src/tema-dimap.dev.css` → `.modal-glass`, `.modal-box-glass`: o material do modal e da caixa dele.
- `@templates/base.html` → chip da marca e `#widget-area-usuario`: as duas placas fixas do topo.
- Skills: `componentes-frontend`, `mock`, `daisyui`.

## 6 · Snippets

**`static/src/tema-dimap.dev.css`** — bloco do modal, no lugar da regra de neutralização atual

```css
/* Modal fechado é o que não está aberto por NENHUMA das quatro portas. A quarta — toggle irmão
   marcado — é como todo modal do projeto abre, e sem ela a neutralização casava também com o modal
   aberto: `:has()` procura o toggle DENTRO do .modal, e ele é irmão. */
.modal:not(.modal-open, [open], :has(.modal-toggle:checked), .modal-toggle:checked + *),
.modal:not(.modal-open, [open], :has(.modal-toggle:checked), .modal-toggle:checked + *) * {
  backdrop-filter: none !important;
}
```

**`static/src/tema-dimap.dev.css`** — bloco COREOGRAFIA

```css
/* A moldura fixa entra pela MESMA regra do .glass-hide-up: segundo caminho de entrada na peça, não
   uma cópia dela. O estado é lido do documento com :has(), como toda coreografia do tema. */
.glass-hide-up,
:root:has(.modal-toggle:checked) .moldura-fixa {
  @apply opacity-0 -translate-y-5 scale-95 pointer-events-none;
}
```

**`templates/base.html`** — as duas âncoras ganham `moldura-fixa`; nenhuma classe sai

```html
<a href="{% url 'core:home' %}"
   class="moldura-fixa fixed top-6 left-4 lg:left-6 z-20 glass-panel rounded-full! ...">

<a id="widget-area-usuario" href="{% url 'painel:painel' %}"
   class="moldura-fixa fixed top-6 right-4 lg:right-6 z-20 glass-panel rounded-full! ...">
```

## 7 · Caveats
O `!important` da neutralização permanece. Ele é a exceção pré-aprovada do CLAUDE.md §3.4 — reset de GPU sobre utility do daisyUI, que de outro modo venceria a regra do tema. Custo: nenhuma utility no markup consegue devolver o desfoque a um modal fechado.

A regra do `.glass-hide-up` ganha um segundo seletor em vez de a moldura fixa receber a classe no markup. A peça não muda de comportamento — mudam as portas de entrada dela —, mas a linha de um átomo já implementado é editada, e é isso que esta SPEC pede aval para fazer (CLAUDE.md §3.4). Custo: quem ler o átomo passa a ter de ler duas condições para saber quando ele vale.

O gatilho é `:root:has(.modal-toggle:checked)`, global ao documento. Qualquer toggle marcado esconde a moldura, não só o do modal em cena. Custo: uma tela que deixe um `.modal-toggle` marcado sem modal visível esconde a marca e o widget sem que haja modal algum.

A moldura escondida continua alcançável por Tab, porque `.glass-hide-up` esconde por opacidade e ponteiro, não por `visibility`. Custo: com o modal aberto, a tabulação ainda passa pela marca e pelo widget antes de chegar ao formulário.

**A SPEC não carrega teste automatizado.** O entregável é regra declarativa de CSS do design system, sem regra de negócio em `services/`, model ou contrato de DTO, e o que ela fixa — desfoque composto pela GPU — só se observa no navegador. Custo: a validação é visual, no mock e no smoke da tela.

## 8 · Testes (TDD)
Nenhum teste automatizado — ver Caveats.
