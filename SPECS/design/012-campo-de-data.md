---
spec: design/012
versao: v1
atualizado_em: 2026-09-05
testes_tdd: false
implementado: true
markers_obrigatorios: []
changelog:
  - v1: versão inicial
---

# SPEC design/012 — Campo de data do design system (`.campo-data`)

## 1 · User story
Servidor da DIMAP informa uma data em `dd/mm/aaaa` num formulário da área administrativa para
registrar o período de um ato sem traduzir o formato do seletor do sistema operacional.

## 2 · Condições de pronto
- [ ] Um campo de data mostra e aceita **`dd/mm/aaaa`**: digitar `05092026` exibe `05/09/2026`.
- [ ] O calendário abre num painel de vidro ancorado no campo, e escolher um dia escreve a data nele.
- [ ] Data digitada e data escolhida no calendário são o mesmo valor — o formulário continua enviando
      `AAAA-MM-DD` no nome de campo que já envia hoje.
- [ ] O campo vazio se lê como vazio: o texto de apoio é `dd/mm/aaaa` e o calendário abre no mês
      corrente sem dia marcado.
- [ ] O dia sob o ponteiro **incha e acende em ciano**; o dia escolhido fica preenchido de água; hoje
      tem marca própria mesmo sem estar escolhido.
- [ ] O calendário tem **uma caixa só**: a face de meses substitui a de dias e a de anos substitui a
      de meses, sem o painel mudar de altura. O título sobe a pilha; escolher desce de volta um nível.
- [ ] O calendário anda por teclado — setas, `PageUp`/`PageDown`, `Home`/`End`, `Enter` escolhe, `Esc`
      fecha — e `Tab` continua saindo do campo.
- [ ] Dia fora de `min`/`max` não é escolhível.
- [ ] Nenhum `input[type="date"]` da aplicação aparece sem a casca: o seletor do sistema operacional
      não é exibido em tela alguma.
- [ ] Design aprovado no mock e peças portadas para `static/src/tema-dimap.dev.css` e para
      `/design_system` antes de qualquer template da aplicação usar as classes.

## 3 · Domínio
Não há domínio novo. O campo continua sendo o `input[type="date"]` que o servidor já renderiza — ele
permanece no DOM como fonte da verdade do formulário, com valor ISO, e ganha uma casca de vidro. A
pergunta que esta SPEC faz ao domínio existente é nenhuma: view, DTO e model dos períodos
(`Impedimento`, `Substituicao`, `Delegacao`) seguem recebendo `AAAA-MM-DD` e não são tocados.

**Mock:** [012-mock-campo-de-data.html](012-mock-campo-de-data.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Seleção de **intervalo** num calendário único (dois campos seguem sendo dois) — sem dono ainda.
- Campo de **data e hora** — sem dono ainda.
- Formulários do Django admin, fora do design system — sem dono.

## 5 · Peças de referência a compor
- `@static/src/js/ui/select_onsen.js` → casca de popover sobre controle nativo: posicionamento,
  teclado, realce por `data-ativo` e `change` disparado no campo real.
- `@static/src/js/ui/campo_mascarado.js` → máscara por gabarito com cursor estável entre reformatações.
- `@static/src/tema-dimap.dev.css` → `.input-glass`, `.btn-etched-swell`, `.etched`, `.icon-etched`,
  `.text-overline`, `.form-field`, `.campo-periodo`.
- `@templates/partials/_filtros_gravacao.html` → `defs` do filtro de gravação, já incluídos no `base.html`.
- Skills: `mock`, `componentes-frontend`, `htmx`.

## 6 · Snippets

### A casca: o campo nativo continua sendo o campo

**`static/src/js/ui/campo_data.js`**
```javascript
// Didático (não portar): o módulo espelha select_onsen.js — o controle que o servidor renderizou
// some da tela, nunca do formulário, e a casca só escreve nele.
const GABARITO = "00/00/0000";

function montarCasca(nativo) {
  const casca = document.createElement("div");
  casca.className = "campo-data";
  nativo.parentNode.insertBefore(casca, nativo);
  casca.appendChild(nativo);
  nativo.hidden = true;
  return casca;
}

// A entrada visível herda as classes que o servidor escreveu no campo nativo — input-sm, w-full e
// o campo-realce-* de uma recusa chegam de graça, sem a casca conhecer nenhuma delas.
function montarEntrada(casca, nativo) {
  const entrada = document.createElement("input");
  entrada.type = "text";
  entrada.inputMode = "numeric";
  entrada.className = `${nativo.className} campo-data-entrada`;
  entrada.placeholder = "dd/mm/aaaa";
  entrada.value = paraBr(nativo.value);
  casca.appendChild(entrada);
  return entrada;
}
```

**`static/src/js/ui/campo_data.js`** — a conversão, o único lugar em que os dois formatos se encontram

```javascript
// Didático (não portar): o ISO é o que trafega; o dd/mm/aaaa só existe na tela. Data incompleta
// devolve string vazia em vez de data errada — meio valor não vira valor.
function paraBr(iso) {
  if (!iso) return "";
  const [ano, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${ano}`;
}

