---
spec: design/013
versao: v1
atualizado_em: 2026-09-05
testes_tdd: false
implementado: false
changelog:
  - v1: versão inicial
---

# SPEC design/013 — Gaveta lateral e a paleta

## 1 · User story
O servidor da DIMAP abre a gaveta da entidade localizada no contexto da home para ler os dados dela
sem tirar o mapa da tela.

## 2 · Condições de pronto
- [ ] Com a gaveta recolhida, o que aparece sobre o mapa é **só a paleta**: um meio disco de gelo
      rente à borda esquerda, centrado verticalmente, com o glifo `>` gravado.
- [ ] Acionar a paleta desliza a gaveta a partir da esquerda e **leva a paleta junto**, agora rente à
      borda direita da gaveta e com o glifo apontando para dentro; acioná-la de novo recolhe.
- [ ] A gaveta aberta sobre o mapa vivo sustenta **texto denso**: adota a mesma densidade de gelo
      da caixa de modal, e nenhum traço do mapa atravessa a leitura.
- [ ] A gaveta comporta, na mesma coluna, **texto corrido, indicadores numéricos e um mapa Leaflet
      interativo** — o mapa da gaveta responde a zoom e arrasto sem mover o mapa de fundo.
- [ ] O mapa da gaveta vem **emoldurado**: um poço em volta, com o mapa assentado nele como placa.
- [ ] Conteúdo mais alto que a gaveta **rola dentro dela**, com a barra gravada; o cabeçalho da
      gaveta não sai de cena e a página não rola.
- [ ] Uma linha de detalhe da gaveta abre a **segunda gaveta**, que sai **de trás da primeira** e
      permanece um degrau atrás: aberta, ela mantém o tamanho natural, e o que a põe atrás é a folga
      vertical, a aresta da primeira por cima e o material sem brilho.
- [ ] A segunda gaveta traz a **sua própria paleta** na borda externa, no material do plano recuado.
- [ ] Recolher a primeira gaveta leva a segunda junto, sem que ela reapareça sozinha à frente.
- [ ] A gaveta sem entidade resolvida mostra o **estado de falta escrito**, e não uma placa em branco.
- [ ] A barra de busca **sai de cena** quando a gaveta abre e volta quando ela recolhe.
- [ ] Nenhum estado de gaveta vive em JavaScript: abrir, recolher e o plano recuado são CSS.
- [ ] O design foi aprovado no mock e as peças foram portadas para `static/src/tema-dimap.dev.css`
      e registradas no styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
SPEC de interface: não introduz domínio. As peças entregues são a casca da gaveta, e o conteúdo que
elas recebem é sempre a ontologia da entidade territorial resolvida pela busca — de quem esta SPEC
não pergunta nada além de "cabe em texto, número ou geometria?".

**Mock:** [013-mock-gaveta-lateral-e-paleta.html](013-mock-gaveta-lateral-e-paleta.html) — leia a
skill `mock`.

## 4 · Fora de escopo
- Conteúdo da gaveta por tipo de entidade (logradouro, lote, endereço, quadra) — épico
  `geocodificacao`, sem dono ainda.
- Ações na gaveta e o router perfil × tipo de entidade — épico `autorizacao`, sem dono ainda.
- O gatilho HTMX que carrega a gaveta a partir do resultado da busca — sem dono ainda.
- A gaveta da direita (conta, projetos, camadas) — sem dono ainda.
- A geometria real dentro do mapa da gaveta: aqui ele é canvas, não resultado — sem dono ainda.

