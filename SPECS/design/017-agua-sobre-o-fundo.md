---
spec: design/017
versao: v4
atualizado_em: 2026-09-10
testes_tdd: true
implementado: true
markers_obrigatorios: []
changelog:
  - v1: versão inicial
  - v2: o controle de fundo ganha a engrenagem e o painel Ajustes da Animação, e o trilho do
    `.range-onsen` vira bandeja com fio entintado
  - v3: reconciliada com o mock aprovado — o disco de vidro é `.fundo-controle__acao` (e não um
    `.btn-disco-onsen` novo), o desligado da ortofoto vira fade, o fio entintado ganha módulo
    próprio e o preset padrão sobe de intensidade
  - v4: a abertura da água é sorteada e a superfície já entra aquecida, para que duas telas
    seguidas não mostrem a mesma cena
---

# SPEC design/017 — Água sobre o fundo administrativo

## 1 · User story
O servidor da DIMAP desliga o fundo de ortofoto no contexto das telas administrativas para obter um
fundo que continua tendo profundidade e movimento, em vez do branco da página sob a tinta azul.

## 2 · Condições de pronto
- [ ] Com o fundo **desligado**, o que aparece sob a lente é um **gradiente de rocha com grão**, nunca
      o branco da página; com a ortofoto na tela, nada dele aparece.
- [ ] Uma **superfície de água em movimento** ondula sobre os dois pisos — a ortofoto e o gradiente.
- [ ] Com a água **em repouso**, a tela fica **idêntica** à que existiria sem ela: a camada não pinta,
      só desvia a luz do que está atrás.
- [ ] A água **não reage ao ponteiro** e **não intercepta clique nem rolagem** em lugar nenhum da
      tela.
- [ ] A **engrenagem** do controle de fundo abre e fecha o painel **Ajustes da Animação**, que ascende
      do próprio controle.
- [ ] O painel **desliga a animação** e **devolve todos os ajustes ao padrão**, cada um por um gesto
      só; desligada, não há ajuste a mexer.
- [ ] Desligar a animação ou mexer em qualquer ajuste **permanece** na tela seguinte e na sessão
      seguinte.
- [ ] O trilho de qualquer `.range-onsen` **mostra quanto já foi percorrido**, e o polegar **incha e
      acende** sob o ponteiro.
- [ ] Sem **WebGL2**, sem alvo de renderização de ponto flutuante ou sob `prefers-reduced-motion:
      reduce`, as telas administrativas continuam respondendo, a água **não aparece**, **nenhum
      canvas** permanece no documento e a **engrenagem não se oferece**.
- [ ] Com a **aba oculta**, nenhum quadro é simulado nem desenhado; ao reexibir, a água retoma do
      ponto em que parou, sem salto.

## 3 · Domínio
Iteração de interface: nenhum model, nenhuma migração, nenhum domínio novo.

O fundo é o de [design/010](010-ortofotos-de-fundo.md) com o empilhamento de camadas de
[design/011](011-troca-de-fundo-sem-vao.md), e a pergunta que esta SPEC faz a ele é: **o que existe
atrás da lente?** Hoje a resposta é "a ortofoto, ou nada" — e "nada" é o branco do `base-100`, que a
tinta `mix-blend-multiply` só consegue tingir, não escurecer. Aqui a pilha ganha duas camadas, e a
resposta passa a ter três leituras:

| Estado | Piso | Superfície |
|---|---|---|
| Sem WebGL2, ou movimento reduzido | gradiente de rocha (fundo desligado) ou ortofoto | — |
| Fundo desligado | gradiente de rocha | água |
| Fundo ligado | ortofoto à deriva | água |

O **piso** é `.fundo-rocha`: um gradiente da escala `rocha-*` com grão, que existe exatamente quando
a ortofoto não existe. Ele obedece ao mesmo contrato que ela — a classe `fundo-desligado` no
`<html>` —, então nenhum estado novo entra no cliente.