function paraIso(br) {
  const digitos = br.replace(/\D/g, "");
  if (digitos.length !== 8) return "";
  const dia = digitos.slice(0, 2);
  const mes = digitos.slice(2, 4);
  const ano = digitos.slice(4);
  const data = new Date(`${ano}-${mes}-${dia}T00:00:00`);
  // 31/02 existe como texto e não existe como data: o Date normaliza para 03/03 em silêncio, e é
  // essa volta que denuncia a diferença.
  if (Number.isNaN(data.getTime()) || data.getDate() !== Number(dia)) return "";
  return `${ano}-${mes}-${dia}`;
}

// Escrever no nativo E disparar change é o contrato inteiro com o resto do sistema: HTMX, validação
// do navegador e qualquer outro ouvinte continuam vendo o campo de sempre. Só quando o valor MUDA:
// a máscara reescreve o campo a cada tecla, e o card de busca do registro, que tem
// hx-trigger="change" no form, dispararia um request por dígito.
function escrever(nativo, iso) {
  if (nativo.value === iso) return;
  nativo.value = iso;
  nativo.dispatchEvent(new Event("change", { bubbles: true }));
}
```

### O calendário dentro de um `<label>`

**`static/src/js/ui/campo_data.js`**
```javascript
// Didático (não portar): todo campo de data do sistema mora dentro de um <label class="form-field">,
// e o painel é descendente dele no DOM mesmo vivendo na top layer. Sem cancelar o default, cada
// clique dentro do calendário ativa o rótulo, o foco salta para a entrada e o teclado morre.
painel.addEventListener("click", (evento) => {
  if (evento.target.closest("button")) evento.preventDefault();
});

// Pelo mesmo motivo o gatilho não usa popovertarget: ele precisa cancelar o default antes de abrir.
gatilho.addEventListener("click", (evento) => {
  evento.preventDefault();
  if (painel.matches(":popover-open")) painel.hidePopover();
  else abrir();
});
```

### A grade do mês

**`static/src/js/ui/campo_data.js`**
```javascript
// Didático (não portar): a grade tem 42 células sempre — seis semanas. Mês que cabe em cinco deixa
// o painel encolher e a linha de baixo dança sob o ponteiro a cada troca de mês.
const CELULAS = 42;