## 5 · Peças de referência a compor
- `@static/src/tema-dimap.dev.css` → `.glass-drawer-panel`: material da gaveta lateral.
- `@static/src/tema-dimap.dev.css` → `.card-well` e `--sombra-poco`: poço dos indicadores e moldura do mapa.
- `@static/src/tema-dimap.dev.css` → `.modal-box-glass` e `--radius-placa`: a terceira densidade e o raio da placa assentada.
- `@static/src/tema-dimap.dev.css` → `.etched` / `.etched-inked`: gravação do glifo da paleta.
- `@static/src/js/ui/scroll_etched.js` + `.scroll-etched`: barra de rolagem do corpo da gaveta.
- `@static/src/tema-dimap.dev.css` → `.gaveta-vazia`: o estado de falta escrito, da gaveta inferior.
- `@static/src/tema-dimap.dev.css` → `.search-hero` / `.search-panel`: a UI que recolhe.
- `@templates/mapping/_mapa_fullscreen.html` → a lente da home, atrás da qual a gaveta desliza.
- `@static/src/js/mapa/criar_mapa.js` e `camada_base.js`: instância e base WMS do mapa da gaveta.
- Skills: `mock`, `componentes-frontend`, `leaflet-map`.

## 6 · Snippets

**`static/src/tema-dimap.dev.css`** — tokens da gaveta

```css
html[data-theme="dimap"] {
  --gaveta-largura: 25rem;
  --gaveta-detalhe-largura: 21rem;
  /* Quanto da segunda gaveta fica enfiado sob a primeira quando ela está aberta: é o que a paleta
     cobre mais a folga da sombra. É também o que a segunda gaveta reserva de padding à esquerda. */
  --gaveta-recuo: 4rem;
}
```

**`static/src/tema-dimap.dev.css`** — os dois planos, na terceira densidade

```css
@layer components {
  /* A terceira densidade deixa de morar dentro do .modal-box-glass e passa a ser primitivo: o gelo
     que SUBSTITUI o que está atrás, em vez de flutuar sobre ele. A gaveta é o segundo lugar que
     precisa dela — sobre o mapa vivo, o gelo fino deixa o traço do mapa atravessar o texto. */
  .glass-blur-denso { @apply backdrop-blur-[28px]; }
  .glass-bg-denso   { @apply bg-gradient-to-br from-white/97 via-white/93 to-white/88; }

  /* A mesma densidade na direção da gaveta: a luz entra pela borda direita, que é a que fica solta. */
  .glass-drawer-panel-denso {
    @apply backdrop-blur-[28px] bg-gradient-to-l from-white/97 via-white/93 to-white/88 border-r border-white/80;
    @apply shadow-[inset_0_1px_0_rgba(255,255,255,1),12px_0_40px_rgba(7,58,84,0.3),0_0_36px_rgba(72,202,228,0.25)];
  }

  /* O plano de trás é um degrau, não um andar: mesma densidade, sem o brilho ciano, e a sombra da
     placa da frente apenas encostando na aresta esquerda. */
  .glass-drawer-panel-recuado {
    @apply backdrop-blur-[28px] bg-gradient-to-l from-white/94 via-white/90 to-white/85 border border-white/60;
    box-shadow:
      inset 16px 0 22px -16px rgba(7, 58, 84, 0.3),
      inset 0 1px 0 rgba(255, 255, 255, 0.85),
      10px 0 28px rgba(7, 58, 84, 0.18);
  }
}
```

**`static/src/tema-dimap.dev.css`** — o mapa emoldurado

```css
@layer components {
  /* Poço em volta (o .card-well empilhado no markup) e, dentro dele, o mapa como PLACA ASSENTADA:
     raio de placa, aresta de luz e sombra por FORA. Poço dentro de poço perderia o degrau — e o que
     se quer aqui é levantar o mapa, não afundá-lo mais. */
  .mapa-gaveta-moldura { @apply flex flex-col gap-2 p-3; }
  .mapa-gaveta {
    @apply relative isolate w-full h-52 overflow-hidden border border-white/70;
    border-radius: var(--radius-placa);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.9),
      0 8px 20px rgba(7, 58, 84, 0.3),
      0 0 22px rgba(72, 202, 228, 0.25);
  }
  /* A lente da home em miniatura: tinta de água límpida e vinheta ciana só na borda. */
  .mapa-gaveta::after {
    content: "";
    @apply absolute inset-0 z-10 pointer-events-none mix-blend-multiply bg-[#bfeaf5]/60;
  }
  .mapa-gaveta::before {
    content: "";
    @apply absolute inset-0 z-20 pointer-events-none;
    background: radial-gradient(ellipse at center, transparent 55%, rgba(0, 119, 182, 0.22) 100%);
  }
}
```

