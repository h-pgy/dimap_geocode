---
spec: design/022
versao: v1
atualizado_em: 2026-10-09
testes_tdd: true
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC design/022 — Gaveta inferior puxável (`.gaveta-inferior-puxavel`)

## 1 · User story
O servidor da DIMAP puxa a alça da gaveta inferior para cima ou para baixo, no contexto de um conteúdo
que pede mais altura que a de nascença, para repartir a tela entre a gaveta e o mapa como o trabalho da
vez exigir.

## 2 · Condições de pronto
- [ ] Numa gaveta inferior **marcada como puxável**, arrastar a alça muda a altura da gaveta junto com
      o ponteiro; solta, ela fica na altura em que foi deixada.
- [ ] A altura para num **piso** e num **teto**: além deles a gaveta não acompanha o ponteiro, e no
      teto sobra uma faixa de mapa à vista e clicável. Redimensionar a janela não a tira desses limites.
- [ ] Gaveta inferior **sem a marca** não responde ao arrasto: a de "Lotes intersectados" nasce sem
      ela e se comporta como antes.
- [ ] Um **clique parado** na alça segue recolhendo a gaveta; um arrasto não a recolhe.
- [ ] A **gaveta lateral** acompanha a borda de cima da gaveta enquanto ela é puxada, sem que uma cubra
      a outra, e a **bancada de desenho** sai de baixo dela quando a alça é solta.
- [ ] Recolhida e reaberta, a gaveta volta na altura em que estava; a **próxima gaveta puxável** aberta
      na mesma página nasce nessa altura, e recarregar a página devolve a altura de nascença.
- [ ] Abaixo de 768px a gaveta ocupa a tela inteira e **não se puxa**.
- [ ] O design da alça puxável, do piso, do teto e da gaveta lateral encurtada foi aprovado no mock, e
      as peças foram portadas para o tema e o styleguide antes de qualquer template da aplicação
      usá-las.

## 3 · Domínio
Não há domínio novo. A puxável é uma **variante** da casca da [gaveta inferior](014-gaveta-inferior.md),
composta no HTML com a
[rasa](../localizacao_lote/003-lotes-do-desenho.md): a rasa dá a altura fixa, a puxável deixa o
ponteiro mudá-la. A ausência da classe é o padrão, e a pergunta que esta SPEC faz à rasa é "de que
medida a gaveta e a gaveta lateral leem a altura?".

Ao soltar a alça, a gaveta publica o evento `gaveta-inferior:puxada`; é a ele que pergunta "a altura
mudou?" quem precisa se reacomodar.

**Mock:** [022-mock-gaveta-inferior-puxavel.html](022-mock-gaveta-inferior-puxavel.html) — leia a skill
`mock`.

## 4 · Fora de escopo
- A gaveta do panorama, primeira a nascer puxável —
  [SPEC street_view/002](../street_view/002-street-view-na-gaveta-inferior.md).
- Puxar pelo teclado, com as setas sobre a alça — sem dono ainda.
- Arrastar abaixo do piso para recolher ou fechar a gaveta — sem dono ainda.
- Guardar a altura entre recargas da página ou por usuário — sem dono ainda.
- Puxar a gaveta de teto, a `.gaveta-inferior` sem a rasa — sem dono ainda.

## 5 · Peças de referência a compor
- `@static/src/tema-dimap.dev.css` → `.gaveta-inferior-rasa`, `--gaveta-rasa-altura`: a altura fixa e a regra que faz a gaveta lateral parar acima dela.
- `@static/src/tema-dimap.dev.css` → `.gaveta-alca`, `.gaveta-inferior-recolher`, `.paleta-gaveta-inferior`: a alça que recolhe e a paleta que reabre.
- `@static/src/js/mapa/desenho/bancada.js` → `acompanharGaveta`: a reacomodação da bancada quando a gaveta inferior toma o rodapé.
- `@static/src/js/ui/fechar_gaveta_clique_fora.js` → `naGavetaInferior`: o gesto que começa na gaveta inferior já poupa a lateral.
- Skills: `mock`, `componentes-frontend`, `htmx`, `escrever-testes`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`static/src/tema-dimap.dev.css`** — os valores do piso e do teto saem do mock.