function diasDaGrade(ano, mes) {
  const primeiro = new Date(ano, mes, 1);
  // Domingo é o começo da semana no calendário brasileiro, e getDay() já conta a partir dele.
  const inicio = new Date(ano, mes, 1 - primeiro.getDay());
  return Array.from({ length: CELULAS }, (_, passo) => {
    const dia = new Date(inicio);
    dia.setDate(inicio.getDate() + passo);
    return dia;
  });
}
```

### A pilha das faces

**`static/src/js/ui/campo_data.js`**
```javascript
// Didático (não portar): sobe-se pelo título, desce-se escolhendo. Nenhuma face é acrescentada
// embaixo da outra — o corpo é uma caixa só, e o data-face diz qual delas está em cena.
titulo.addEventListener("click", () => {
  if (face === "anos") return;
  face = face === "dias" ? "meses" : "anos";
  desenhar();
});

painel.addEventListener("click", (evento) => {
  const alvo = evento.target.closest(".calendario-celula");
  if (!alvo || alvo.disabled) return;
  if (alvo.dataset.iso) return escolher(alvo.dataset.iso);
  // Escolher um mês devolve os dias; escolher um ano devolve os meses.
  if (alvo.dataset.mes) {
    visivel = new Date(visivel.getFullYear(), Number(alvo.dataset.mes), 1);
    face = "dias";
  } else if (alvo.dataset.ano) {
    visivel = new Date(Number(alvo.dataset.ano), visivel.getMonth(), 1);
    face = "meses";
  }
  desenhar();
});

function desenhar() {
  corpo.dataset.face = face;
  // O caret é a afordância da subida; sem ele o título é só o rótulo do nível.
  titulo.toggleAttribute("data-topo", face === "anos");
  caret.hidden = face === "anos";
  ...
}
```

### As peças, na camada a que pertencem

**`static/src/tema-dimap.dev.css`** — seção ÁTOMOS

```css
/* O gatilho do calendário: gravação em repouso, água e swell sob o ponteiro. Mora DENTRO do poço do
   campo, então não é botão de vidro — placa levantada dentro de cavidade fecha o degrau. */