**`static/src/tema-dimap.dev.css`** — a paleta e a âncora que a faz servir aos dois estados

```css
@layer components {
  /* Meio disco: largura = raio, altura = diâmetro, com a aresta reta encostada na gaveta.
     Ancorada em left-full (a borda direita da casca), ela não precisa de duas posições: fechada, a
     casca está deslocada de -100% e a paleta cai exatamente sobre a borda da tela. */
  .paleta-gaveta {
    @apply absolute left-full top-1/2 -translate-y-1/2 z-20 pointer-events-auto;
    @apply w-9 h-[4.5rem] rounded-r-full grid place-items-center cursor-pointer;
    @apply backdrop-blur-[12px] bg-gradient-to-r from-white/78 to-white/58 border border-l-0 border-white/60;
    @apply shadow-[inset_0_1px_0_rgba(255,255,255,0.85),8px_0_24px_rgba(7,58,84,0.28),0_0_20px_rgba(72,202,228,0.25)];
    @apply transition-all duration-300;
  }
  .paleta-gaveta:hover { @apply from-white/90 to-white/72; }

  /* O glifo é .etched no markup: a seta é afordância pura — quem informa que a gaveta está aberta é
     a gaveta na tela, não o desenho dela. */
  .paleta-gaveta-glifo { @apply w-5 h-5 transition-transform duration-500; }
  .paleta-gaveta:hover .paleta-gaveta-glifo {
    filter: url(#etched-onsen) drop-shadow(0 0 6px rgba(72, 202, 228, 0.7));
    color: rgba(0, 119, 182, 0.85);
  }
}
```

**`static/src/tema-dimap.dev.css`** — a coreografia, lida do DOM

```css
@layer components {
  /* absolute, não fixed: a âncora é a casca da home (relative h-screen w-screen overflow-hidden),
     e é o que permite ao mock renderizar a tela montada dentro de um quadro. */
  .gaveta-lateral {
    @apply absolute left-0 inset-y-0 z-30 pointer-events-none;
    width: var(--gaveta-largura);
    transform: translateX(-100%);
    @apply transition-transform duration-500 ease-in-out;
  }
  /* O interruptor mora DENTRO da casca: a peça não depende de nenhuma classe no ancestral e pode
     ser incluída em qualquer tela. */
  .gaveta-lateral:has(> .gaveta-lateral-toggle:checked) { transform: translateX(0); }
  .gaveta-lateral:has(> .gaveta-lateral-toggle:checked) .paleta-gaveta-glifo { @apply rotate-180; }

  /* Fechada, a segunda gaveta cabe inteira atrás da primeira — daí o translate de exatamente
     (largura - recuo). Aberta, ela só volta a zero: o quanto ela aparece já está na conta. */
  .gaveta-lateral-detalhe {
    @apply absolute inset-y-4 z-0 origin-left opacity-0 pointer-events-none;
    left: calc(100% - var(--gaveta-recuo));
    width: var(--gaveta-detalhe-largura);
    transform: translateX(calc(-1 * (var(--gaveta-detalhe-largura) - var(--gaveta-recuo)))) scale(0.98);
    @apply transition-all duration-500 ease-in-out;
  }
  /* Aberta, ela volta ao tamanho natural: quem diz que está atrás é a folga vertical, a aresta da
     primeira por cima e o material sem brilho — não um encolhimento. */
  .gaveta-lateral:has(> .gaveta-lateral-detalhe-toggle:checked) .gaveta-lateral-detalhe {
    @apply opacity-100 pointer-events-auto;
    transform: translateX(0) scale(1);
  }
}
```

**`templates/core/home.html`** — a casca recebe o nome que a busca lê

```html
<!-- A gaveta é irmã do mapa e da UI flutuante; a classe na casca é o que permite ao CSS recolher a
     busca quando ela abre, sem JavaScript imperativo. -->
<div class="tela-home relative h-screen w-screen overflow-hidden">
  {% include "mapping/_mapa_fullscreen.html" %}
  <div class="search-hero ...">…</div>
  {% include "search/partials/_gaveta_entidade.html" %}
</div>
```