```css
:root {
  --gaveta-puxavel-piso: 12rem;
  --gaveta-puxavel-teto: 75dvh;
  /* a altura de nascença: a da rasa, lida aqui para a variante que a troca ter onde escrever */
  --gaveta-puxavel-partida: var(--gaveta-rasa-altura);
}

@media (width >= 48rem) {
  /* A casca relê a medida da rasa. --gaveta-puxada-altura é escrita pelo script e não existe antes
     do primeiro arrasto: até lá vale a partida. O piso e o teto são daqui, e não do script: o dvh
     do teto se recalcula sozinho quando a janela muda. */
  .tela-home:has(.gaveta-inferior-puxavel) {
    --gaveta-rasa-altura: clamp(
      var(--gaveta-puxavel-piso),
      var(--gaveta-puxada-altura, var(--gaveta-puxavel-partida)),
      var(--gaveta-puxavel-teto)
    );
  }

  .gaveta-inferior-puxavel > .gaveta-alca { @apply cursor-ns-resize touch-none select-none; }

  /* Enquanto se puxa, a lateral acompanha sem a transição do bottom, que a deixaria para trás. */
  .tela-home[data-puxando] .gaveta-lateral { transition-property: transform; }
}
```

**`static/src/js/ui/puxar_gaveta.js`** — incluído pelo `home.html`.

```javascript
const ALCA = ".gaveta-inferior-puxavel > .gaveta-alca";
const LIMIAR_ARRASTO_PX = 6;

// `puxou` sobrevive ao pointerup: é o click que o navegador dispara em seguida que o lê.
const GESTO = { alca: null, origem: 0, folga: 0, puxou: false };

function apertar(evento) {
  GESTO.puxou = false;
  GESTO.alca = evento.target.closest?.(ALCA) ?? null;
  if (GESTO.alca === null) return;
  GESTO.origem = evento.clientY;
  // a distância do ponteiro à borda da placa se mantém: a gaveta não salta no primeiro movimento
  GESTO.folga = evento.clientY - GESTO.alca.parentElement.getBoundingClientRect().top;
  // o ponteiro continua da alça mesmo passando sobre o mapa ou o panorama
  GESTO.alca.setPointerCapture(evento.pointerId);
}

function mover(evento) {
  if (GESTO.alca === null) return;
  if (!GESTO.puxou && Math.abs(evento.clientY - GESTO.origem) < LIMIAR_ARRASTO_PX) return;
  GESTO.puxou = true;
  const casca = GESTO.alca.closest(".tela-home");
  casca.dataset.puxando = "";
  // altura absoluta, medida do rodapé da casca: nada se acumula entre um arrasto e outro
  const altura = casca.getBoundingClientRect().bottom - evento.clientY + GESTO.folga;
  casca.style.setProperty("--gaveta-puxada-altura", altura + "px");
}

function soltar() {
  const alca = GESTO.alca;
  GESTO.alca = null;
  if (alca === null || !GESTO.puxou) return;
  delete alca.closest(".tela-home").dataset.puxando;
  alca.dispatchEvent(new CustomEvent("gaveta-inferior:puxada", { bubbles: true }));
}

// A alça é o <label> do recolher: sem isto, o click que fecha o arrasto recolheria a gaveta.
function pouparRecolher(evento) {
  if (GESTO.puxou && evento.target.closest?.(ALCA)) evento.preventDefault();
}

document.addEventListener("pointerdown", apertar);
document.addEventListener("pointermove", mover);
document.addEventListener("pointerup", soltar);
document.addEventListener("pointercancel", soltar);
document.addEventListener("click", pouparRecolher, { capture: true });
```