.campo-data-gatilho {
  @apply absolute right-1.5 top-1/2 -translate-y-1/2 inline-flex items-center justify-center;
  @apply w-7 h-7 rounded-lg cursor-pointer transition-all duration-300 origin-center;
  filter: url(#etched-onsen);
  color: rgba(13, 27, 42, 0.35);
}
.campo-data-gatilho:hover,
.campo-data:focus-within .campo-data-gatilho {
  @apply scale-[1.12] bg-agua-400/20;
  filter: url(#etched-onsen) drop-shadow(0 0 6px rgba(72, 202, 228, 0.7));
  color: rgba(0, 119, 182, 0.85);
}
.campo-data-gatilho:focus-visible {
  @apply outline-none shadow-[0_0_0_3px_rgba(0,150,199,0.25)];
}

/* A célula do calendário — a mesma para dia, mês e ano. O swell é a afordância: a peça cresce sob o
   ponteiro antes de qualquer cor entrar. */
.calendario-celula {
  @apply inline-flex items-center justify-center h-9 rounded-xl text-sm text-base-content;
  @apply cursor-pointer transition-all duration-200 origin-center tabular-nums;
}
.calendario-celula:hover { @apply scale-[1.1] bg-agua-400/25 text-agua-800; }
.calendario-celula[data-fora]  { @apply text-base-content/30; }
/* Hoje é referência, não escolha: aro de água, sem preenchimento. */
.calendario-celula[data-hoje]  { @apply font-bold text-agua-700 shadow-[inset_0_0_0_1px_rgba(0,150,199,0.5)]; }
.calendario-celula[aria-selected="true"] {
  @apply font-bold text-rocha-950 bg-gradient-to-br from-agua-300 to-agua-500;
  @apply shadow-[0_4px_16px_rgba(0,150,199,0.45)];
}
/* Cursor do teclado: o MESMO marcador que o hover move, pelo motivo do .select-onsen-option. */
.calendario-celula[data-ativo="true"] {
  @apply bg-agua-400/45 text-rocha-950 outline-none;
  @apply shadow-[inset_0_0_0_1px_rgba(0,150,199,0.5),0_2px_10px_rgba(0,150,199,0.25)];
}
.calendario-celula[aria-selected="true"][data-ativo="true"] {
  @apply bg-gradient-to-br from-agua-300 to-agua-500 text-rocha-950;
  @apply shadow-[inset_0_0_0_1px_rgba(255,255,255,0.9),0_4px_18px_rgba(0,150,199,0.55)];
}
.calendario-celula:disabled { @apply opacity-25 cursor-not-allowed; }
.calendario-celula:disabled:hover { @apply scale-100 bg-transparent text-base-content; }
```

**`static/src/tema-dimap.dev.css`** — seção MOLÉCULAS

```css
/* .campo-data: o poço de sempre com o gatilho ancorado dentro dele. */
.campo-data { @apply relative w-full; }
.campo-data-entrada { @apply pr-9 tabular-nums; }

/* .calendario-onsen: mesma receita de top layer do .select-onsen-panel — popover, posição escrita
   pelo JS e inset: auto para derrubar o inset: 0 que o navegador dá a todo popover. Display e
   posição ficam no :popover-open, e não na base, senão o popover fechado aparece: a regra de autor
   que declara display vence o display: none do navegador. */
.calendario-onsen {
  @apply p-3 w-64 rounded-2xl backdrop-blur-[28px] bg-transparent;
  @apply bg-gradient-to-br from-white/88 via-white/82 to-white/76 border border-white/70 text-base-content;
  @apply shadow-[inset_0_1px_0_rgba(255,255,255,0.9),0_20px_50px_rgba(7,58,84,0.34),0_0_36px_rgba(72,202,228,0.28)];
}
.calendario-onsen:popover-open {
  @apply fixed m-0 flex flex-col gap-2;
  inset: auto;
}
.calendario-onsen:focus-visible { @apply outline-none; }
.calendario-onsen-topo   { @apply flex items-center justify-between gap-1; }
/* O corpo é UMA caixa: as faces se substituem dentro dela, e a altura mínima impede o painel de
   saltar quando a grade de 42 dias dá lugar à de 12 meses. */
.calendario-onsen-corpo  { @apply flex flex-col gap-1 min-h-[16rem]; }
.calendario-onsen-semana { @apply grid grid-cols-7 gap-1 text-center; }
.calendario-onsen-grade  { @apply grid grid-cols-7 gap-1; }
.calendario-onsen-meses  { @apply grid grid-cols-3 gap-1.5 flex-1 content-center; }
.calendario-onsen-anos   { @apply grid grid-cols-4 gap-1.5 flex-1 content-center overflow-y-auto overscroll-contain; }
/* Quem manda na substituição é o data-face do corpo, e não classe posta por JS: uma utility solta
   empata em força com o display: grid da peça, e a face escondida vaza embaixo da que está em cena. */
.calendario-onsen-corpo[data-face="dias"]  :is(.calendario-onsen-meses, .calendario-onsen-anos),
.calendario-onsen-corpo[data-face="meses"] :is(.calendario-onsen-semana, .calendario-onsen-grade, .calendario-onsen-anos),
.calendario-onsen-corpo[data-face="anos"]  :is(.calendario-onsen-semana, .calendario-onsen-grade, .calendario-onsen-meses) {
  @apply hidden;
}
/* No topo da pilha o título para de subir — e para de se oferecer. */
.calendario-onsen-titulo[data-topo] { @apply pointer-events-none; }
.calendario-onsen-rodape { @apply flex items-center justify-between gap-2 pt-1 border-t border-white/50; }
```

**`static/src/tema-dimap.dev.css`** — molécula existente, uma linha alterada

```css
/* ALTERADO: aprimorado o campo, quem ocupa a linha do intervalo é a casca — o mesmo caso já
   resolvido em .form-field-inline-action para o .select-onsen. */
.campo-periodo > :where(input, .campo-data) { @apply min-w-0 flex-1; }
```

### O refator: onde ele acontece

O campo nativo continua no template. A mudança é o atributo de adesão e o módulo na página — nenhuma
view, nenhum DTO, nenhum `name` muda.

```diff
- <input type="date" name="data_inicio" class="input input-glass {{ realce.data_inicio }}" value="{{ valores.data_inicio|default:'' }}" />
+ <input type="date" name="data_inicio" class="input input-glass {{ realce.data_inicio }}" value="{{ valores.data_inicio|default:'' }}" data-campo-data />
```

| Onde | Campos |
|---|---|
| `templates/user_admin/partials/_form_impedimento.html` | `data_inicio`, `data_fim` |
| `templates/user_admin/partials/_face_substituicao.html` | `data_inicio`, `data_fim` |
| `templates/user_admin/partials/_modal_designar.html` | `data_inicio`, `data_fim` |
| `templates/competencias/partials/_modal_delegar.html` | `data_inicio`, `data_fim` |
| `templates/competencias/partials/_busca_execucoes.html` | `inicio`, `fim` (dentro do `.campo-periodo`) |
| `templates/core/design_system.html` | as amostras do `.campo-periodo` + as peças novas nas seções 2 e 3 |

O módulo entra em toda página que **alcança** um desses partials — a maioria deles chega por HTMX,
então a conta não é "onde o campo é renderizado" e sim "de onde o modal pode ser aberto":
`templates/painel/painel.html`, `templates/user_admin/perfil.html`, `templates/unidades/unidade.html`,
`templates/competencias/conceder_competencia.html`, `templates/competencias/registro_acoes_list.html`
e `templates/core/design_system.html`. Em todas ele fica ao lado do `select_onsen.js`, que já responde
ao mesmo `htmx:afterSwap`.

```html
{# Modais e formulários chegam por HTMX: o módulo reage a htmx:afterSwap, como o select_onsen.js. #}
<script type="module" src="{% static 'js/ui/campo_data.js' %}"></script>
```

## 7 · Caveats

O calendário inteiro é JavaScript de interface — grade do mês, navegação e realce do cursor. O
CLAUDE.md §7.2 admite JS para estado visual de um controle **mediante aprovação**, e ela foi dada
explicitamente para esta peça. O custo é um controle cujo comportamento não é verificável pelos
testes do projeto: quem o valida é o mock e o olho.

Esta SPEC não traz teste automatizado, contra o §9 do CLAUDE.md. O que ela entrega é pele e teclado
sobre um campo cujo contrato com o servidor não muda — não há regra de domínio a fixar, e teste de
JS de interface exigiria uma stack de testes de navegador que o projeto não tem. O custo é que uma
regressão na casca só aparece em uso, e por isso o gate de `testes_tdd` fica levantado aqui por
decisão explícita do usuário.

A molécula `.campo-periodo` (SPEC painel/002) ganha uma linha para alcançar também a casca. É a
mesma alteração de uma linha que o `.select-onsen` exigiu do `.form-field-inline-action`, e sem ela
os dois campos do intervalo param de dividir a largura. O custo é uma peça já implementada tocada
por esta SPEC.

Sem JavaScript o formulário continua funcionando: o campo nativo segue no DOM, enviando e validando
como hoje. O custo é que nesse caminho o formato volta a ser o do sistema operacional — a promessa
de `dd/mm/aaaa` vale para a casca, não para o campo nu.

A data digitada é normalizada no cliente, que recusa `31/02` e escreve vazio no campo nativo. Isso
não é validação: a recusa de verdade continua no servidor, e o cliente só evita mandar lixo. O custo
é uma regra de calendário existindo em dois lugares — mas é regra do calendário gregoriano, não do
domínio da DIMAP.

## 8 · Testes (TDD)
_Sem teste automatizado._ O que aprova esta SPEC é o mock do §3, percorrido nos estados que ele
mostra, e o smoke das cinco telas refatoradas — ver o caveat do §7.