```css
/* static/src/tema-dimap.dev.css — mesma direção do recolhimento que a .glass-hide-up já usa. */
.tela-home:has(.gaveta-lateral-toggle:checked) .search-hero {
  @apply opacity-0 -translate-y-5 scale-95 pointer-events-none;
}
```

**`static/src/js/mapa/gaveta_mapa.js`** — a única linha de JS da SPEC

```javascript
// O Leaflet mede o container no momento em que o mapa nasce. Dentro de uma gaveta que entra por
// transform, essa medida acontece com a gaveta ainda fora da tela — e os tiles saem cortados.
// Cola de Leaflet, não estado: quem sabe que a gaveta abriu é o CSS.
gaveta.addEventListener("transitionend", () => mapa.invalidateSize());
```

## 7 · Caveats
A segunda gaveta guarda o próprio estado marcado enquanto a primeira recolhe. Recolher a primeira a
esconde junto — ela viaja na mesma casca —, mas reabrir a primeira devolve a segunda aberta no ponto
em que estava. O custo é que o usuário pode reabrir a gaveta e encontrar dois planos onde deixou
dois, sem um gesto que zere o conjunto de uma vez.

A posição da paleta é ancorada em `left-full` da casca, então ela depende de `--gaveta-largura` para
cair exatamente sobre a borda da tela quando recolhida. Uma gaveta de outra largura muda a variável;
reposicionar a paleta por utility no markup quebra o estado fechado sem quebrar o aberto, que é a
pior forma de quebrar.

O mapa da gaveta é uma segunda instância Leaflet na home, com a mesma base WMS do mapa de fundo.
Dobra o tráfego de tiles enquanto a gaveta está aberta, e é o preço de mostrar a geometria no lugar
onde os dados dela estão sendo lidos, em vez de mandar o olho até o fundo.

A terceira densidade deixa de ser exclusiva do modal e passa a ser primitivo compartilhado
(`.glass-blur-denso` / `.glass-bg-denso`), consumido pela gaveta e pelo `.modal-box-glass`. A razão é
que a gaveta responde à mesma pergunta que o modal — ela substitui o que está atrás enquanto está
aberta, e sobre o mapa vivo o gelo fino deixa o traço atravessar o texto. O custo é que a densidade
do modal deixa de poder ser calibrada sozinha: mexer nela passa a mexer na gaveta.

A SPEC design/014 já entrega uma gaveta — a inferior — para a **mesma pergunta**: mostrar o que a
busca resolveu sem perder o mapa. As duas passam a conviver no design system, e a escolha de qual a
home usa fica em aberto. O custo é um segundo organismo de gaveta a manter enquanto a decisão não
vem, e a nota do styleguide da 014 que descreve o `.glass-drawer-bottom` como "a receita da gaveta
lateral, mesma densidade e mesmo blur de 12px" deixa de valer para a lateral desta SPEC.

A família `.gaveta-*` é da gaveta inferior, então a lateral se nomeia por inteiro
(`.gaveta-lateral*`) — inclusive o interruptor, que de outro modo colidiria com o `.gaveta-toggle`
já implementado. A razão é que os dois interruptores têm mecanismos diferentes de leitura de estado
(irmão imediato lá, filho imediato aqui) e um nome só para os dois esconderia isso. O custo é um
prefixo mais longo em todas as peças da casca.

A regra de vidro sobre vidro da SPEC design/009 passa a listar `.glass-drawer-panel-denso` e `.glass-drawer-panel-recuado` entre os materiais que apagam a tinta das placas aninhadas. É edição
de uma peça existente, e sem ela os poços dentro das gavetas pintariam branco onde toda outra placa
aninhada já não pinta.

## 8 · Testes (TDD)
_Sem teste automatizado._ O que aprova esta SPEC é o mock do §3, percorrido nos estados que ele
mostra — recolhida, aberta, com a segunda gaveta atrás, com o corpo rolando e com o mapa vivo
emoldurado dentro dela.
