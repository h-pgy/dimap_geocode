---
spec: design/011
versao: v1
atualizado_em: 2026-08-31
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC design/011 — Troca de fundo sem vão

## 1 · User story
O servidor da DIMAP permanece numa tela administrativa enquanto o fundo se renova sozinho para
obter a troca da ortofoto sem que a tela pisque.

## 2 · Condições de pronto
- [ ] A troca do fundo — pelo rodízio ou pelo botão **Trocar** — **nunca deixa a tela sem
      ortofoto**: a imagem que sai só some depois que a que entra está inteira na tela.
- [ ] Uma ortofoto que **demora a chegar atrasa a troca, não a interrompe**: a anterior segue
      exibida até a nova estar decodificada.
- [ ] O rodízio **continua sorteando diferente da que está na tela**, depois de qualquer número de
      trocas seguidas.
- [ ] Com o fundo **desligado**, o rodízio **não acumula camadas** no documento.
- [ ] O design foi aprovado no **mock**, e as peças foram portadas para
      `static/src/tema-dimap.dev.css` e para o styleguide.

## 3 · Domínio
Iteração de interface: nenhum model, nenhuma migração, nenhum domínio novo.

O fundo é o de [design/010](010-ortofotos-de-fundo.md), e a pergunta que esta SPEC faz a ele é:
**quantas ortofotos existem no documento durante uma troca?** Em 010 existe uma só, e o fade é
sequencial sobre ela — a imagem tem que sumir para a próxima poder entrar. Aqui existem duas: a que
chega nasce transparente **sobre** a que está na tela, e a que sai só é descartada depois que a
nova está opaca. O sequencial vira simultâneo, e a troca deixa de ter um instante sem imagem.

O que decide **quando** a nova camada começa a aparecer não é o relógio, e sim o `decode()` da sua
própria imagem. Por isso a ortofoto passa de `background-image` num `<div>` para um `<img>`: é o
elemento que mostra a imagem quem sabe dizer que ela está pronta.

As peças alteradas de 010 vêm inteiras no §6 — a partir daqui, elas são as desta SPEC.

**Mock:** [011-mock-troca-de-fundo-sem-vao.html](011-mock-troca-de-fundo-sem-vao.html) — leia a
skill `mock`.

## 4 · Fora de escopo
- Reencodar as ortofotos: PNG cinza de ~2 MB por ponto, ~16 MB no catálogo, contra ~760 KB em WebP
  q70 — sem dono ainda.
- Buscar a próxima ortofoto antes da hora da troca, para a camada nova já entrar decodificada — sem
  dono ainda.
- Parar o rodízio enquanto o fundo está desligado ou a aba está oculta — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/utils/sorteio` → `sortear_diferente`: o sorteio que nunca devolve a que está na tela.
- `@apps/mapping/context.py` → `ortofotos_disponiveis()`: interseção catálogo × disco, memoizada.
- `@static/src/js/ui/controle_fundo.js` → classe `fundo-desligado` no `<html>`: o contrato de
  "fundo desligado" já publicado.
- `@static/src/js/ui/select_onsen.js` → o padrão de módulo do projeto que reage a evento do HTMX.
- `@static/src/tema-dimap.dev.css` → `.fundo-ortofoto__deriva`: a moldura que transborda a viewport
  e carrega a deriva vertical.
- Skills: `mock`, `componentes-frontend`, `htmx`.

## 6 · Snippets

O `#fundo-ortofoto` deixa de ser o alvo que se substitui e passa a ser a **casca que permanece**:
`beforeend` empilha a camada nova como último filho, que em ordem de DOM é a de cima.

**`templates/mapping/_fundo_ortofoto.html`**
```django
{# A casca nunca é reescrita: é ela que garante que sempre há um recipiente com uma camada dentro. #}
<div class="fundo-ortofoto" id="fundo-ortofoto"
     hx-get="{% url 'mapping:fundo_ortofoto' %}"
     hx-trigger="every 60s, click from:[data-trocar]"
     hx-target="this" hx-swap="beforeend">
  {% include "mapping/_camada_ortofoto.html" %}
</div>
```