**`static/src/js/mapa/desenho/bancada.js`** — a bancada passa a ouvir também a gaveta puxada.

```javascript
document.addEventListener("gaveta-inferior:puxada", acompanharGaveta);
```

**`templates/mapping/_resultado_acao.html`** — a base de toda resposta de ação aceita `puxavel` no
contexto; sem a chave, a gaveta nasce como hoje.

```html
<aside class="glass-drawer-bottom gaveta-inferior gaveta-inferior-rasa{% if puxavel %} gaveta-inferior-puxavel{% endif %}" …>
```

**`templates/core/home.html`**

```html
<script type="module" src="{% static 'js/ui/puxar_gaveta.js' %}"></script>
```

## 7 · Caveats
O arrasto é JavaScript de estado visual de um controle, que o §7.2 do CLAUDE.md condiciona à aprovação
do usuário, pedida junto com esta SPEC. Seguir o ponteiro não tem forma em CSS — o `resize` nativo só
oferece o canto inferior direito da caixa, e a borda que se puxa aqui é a de cima. O custo é a gaveta
inferior deixar de ter todo o seu estado em controles nativos: a altura puxada vive numa propriedade
escrita pelo script.

A altura é escrita na casca da home (`.tela-home`), e não na própria gaveta. É de lá que a gaveta
lateral lê a medida para parar acima da inferior, e ela não é descendente da placa. O custo é o script
conhecer a casca da home — gaveta puxável fora dela não se puxa — e cada movimento do ponteiro
recalcular o estilo da casca inteira, mapa incluído.

A altura puxada é uma só para a página: vale para qualquer gaveta puxável aberta depois e some na
recarga. Limpar a propriedade quando a gaveta sai pediria um segundo gancho no ciclo do HTMX, e quem
puxou o panorama uma vez o quer grande na próxima — descartado. O custo é que duas gavetas puxáveis de
natureza diferente herdam a altura uma da outra.

No teto, a gaveta lateral fica com a faixa que sobra acima da inferior. Deixar a inferior cobrir a
lateral quebraria a regra de que nenhuma gaveta se sobrepõe a outra — descartado. O custo é uma gaveta
lateral espremida enquanto a inferior está no alto, e o teto ser a medida que decide quanto.

A bancada de desenho passa a conhecer o evento `gaveta-inferior:puxada`. Ela só se reacomoda ao ouvir
`change` nos interruptores das gavetas, e o arrasto não muda interruptor nenhum. O custo é mais um
contrato entre a bancada e a gaveta, e quem ler a altura da gaveta sem ouvir o evento ficar com a
medida velha.

O arrasto não tem teste automatizado, contra o §9 do CLAUDE.md. O projeto não tem stack de teste de
navegador, e o que o servidor decide aqui é só a presença da marca. O custo é que uma regressão no
gesto — o clique engolido, o limite, a lateral atrasada — só aparece em uso.

## 8 · Testes (TDD)
O arrasto, os limites, a lateral que acompanha e a bancada que se reacomoda acontecem no navegador e
são conferidos pelo usuário; os testes fixam quem nasce puxável.

**Base de resultado de ação** — `tests/apps/mapping/test_resultado_acao.py`
- `test_resultado_de_acao_so_e_puxavel_quando_o_contexto_pede` — parametrizado: a base renderizada sem
  `puxavel` e com `puxavel=False` traz a placa sem a classe `gaveta-inferior-puxavel`; com
  `puxavel=True`, com ela, ao lado da `gaveta-inferior-rasa`.

**Lotes intersectados** — `tests/apps/lotes_mais_proximos/test_views.py`
- `test_lotes_do_desenho_nasce_sem_puxar` — a resposta de "Lotes intersectados" traz a gaveta inferior
  sem a classe `gaveta-inferior-puxavel`.