A **superfície** é `.fundo-agua`: um campo de altura simulado em WebGL, do qual se extrai a
**cáustica** — a compressão de área do mapa de raios refratados — e o brilho especular da crista. Ela
é modelada como **lente, não como pigmento**: o canvas é cinza neutro e entra em `soft-light`, cujo
neutro é 0.5. Água em repouso tem relevo zero, jacobiano unitário e escreve exatamente 0.5 — a camada
desaparece sozinha, sem depender de opacidade. É esse invariante que faz a mesma peça servir sobre a
ortofoto e sobre o gradiente sem precisar conhecer nenhum dos dois.

A água não tem entrada: a camada é `pointer-events: none`, e quem a mexe é uma **deriva invisível** —
uma soma de senos incomensuráveis, que passeia sem repetir o traço — mais gotas ambientes.

**Quem calibra é quem olha.** O `.fundo-controle` de design/010 ganha uma **engrenagem**, e dela
ascende a **torre de ajustes** — mesma coreografia da `.torre-camadas` de
[design/016](016-controles-mapa-onsen.md). Ela expõe o parâmetro da água, o interruptor da animação e
a volta ao padrão. Os ajustes são **preferência de quem olha**, no mesmo regime do liga/desliga e da
velocidade da deriva: `localStorage`, nunca o servidor.