A camada é o que a rota devolve. `entrando` é o que separa os dois usos do mesmo partial: a camada
da primeira pintura já nasce visível, porque não há JS para revelá-la; a do rodízio nasce
transparente e espera o `decode()`.

**`templates/mapping/_camada_ortofoto.html`**
```django
{% load static %}
<div class="fundo-ortofoto__camada{% if not entrando %} fundo-ortofoto__camada--visivel{% endif %}"
     data-ortofoto="{{ ortofoto_fundo|default:'' }}">
  {% if ortofoto_fundo %}
  <div class="fundo-ortofoto__deriva">
    {# <img>, e não background-image: só o elemento que mostra a imagem sabe dizer que decodificou. #}
    <img class="fundo-ortofoto__imagem" alt="" aria-hidden="true"
         src="{% static "img/ortofotos_fundo/"|add:ortofoto_fundo|add:".png" %}" />
  </div>
  {% endif %}
</div>
```

A view muda só de partial: o sorteio e a rota aberta seguem os de 010.

**`apps/mapping/views.py`**
```python
def fundo_ortofoto(request: HttpRequest) -> HttpResponse:
    """Rota aberta (design/010 §3): a tela de login é anônima e mostra o mesmo fundo."""
    disponiveis = ortofotos_disponiveis()
    escolhida = sortear_diferente(disponiveis, request.GET.get("atual")) if disponiveis else None
    return render(
        request,
        "mapping/_camada_ortofoto.html",
        {"ortofoto_fundo": escolhida, "entrando": True},
    )
```

A regra desta SPEC está aqui: **o que dispara a revelação é o `decode()`, não um `transition` no
relógio.** Enquanto a imagem não existe em pixel, quem está na tela é a camada anterior, inteira.

**`static/src/js/ui/fundo_ortofoto.js`**
```javascript
const ID_CASCA = "fundo-ortofoto";
const SELETOR_CAMADA = ".fundo-ortofoto__camada";
const CLASSE_VISIVEL = "fundo-ortofoto__camada--visivel";

// A casca não é reescrita no swap: `atual` fixado na URL congelaria na primeira ortofoto e o
// sorteio voltaria a repetir a que está na tela. Quem sabe qual está em cima é a última camada.
document.body.addEventListener("htmx:configRequest", (evento) => {
  const casca = evento.detail.elt;
  if (casca.id !== ID_CASCA) return;
  evento.detail.parameters.atual = casca.lastElementChild?.dataset.ortofoto ?? "";
});

document.body.addEventListener("htmx:afterSwap", (evento) => {
  if (evento.target.id !== ID_CASCA) return;
  aparar(evento.target);
  revelar(evento.target.lastElementChild);
});

// Invariante: no máximo duas camadas. Com o fundo desligado o elemento é `display: none`, nenhuma
// transição roda e o descarte nunca dispara — sem esta poda o rodízio empilharia para sempre.
function aparar(casca) {
  const camadas = [...casca.querySelectorAll(SELETOR_CAMADA)];
  for (const camada of camadas.slice(0, -2)) camada.remove();
}

// O gate. `decode()` resolve quando o pixel existe, não quando o byte chega — é o que impede a
// camada nova de subir sobre nada.
async function revelar(camada) {
  const imagem = camada?.querySelector("img");
  if (imagem) {
    try {
      await imagem.decode();
    } catch {
      /* PNG ausente ou corrompido: revela assim mesmo, e a lente sozinha vira o piso visual */
    }
  }
  camada.addEventListener("transitionend", () => descartarAnteriores(camada), { once: true });
  camada.classList.add(CLASSE_VISIVEL);
}

// A anterior só sai depois que a nova chegou a opacity 1: em nenhum quadro as duas somam menos que
// uma imagem opaca.
function descartarAnteriores(camada) {
  for (const anterior of camada.parentElement.querySelectorAll(SELETOR_CAMADA)) {
    if (anterior !== camada) anterior.remove();
  }
}
```

O tema perde o fade sequencial (`.htmx-swapping` / `.htmx-added` sobre `.fundo-ortofoto`) e ganha a
camada. A deriva não muda de lugar: continua no `.fundo-ortofoto__deriva`, agora dentro da camada.

