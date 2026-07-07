---
spec: design/002
versao: v2
atualizado_em: 2026-07-06
implementado: true
changelog:
  - v1: versão inicial
  - v2: patch 001 — duração da lista pós-commit de 900ms para 1500ms (sumia rápido demais
        no Enter rápido)
---

# SPEC design/002 — Feedback visual do Enter: lista de sugestões + animação de seleção

- [x] **Implementada**

## User story
Como usuário da busca, quero que, ao pressionar Enter, eu **veja** qual sugestão foi acionada —
a lista de sugestões aparece (mesmo que eu tenha dado Enter rápido demais), o item escolhido é
destacado com uma animação e a lista some sozinha depois de um instante — para entender o que o
sistema buscou em meu nome, em qualquer tipo de busca (logradouro, endereço, codlog, lote).

## Critérios de aceite
- [ ] Enter com a lista de sugestões **já visível**: o primeiro item da primeira seção recebe
      uma animação de seleção; a lista permanece visível por um intervalo curto fixo e então
      desaparece suavemente (fade), deixando o resultado no mapa em foco.
- [ ] Enter **rápido** (antes de a lista ter aparecido): a busca comita imediatamente (sem
      atraso artificial na requisição), e quando a resposta das sugestões chegar a lista ainda
      aparece, com a mesma animação de seleção no primeiro item, e some sozinha após o mesmo
      intervalo.
- [ ] O comportamento vale para **todos os tipos** de busca da barra única (todas as seções).
- [ ] Digitar novamente após o Enter cancela o estado "pós-commit": a lista volta ao
      comportamento normal de sugestões (sem fade automático nem animação residual).
- [ ] Enter sem nenhuma sugestão possível (roteamento vazio/impossível) não exibe lista
      fantasma — apenas o aviso atual no resultado.
- [ ] Nenhuma regra de negócio no JS: apenas callbacks de eventos HTMX e manipulação visual
      (classes/animação), conforme CLAUDE.md §11.

## Contexto e decisões de arquitetura

Hoje o Enter dispara o `comitar` imediatamente e o único feedback é um `hx-indicator` que
acende `#sugestao-top .suggestion-item:first-child` **se a lista já estiver renderizada**. Como
o keyup tem debounce de 300ms, um Enter rápido comita antes de a lista existir — o usuário não
vê o que foi acionado. Além disso, a lista não tem dismissão pós-commit: ela fica na tela ou
aparece "atrasada" sem contexto.

Esta SPEC é **exclusivamente de frontend** (templates + CSS + JS utilitário de eventos HTMX).
Nenhuma view, domínio ou model muda. Princípios aplicados:

- **HATEOAS intacto (§3.1):** o fluxo de requisições não muda — keyup segue populando
  `#sugestoes-busca` e o Enter segue postando em `search:comitar` para `#resultado-busca`.
  O JS não consome JSON nem monta UI: só orquestra classes CSS em resposta a eventos HTMX
  (`htmx.on`), que é o uso permitido pelo §11.
- **Estado mínimo e local:** o "pós-commit" é um estado visual transitório (uma classe no
  contêiner de sugestões + um timer de dismissão). O timer usa uma constante única de
  duração (o "tempinho arbitrário") no módulo JS. Digitação nova limpa classe e timer.
- **Animação de seleção:** reaproveita/expande o mecanismo do `hx-indicator` existente — o
  destaque do primeiro item vira uma animação explícita (ex.: pulso/realce) definida no CSS
  do design system, aplicada tanto quando a lista já existe quanto quando ela chega depois
  do Enter (no evento `htmx:afterSwap` do alvo de sugestões, se o estado pós-commit estiver
  ativo).
- **Sem atraso na busca:** o commit nunca espera a lista — o requisito é feedback, não
  sincronização. A lista que chegar depois é exibida, animada e dispensada.