**Mock:** [017-mock-agua-sobre-o-fundo.html](017-mock-agua-sobre-o-fundo.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Refração do que está atrás: a ortofoto entrar como textura no WebGL para a onda deslocar a imagem —
  sem dono ainda.
- Água sobre o mapa Leaflet da home — sem dono ainda.
- Ondas onde o ponteiro passa — sem dono ainda.
- Presets nomeados de calibragem, além do padrão — sem dono ainda.

## 5 · Peças de referência a compor
- `@static/src/js/ui/controle_fundo.js` → classe `fundo-desligado` no `<html>` e o regime de
  preferência em `localStorage`.
- `@static/src/tema-dimap.dev.css` → `.torre-camadas--fechada/--aberta`: a coreografia de torre que
  ascende de um botão.
- `@static/src/tema-dimap.dev.css` → `.calha-cobertura` + `.etched-line` / `.etched-line-inked`: a
  bandeja funda com o fio entintado correndo no fundo.
- `@static/src/tema-dimap.dev.css` → escala `rocha-*`: os tons do gradiente do piso.
- `@templates/partials/_filtros_gravacao.html` → `#etched-onsen`: o relevo do polegar e dos glifos.
- Skills: `mock`, `componentes-frontend`.

## 6 · Snippets

A pilha do fundo administrativo ganha duas camadas, ambas em `z-0`, antes da lente. Ordem de DOM é
ordem de pintura: o piso, a ortofoto que o cobre quando existe, a água sobre os dois — e só então as
quatro camadas da lente, que seguem intocadas.

**`templates/mapping/_mapa_admin.html`**
```django
{% include "mapping/_glifos_fundo.html" %}
<div class="fundo-rocha"><div class="fundo-rocha__grao"></div></div>
{% include "mapping/_fundo_ortofoto.html" %}
{# Cinza neutro e opaco: quem o torna invisível em repouso é o soft-light, não a opacidade. #}
<canvas class="fundo-agua" aria-hidden="true"></canvas>
<div class="fixed inset-0 z-[1] pointer-events-none mix-blend-multiply bg-[#ade8f4]/90"></div>
{# ... as outras três camadas da lente, inalteradas ... #}
{% include "mapping/_controle_fundo.html" %}
<script src="{% static 'js/ui/controle_fundo.js' %}"></script>
<script type="module" src="{% static 'js/ui/fundo_ortofoto.js' %}"></script>
{# Dono único do fio entintado de qualquer .range-onsen da página. #}
<script type="module" src="{% static 'js/ui/trilho_onsen.js' %}"></script>
<script type="module" src="{% static 'js/ui/fundo_agua.js' %}"></script>
<script type="module" src="{% static 'js/ui/controle_agua.js' %}"></script>
```

O widget ganha a engrenagem no cabeçalho — fora do que recolhe com o fundo desligado: a água roda
nos dois estados. A torre mora dentro dele, ancorada no canto de onde ascende, e o `relative` do
markup é o que a ancora abaixo de `xl`, onde o widget deixa de ser `fixed`.

**`templates/mapping/_controle_fundo.html`**
```django
<div class="fundo-controle glass-panel relative self-end ml-auto mt-4 xl:fixed xl:bottom-6 xl:right-6 xl:z-20 transition-glass">

  <div class="torre-ajustes torre-ajustes--fechada" id="torre-ajustes">
    <p class="torre-ajustes__titulo">Ajustes da Animação</p>
    <div class="torre-ajustes__chave">
      <span class="text-overline">Animação</span>
      <input type="checkbox" class="toggle-onsen" data-agua-ligada checked aria-label="Ligar a animação da água">
    </div>
    {# Uma linha por parâmetro, montadas pelo controle_agua.js a partir da tabela de ajustáveis. #}
    <div class="torre-ajustes__barras" data-barras></div>
    <button class="btn-etched btn-etched-swell etched btn-etched-mini justify-center" type="button" data-padrao>
      <span class="icone-acao w-3.5 h-3.5 icon-etched"><svg viewBox="0 0 24 24"><use href="#glifo-padrao"/></svg></span>
      Padrão
    </button>
  </div>

  <div class="fundo-controle__cabecalho">
    <span class="text-overline fundo-controle__titulo">Fundo</span>
    <div class="fundo-controle__acoes">
      <span class="tooltip tooltip-left fundo-controle__dica" data-tip="Mostrar o fundo">
        <input type="checkbox" class="toggle-onsen" data-fundo-ligado checked aria-label="Mostrar o fundo">
      </span>
      {# O recolhimento embrulha só o Trocar: a engrenagem fica nos dois estados. #}
      <span class="tooltip tooltip-left fundo-controle__dica" data-tip="Trocar foto">
        <span class="fundo-controle__recolhe-x"><span class="fundo-controle__recolhido-x">
          <button class="btn btn-sm btn-circle btn-glass fundo-controle__acao" type="button" data-trocar
                  aria-label="Trocar a imagem de fundo"> ... </button>
        </span></span>
      </span>
      <span class="tooltip tooltip-left fundo-controle__dica ml-1.5" data-tip="Configurações">
        <button class="btn btn-sm btn-circle btn-glass fundo-controle__acao" type="button" data-ajustes
                aria-expanded="false" aria-controls="torre-ajustes" aria-label="Ajustes da animação"> ... </button>
      </span>
    </div>
  </div>

  <span class="tooltip tooltip-top fundo-controle__trilho" data-tip="Velocidade da deriva">
    <span class="fundo-controle__recolhe-y"><span class="fundo-controle__recolhido-y">
      <input type="range" class="range-onsen" min="0" max="4" step="1" value="2"
             data-nivel aria-label="Velocidade da deriva">
    </span></span>
  </span>
</div>
```

Os átomos novos e o alterado.

**`static/src/tema-dimap.dev.css`**
```css
:root {
  --fundo-rocha-grao: 0.055;
}

/* .fundo-rocha — átomo: o piso que existe exatamente quando a ortofoto não existe. */
.fundo-rocha {
  @apply fixed inset-0 z-0 pointer-events-none hidden overflow-hidden;
  background-image:
    radial-gradient(ellipse at 50% 30%, rgba(255, 255, 255, 0.35) 0%, transparent 62%),
    linear-gradient(163deg,
      var(--color-rocha-100) 0%,
      var(--color-rocha-300) 46%,
      var(--color-rocha-500) 100%);
}
html.fundo-desligado .fundo-rocha { @apply block; }

/* .fundo-rocha__grao — átomo. Tile de turbulência como IMAGEM, nunca como `filter`: filtro de tela
   cheia repinta a cada quadro. */
.fundo-rocha__grao {
  @apply absolute inset-0;
  opacity: var(--fundo-rocha-grao);
  background-size: 180px 180px;
  background-image: url("data:image/svg+xml,...feTurbulence...");
}

/* .fundo-agua — átomo: a superfície de luz sobre o piso, qualquer que ele seja. */
.fundo-agua {
  @apply fixed inset-0 z-0 pointer-events-none w-full h-full;
  mix-blend-mode: soft-light;
}

/* .fundo-controle__acao — vidro mais fino que o .btn-glass: o disco mora DENTRO de uma placa de
   gelo, e ali o branco a 40% do átomo soma com o do painel e estoura (SPEC design/009). Torre
   aberta: o disco afunda e vira poço — o gesto está preso, não pairando. */
.fundo-controle__acao {
  @apply w-7 h-7 min-h-0 shrink-0 rounded-full bg-white/8 border-white/30;
  @apply hover:bg-white/25 hover:border-white/50;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.35);
}
.fundo-controle__acao[aria-expanded="true"] {
  @apply bg-white/10 border-white/30;
  box-shadow: var(--sombra-poco-fina);
}

/* Recolhimento sem JS e sem medida fixa: a transição de `fr` fecha o vão sozinha, e o `w-fit` do
   widget acompanha quadro a quadro. O espaçamento mora DENTRO do que recolhe. */
.fundo-controle__recolhe-x { @apply grid transition-all duration-300 ease-out; grid-template-columns: 1fr; }
.fundo-controle:has([data-fundo-ligado]:not(:checked)) .fundo-controle__recolhe-x { grid-template-columns: 0fr; }

/* .fundo-ortofoto — ALTERADO nesta SPEC: desligar deixa de ser corte e vira fade. Sobre o piso de
   rocha o corte apareceria como salto, e `display` não transita. */
.fundo-ortofoto { transition: opacity var(--fundo-troca-duracao) ease-out; }
html.fundo-desligado .fundo-ortofoto { @apply opacity-0; }
/* Pausada, não zerada: `animation: none` devolveria a deriva ao ponto de partida. */
html.fundo-desligado .fundo-ortofoto__deriva,
html.fundo-desligado .fundo-ortofoto__imagem { animation-play-state: paused; }

/* .range-onsen — ALTERADO nesta SPEC: o trilho vira bandeja funda com o fio correndo no fundo,
   entintado até o polegar, e o polegar incha e acende sob o ponteiro. A bandeja nunca se preenche:
   o que muda de estado é o fio, como na .calha-cobertura. */
.range-onsen {
  @apply w-full h-4 appearance-none cursor-pointer rounded-full bg-white/30 border border-white/45;
  box-shadow: var(--sombra-poco-fina);
  background-image:
    linear-gradient(to right, rgba(0, 119, 182, 0.85), rgba(0, 119, 182, 0.85)),
    linear-gradient(to right, rgba(13, 27, 42, 0.14), rgba(13, 27, 42, 0.14));
  background-repeat: no-repeat;
  background-position: left center;
  background-size: var(--preenchimento, 0%) 0.375rem, 100% 0.375rem;
}
.range-onsen:hover::-webkit-slider-thumb,
.range-onsen:active::-webkit-slider-thumb {
  @apply scale-125;
  filter: url(#etched-onsen) drop-shadow(0 0 8px rgba(72, 202, 228, 0.95)) drop-shadow(0 0 12px rgba(0, 150, 199, 0.6));
}

/* .torre-ajustes — molécula: a torre que ascende da engrenagem. Coreografia da .torre-camadas,
   geometria de painel. */
.torre-ajustes {
  @apply absolute bottom-full right-0 mb-2.5 w-60 max-h-[70vh] overflow-y-auto overscroll-contain;
  @apply flex flex-col gap-2.5 p-3 rounded-2xl origin-bottom-right;
  @apply backdrop-blur-[18px] bg-gradient-to-br from-white/65 via-white/50 to-white/40 border border-white/60;
  @apply transition-all duration-300 ease-out;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.8), 0 8px 24px rgba(7,58,84,0.3), 0 0 20px rgba(72,202,228,0.2);
}
.torre-ajustes--fechada { @apply opacity-0 translate-y-3 scale-95 pointer-events-none; }
.torre-ajustes--aberta { @apply opacity-100 translate-y-0 scale-100 pointer-events-auto; }
/* Animação desligada: não há o que calibrar. Mesmo gesto do .fundo-controle__corpo. */
.torre-ajustes:has([data-agua-ligada]:not(:checked)) .torre-ajustes__barras {
  @apply opacity-35 pointer-events-none;
}
```

O preset. A água é textura do fundo, não assunto da tela — mas, como a torre a desliga por um
gesto só, ele é calibrado para ser visto, não para se esconder.

**`static/src/js/ui/fundo_agua.js`**
```javascript
export const PADRAO = Object.freeze({
  propagacao: 0.245,      // abaixo de 0.25 é a condição de estabilidade da equação de onda
  amortecimento: 0.998,
  caustica: 7.0,          // quanto o relevo comprime o mapa de raios
  piso: 0.3,              // achata o pico da cáustica — é este número que tira a água "intensa"
  teto: 2.4,
  contraste: 1.0,
  ganho: 0.3,             // desvio máximo em torno do neutro
  escalaNormal: 10.5,
  brilho: 0.13,
  dureza: 90,
  grao: 0.012,
  velocidadeDeriva: 0.75,
  baseDeriva: 0.012,
  ganhoDeriva: 0.9,
  tetoDeriva: 0.06,
  raioDeriva: 0.045,
  fontes: 4,
  forcaGota: 0.015,
  periodoGota: 2.4,
});

// Mutável de propósito: é o que a torre de ajustes escreve e o shader lê a cada quadro.
export const PARAMETROS = { ...PADRAO };
```

A guarda. Três motivos derrubam a água, e o desfecho dos três é o mesmo: o canvas **sai do
documento**, em vez de ficar como camada de blend inerte custando composição por nada.

```javascript
function iniciar() {
  const tela = document.querySelector(SELETOR);
  if (!tela) return;

  const parado = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const gl = parado
    ? null
    : tela.getContext("webgl2", { alpha: false, antialias: false, depth: false });
  const temAlvoFlutuante =
    gl?.getExtension("EXT_color_buffer_float") ?? gl?.getExtension("EXT_color_buffer_half_float");

  if (!gl || !temAlvoFlutuante) {
    tela.remove();
    return;
  }
  // ... alvos em ping-pong (RGBA16F), programas e uniformes: boilerplate de WebGL
}
```

O passo da simulação. O estado é um campo de altura em duas texturas alternadas: `r` é a altura
atual, `g` é a do passo anterior — a equação de onda precisa das duas.

**`shaders` de `static/src/js/ui/fundo_agua.js`**
```glsl
void main() {
  vec2 uv = vUv;
  float atual = texture(uEstado, uv).r;
  float anterior = texture(uEstado, uv).g;
  float e = texture(uEstado, uv - vec2(uTexel.x, 0.0)).r;
  float d = texture(uEstado, uv + vec2(uTexel.x, 0.0)).r;
  float c = texture(uEstado, uv + vec2(0.0, uTexel.y)).r;
  float b = texture(uEstado, uv - vec2(0.0, uTexel.y)).r;

  // Equação de onda discreta: extrapola a altura anterior e corrige pelo laplaciano dos vizinhos.
  float nova = (2.0 * atual - anterior) + (e + d + c + b - 4.0 * atual) * uPropagacao;
  nova *= uAmortecimento;

  // Cada gota é uma gaussiana somada ao relevo.
  for (int i = 0; i < MAX_GOTAS; i++) {
    if (i >= uQuantasGotas) break;
    vec2 delta = uv - uGotas[i].xy;
    delta.x *= uAspecto;
    nova += uGotas[i].z * exp(-dot(delta, delta) / (uGotas[i].w * uGotas[i].w));
  }

  // A borda absorve em vez de refletir: onda que volta da parede vira padrão estacionário visível.
  vec2 margem = min(uv, 1.0 - uv);
  nova *= mix(0.9, 1.0, smoothstep(0.0, 0.045, min(margem.x, margem.y)));

  saida = vec4(clamp(nova, -1.6, 1.6), atual, 0.0, 1.0);
}
```

O passe de pintura. **É aqui que está a regra desta SPEC**: a saída é luminância em torno de 0.5, e
não uma cor de água.

```glsl
void main() {
  vec2 uv = vUv, t = uTexel;
  float h   = texture(uEstado, uv).r;
  float he  = texture(uEstado, uv - vec2(t.x, 0.0)).r;
  float hd  = texture(uEstado, uv + vec2(t.x, 0.0)).r;
  float hc  = texture(uEstado, uv + vec2(0.0, t.y)).r;
  float hb  = texture(uEstado, uv - vec2(0.0, t.y)).r;
  float hdc = texture(uEstado, uv + t).r;
  float heb = texture(uEstado, uv - t).r;
  float hdb = texture(uEstado, uv + vec2(t.x, -t.y)).r;
  float hec = texture(uEstado, uv + vec2(-t.x, t.y)).r;

  float hx = (hd - he) * 0.5;
  float hy = (hc - hb) * 0.5;
  float hxx = hd - 2.0 * h + he;
  float hyy = hc - 2.0 * h + hb;
  float hxy = (hdc - hdb - hec + heb) * 0.25;

  // Cáustica: a luz que atravessa a superfície chega ao fundo comprimida na razão do jacobiano do
  // mapa de raios refratados. |det| < 1 concentra luz; superfície plana dá det = 1.
  float jxx = 1.0 - uCaustica * hxx;
  float jyy = 1.0 - uCaustica * hyy;
  float jxy = -uCaustica * hxy;
  float det = jxx * jyy - jxy * jxy;
  float ca = pow(clamp(1.0 / max(abs(det), uPiso), 0.0, uTeto), uContraste);

  // O glint que a crista acende, sob um sol frio e alto.
  vec3 normal = normalize(vec3(-hx * uEscalaNormal, -hy * uEscalaNormal, 1.0));
  vec3 meio = normalize(vec3(0.30, 0.45, 0.82) + vec3(0.0, 0.0, 1.0));
  float glint = pow(max(dot(normal, meio), 0.0), uDureza) * uBrilho;

  // O invariante: 0.5 é o neutro do soft-light. Água em repouso ⇒ det = 1 ⇒ ca = 1 ⇒ 0.5 exato, e a
  // camada some. A água só sabe desviar a luz do que já está atrás; ela não pinta nada.
  float luz = 0.5 + (ca - 1.0) * uGanho + glint;

  // A borda volta ao neutro: é onde a simulação tem artefato, e nenhum deles pode chegar à tela.
  luz = mix(luz, 0.5, smoothstep(0.55, 1.05, length((uv - 0.5) * vec2(uAspecto, 1.0))));

  luz += (ruido(uv * uResolucao + fract(uTempo)) - 0.5) * uGrao;
  cor = vec4(vec3(luz), 1.0);
}
```

Quem mexe a água. A camada não é alcançável pelo ponteiro, então não há gesto nenhum para escutar: o
movimento é todo interno.

```javascript
const TAU = Math.PI * 2;
const limitar = (valor) => Math.min(Math.max(valor, 0.06), 0.94);

// Soma de senos incomensuráveis: os períodos não têm razão racional entre si, então o traço nunca
// se fecha e a deriva não repete o caminho.
function derivaEm(tempo) {
  const s = PARAMETROS.velocidadeDeriva;
  const x = 0.5 + 0.30 * Math.sin(tempo * 0.037 * TAU * s) + 0.12 * Math.sin(tempo * 0.011 * TAU * s + 1.7);
  const y = 0.5 + 0.28 * Math.cos(tempo * 0.043 * TAU * s) + 0.13 * Math.cos(tempo * 0.017 * TAU * s + 4.1);
  return [limitar(x), limitar(y)];
}
```

O laço. Passo fixo com acumulador, teto de sub-passos e pausa explícita na aba oculta.

```javascript
function quadro(agora) {
  const decorrido = Math.min((agora - ultimo) / 1000, 0.25);
  ultimo = agora;
  acumulado += decorrido;

  let feitos = 0;
  while (acumulado >= PASSO && feitos < MAX_SUBPASSOS) {
    simular();
    acumulado -= PASSO;
    feitos += 1;
  }
  pintar();
  pedido = requestAnimationFrame(quadro);
}

// O rAF já é estrangulado em aba oculta, mas não parado em todo navegador — e um fundo decorativo
// não pode custar GPU numa aba que ninguém está vendo.
document.addEventListener("visibilitychange", () => (document.hidden ? parar() : rodar()));
```

A torre. Ela não sabe simular nada: escreve em `PARAMETROS`, que o shader lê no quadro seguinte.

**`static/src/js/ui/controle_agua.js`**
```javascript
import { PADRAO, PARAMETROS, ligar, desligar, existe } from "./fundo_agua.js";

// A tabela é o ÚNICO lugar em que os ajustáveis são enumerados: a torre é montada dela, e
// parâmetro que não está aqui não se oferece a quem olha.
const AJUSTAVEIS = [
  { k: "ganho", rotulo: "Intensidade", min: 0, max: 0.6, passo: 0.005 },
  { k: "caustica", rotulo: "Cáustica", min: 0, max: 14, passo: 0.1 },
  { k: "piso", rotulo: "Achatamento do pico", min: 0.05, max: 0.8, passo: 0.005 },
  // ... contraste, glint, relevo, velocidade da deriva, gotas, amortecimento, grão
];

// Sem água não há o que ajustar: a torre e a engrenagem saem do documento em vez de abrir vazias.
if (!existe()) {
  document.querySelector(".torre-ajustes")?.remove();
  document.querySelector("[data-ajustes]")?.remove();
}
```

O fio entintado é estado visual de um controle, e é a única coisa que o CSS não consegue ler
sozinho: a posição do polegar não existe como seletor. Ele tem **um dono só** — o `controle_fundo.js`
(clássico) mudaria o valor sem pintar e o `controle_agua.js` (módulo) não consegue importar dele,
então a peça mora num módulo próprio, importado por quem monta barras e carregado na página por
quem já tem barras.

**`static/src/js/ui/trilho_onsen.js`**
```javascript
export function pintarTrilho(barra) {
  const min = Number(barra.min || 0);
  const max = Number(barra.max || 100);
  const fracao = max === min ? 0 : (Number(barra.value) - min) / (max - min);
  barra.style.setProperty("--preenchimento", `${(fracao * 100).toFixed(2)}%`);
}

// O gesto do ponteiro chega pelo `input` delegado; quem muda o valor por código chama a função.
document.addEventListener("input", (evento) => {
  const barra = evento.target.closest(".range-onsen");
  if (barra) pintarTrilho(barra);
});

document.querySelectorAll(".range-onsen").forEach(pintarTrilho);
```

## 7 · Caveats

O `fundo_agua.js` é um módulo de ~150 linhas com dois shaders GLSL, e o §7.2 do CLAUDE.md permite JS
em três casos — callback de evento HTMX, utilitário do Leaflet e estado visual de um controle. Este
não é nenhum dos três: é uma exceção declarada e aprovada, sustentada por não haver regra de negócio,
estado de domínio nem UI montada a partir de JSON dentro dele — só um campo de altura desenhado num
canvas decorativo. O custo é que a fronteira do §7.2 passa a ter um precedente de "apresentação pura
em JS", que precisa ser negado caso a caso daqui em diante.

A pilha de lente do `_mapa_admin.html` e a molécula `.fundo-controle` são peças implementadas,
incluídas por mais de dez telas — login, painel, unidades, conferência de documento —, e o §3.4 as
protege de alteração sem aval. Inserir duas camadas antes da lente muda o que a tinta
`mix-blend-multiply` encontra como fundo em todas elas de uma vez. O custo é que qualquer erro de
calibragem aparece na área administrativa inteira, não numa tela.

O `.range-onsen` é alterado no lugar, com aval explícito, em vez de ganhar uma variante. Ele é usado
por um único componente — o próprio `.fundo-controle` —, e uma variante deixaria duas barras de
aparências diferentes lado a lado dentro do mesmo widget. O custo é que a entrada dele no styleguide
muda de aparência sem que nenhuma tela tenha pedido.

O disco de vidro nasce como parte da própria molécula (`.fundo-controle__acao`, empilhado sobre o
`.btn btn-circle btn-glass` do daisyUI) em vez de átomo novo, e a `.torre-ajustes` repete a
coreografia da `.torre-camadas`. A peça de origem da torre está implementada e serve a home, que o
§3.4 protege — generalizá-la mexeria nos controles do mapa sem que esta SPEC tenha nada a ver com
eles. O custo é vocabulário duplicado entre as duas torres, que vão divergir se uma delas for
retocada sozinha.

A `.fundo-ortofoto` deixa de sumir por `display` e passa a sumir por opacidade, para que o desligado
seja um fade sobre o piso de rocha em vez de um corte. Ela é peça implementada e o §3.4 a protege; a
alteração é feita com aval explícito. O custo é que, desligado, o organismo continua no documento
como camada `fixed` transparente de tela cheia, custando composição sem pintar nada.

A água entra como camada de luz e **não refrata** o que está atrás: a onda acende e apaga a
superfície, mas não desloca o pixel da ortofoto. Refratar exigiria puxar a ortofoto para dentro do
WebGL como textura, o que reescreveria o organismo `.fundo-ortofoto` e o rodízio com `decode()` da
design/011. O custo é que a leitura de "vidro d'água" fica menos convincente de perto do que a do
efeito de referência.

Os ajustes da animação vão para o `localStorage`, e não para o servidor como manda o §3.1 do
CLAUDE.md — pelo mesmo motivo já assumido em design/010 para o liga/desliga e a velocidade da
deriva: são preferências de quem está olhando, não estado da aplicação. O custo é que a calibragem
não acompanha o servidor entre dispositivos e some quando ele limpa o navegador.

Nenhuma condição de pronto desta SPEC tem teste automatizado de verdade — os testes da §8 só
verificam que as peças chegam ao HTML. O projeto não tem infraestrutura de teste de JavaScript nem de
render, e montá-la para um fundo decorativo custaria mais que a própria SPEC. O custo é que o
invariante do neutro, o fallback sem WebGL2, a coreografia da torre e a pausa na aba oculta são
verificados no mock e no smoke test, não na suíte.

A área administrativa passa a ter três camadas de tela cheia com `mix-blend-mode`, uma delas
redesenhada 30 vezes por segundo. Camada com blend força a página a um grupo de composição e derruba
otimização de camada da GPU, e a soma disso já é o que a lente cobra hoje. O custo é consumo contínuo
de GPU em toda tela administrativa aberta, inclusive esquecida — mitigado pela pausa na aba oculta e
pelo interruptor da torre, que não cobrem a janela visível e ociosa de quem não desligou nada.

A classe `fundo-desligado` no `<html>` ganha um terceiro consumidor, e ela continua sendo um contrato
que não está escrito em lugar nenhum além do CSS e dos módulos que a leem. O `.fundo-rocha` precisa
existir exatamente quando a ortofoto não existe, e é essa classe que sabe disso. O custo é que
renomeá-la quebra silenciosamente o piso, sem erro de execução.

O `prefers-reduced-motion` é lido uma vez, no boot do módulo. Reagir à mudança em tempo real pediria
um listener que sabe destruir e reconstruir o contexto WebGL, para um ajuste que se faz nas
preferências do sistema operacional. O custo é que trocar a preferência com a página aberta só surte
efeito no recarregamento seguinte.

## 8 · Testes (TDD)
- `test_tela_administrativa_traz_o_piso_de_rocha` — o HTML de uma tela administrativa traz
  `.fundo-rocha` com o `.fundo-rocha__grao` dentro.
- `test_tela_administrativa_traz_o_canvas_da_agua` — o mesmo HTML traz `<canvas class="fundo-agua">`
  e carrega `fundo_agua.js` e `controle_agua.js` como módulos.
- `test_controle_de_fundo_traz_a_engrenagem_e_a_torre` — o widget traz o `[data-ajustes]` com
  `aria-controls` apontando para a `.torre-ajustes`, que nasce fechada.
- `test_torre_de_ajustes_traz_o_interruptor_e_o_padrao` — a torre traz o título, o
  `[data-agua-ligada]` e o `[data-padrao]`.
- `test_home_nao_traz_o_fundo_administrativo` — a home, que roda sobre o Leaflet, não traz nenhuma das
  duas camadas novas.