**`static/src/tema-dimap.dev.css`**
```css
:root {
  --fundo-troca-duracao: 700ms;
}

/* .fundo-ortofoto — organismo: a casca que permanece, empilhando camadas absolutas. */
.fundo-ortofoto {
  @apply fixed inset-0 z-0 pointer-events-none overflow-hidden;
}
html.fundo-desligado .fundo-ortofoto { @apply hidden; }

/* .fundo-ortofoto__camada — átomo: uma ortofoto e a deriva dela. Entra transparente; a classe que
   a revela é posta pelo JS depois do decode, nunca por timer. */
.fundo-ortofoto__camada {
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity var(--fundo-troca-duracao) ease-out;
}
.fundo-ortofoto__camada--visivel { opacity: 1; }

/* object-fit: cover é o equivalente exato do background-size: cover que sai daqui. */
.fundo-ortofoto__imagem {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  animation-name: deriva-horizontal;
  animation-duration: calc(var(--deriva-periodo) / 4);
  animation-timing-function: ease-in-out;
  animation-iteration-count: infinite;
  animation-direction: alternate;
}
```

**`templates/mapping/_mapa_admin.html`**
```django
{# Módulo, e não script clássico: só precisa existir antes do primeiro rodízio, um minuto depois. #}
<script type="module" src="{% static 'js/ui/fundo_ortofoto.js' %}"></script>
```

## 7 · Caveats

O `.fundo-ortofoto__imagem` deixa de ser `<div>` com `background-image` e passa a ser `<img>` com
`object-fit`, alterando um átomo já implementado que o §3.4 do CLAUDE.md protege. Só o elemento que
carrega a imagem expõe `decode()`, e sem esse sinal a revelação voltaria a depender de um timer —
que é exatamente a causa do vão. O custo é que o átomo muda de tag, e quem compuser com ele passa a
herdar um elemento substituído, com as regras de dimensionamento que vêm junto.

O `decode()` — o núcleo da correção — não tem teste automatizado. O projeto não tem infraestrutura
de teste de JavaScript, e montá-la para três funções custaria mais que a própria SPEC. O custo é
que a condição de pronto mais importante é verificada no mock e no smoke test, não na suíte.

O `fundo_ortofoto.js` passa a conhecer a classe `fundo-desligado`, que é do `controle_fundo.js`, e
os dois módulos passam a compartilhar um contrato que não está em lugar nenhum além do CSS. A poda
existe só por causa do estado desligado, então ela não tem como ignorá-lo. O custo é que renomear
essa classe quebra silenciosamente a poda, sem erro de execução.

O `atual` sai da URL do `hx-get` e passa a ser montado em `htmx:configRequest`. A casca não é
reescrita no swap, então um valor fixado no template envelheceria na primeira troca. O custo é que
ler o template deixa de dizer o que a rota recebe: o parâmetro só aparece no JS.

Duas camadas coexistem enquanto a nova sobe, e as duas mantêm as animações de deriva rodando. Parar
a de baixo com `animation: none` a devolveria ao ponto zero da translação, um salto de até 200 px
bem no meio do crossfade. O custo é o dobro de trabalho de composição do fundo durante os 700 ms
da troca.

## 8 · Testes (TDD)
- `test_rota_do_fundo_devolve_apenas_a_camada` — a resposta traz uma `.fundo-ortofoto__camada` e
  **não** traz o `#fundo-ortofoto`, que é a casca que permanece na página.
- `test_camada_do_rodizio_chega_transparente` — a camada devolvida pela rota **não** traz
  `--visivel`; a renderizada junto com a página traz.
- `test_camada_declara_a_ortofoto_que_mostra` — o `data-ortofoto` da camada é a chave sorteada, que
  é o que alimenta o `atual` da requisição seguinte.
- `test_rota_do_fundo_devolve_ortofoto_diferente` — `GET` com `?atual=` devolve a camada com outra
  ortofoto disponível.
- `test_pagina_administrativa_sem_ortofoto_disponivel` — sem nenhum PNG em disco, o login responde
  200 e o HTML não traz `<img>` de fundo. *(marker `banco`)*