Aproximação aceita: o destaque é sempre o **primeiro item da primeira seção** (o melhor
palpite exibido). O `comitar` aciona o primeiro candidato que *geocodifica com sucesso*, que em
casos raros pode não corresponder exatamente a esse item — aceitável para o feedback visual;
sincronizar isso exigiria acoplar o commit à renderização das sugestões (fora de escopo).

Fluxo resumido:

```
Enter (keyup[Enter] no #input_search)
  ├─ hx-post comitar → #resultado-busca (inalterado)
  └─ JS (htmx.on): marca contêiner de sugestões como "pós-commit"
        lista visível?  → anima 1º item → aguarda DURACAO → fade-out
        lista ausente?  → quando htmx:afterSwap popular #sugestoes-busca:
                          anima 1º item → aguarda DURACAO → fade-out
Novo keyup/digitação → limpa estado pós-commit e timers (lista volta ao normal)
```

## Peças de referência a compor
- `@templates/core/home.html` → barra de busca, gatilhos HTMX do keyup e do Enter
  (`span` de commit com `hx-indicator`) e contêineres `#sugestoes-busca` / `#resultado-busca`.
- `@templates/search/partials/_sugestoes.html` → painel de sugestões e âncora `#sugestao-top`
  (1ª seção) — pontos de aplicação da animação.
- `@static/src/input.css` → design system "Onsen de Inverno" (skill `componentes-frontend`):
  classes do painel (`suggestion-panel`, `suggestion-item`) e onde nasce a animação de
  seleção e o fade-out.
- Mecanismo `hx-indicator` existente do Enter — base do destaque do 1º item, a evoluir para a
  animação explícita.
- Skill `htmx` → eventos `htmx:afterSwap` / `htmx:beforeRequest` para os callbacks permitidos.

## Snippets sugeridos

```js
// static (JS utilitário permitido pelo §11): callbacks HTMX, sem regra de negócio
const DURACAO_LISTA_POS_COMMIT_MS = 900;

htmx.on("#input_search", "keyup", (evt) => {
  if (evt.key === "Enter") marcarPosCommit();      // adiciona classe + agenda dismissão
  else limparPosCommit();                          // digitou de novo: cancela timers/classes
});

htmx.on("#sugestoes-busca", "htmx:afterSwap", () => {
  if (estaPosCommit()) animarSelecaoEDispensar();  // lista chegou depois do Enter
});
```

```css
/* input.css — direção: animação de seleção e dismissão do painel */
.suggestion-panel.pos-commit .suggestion-item:first-child { /* pulso/realce de seleção */ }
.suggestion-panel.dismissing { /* transição de opacidade/translate para o fade-out */ }
```

## Fora de escopo
- Qualquer mudança em views, domínio ou contratos — o fluxo de requisições é o atual.
- Sincronizar o item destacado com o candidato que efetivamente geocodificou no `comitar`
  (aproximação do 1º item aceita — ver Contexto).
- O fallback fuzzy e o badge de grau de certeza — SPEC roteamento_busca/013.
- Navegação por teclado nas sugestões (setas para escolher item antes do Enter) — iteração
  futura.
- Ajustes gerais de layout/estilo do painel além da animação/dismissão.

## Notas de teste
(Só quando explicitamente solicitado — CLAUDE.md §13.)
- Difícil de cobrir por teste unitário de backend (comportamento é JS/CSS); a validação é o
  smoke test manual no browser: Enter lento (lista visível), Enter rápido (lista chega
  depois), digitação após Enter, Enter sem sugestão possível.
- Se houver teste de template: presença dos hooks (`id`s/classes) que o JS consome.

## Patches

### Patch 001 (v2) — Lista pós-commit visível por mais tempo

No uso real, com Enter rápido a lista chegava e sumia cedo demais para ser lida. A constante
`DURACAO_LISTA_POS_COMMIT_MS` do módulo `busca/feedback_selecao.js` subiu de `900` para `1500`.
Nenhuma outra mudança.
