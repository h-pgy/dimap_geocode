---
name: mock
description: "Como construir o mock HTML de validação de design do DIMAP GeoCoder — o artefato que aprova interface antes de qualquer código de aplicação. Use SEMPRE que a SPEC da vez tiver entregável de front-end/interface (componente novo do design system, tela nova, mudança de layout ou de coreografia), e sempre que for escrever, revisar ou portar um mock. Complementar às skills specs e componentes-frontend."
---

# Skill: Mock de validação — DIMAP GeoCoder

**Prosa não aprova interface.** Descrever "poço rebaixado com aresta tracejada que acende no foco" não
permite julgar nada — ver na tela permite. O mock é para o front-end o que o snippet é para o domínio:
o artefato pelo qual a iteração é avaliada.

---

## Fronteira: o que é desta skill e o que é das outras

> **Antes de escrever qualquer mock, leia a skill `componentes-frontend`.** É ela que traz o design
> system — tokens, escalas, materiais, o método do Atomic Design e o **styleguide** com tudo que já
> existe. Sem ela você reinventa peça que já está pronta, que é o erro que o mock existe para impedir.

Esta skill trata **só do front-end/interface** — a marcação, o estilo e o pouco de JS do mock:

| Assunto | Dono |
|---|---|
| Tokens, escalas, materiais, método do Atomic Design, styleguide das peças existentes | skill **`componentes-frontend`** |
| Quando a SPEC exige mock; o link na SPEC; a condição de pronto; a ordem dos portões (modelagem → visual → TDD); quando a SPEC conta como implementada | skill **`specs`** |
| Loader do tema e do fundo, estrutura e template do mock, estados a mostrar, comentários no arquivo, recorte de partials, porte das peças | **esta skill** |

Duas consequências práticas:

- **O mock só começa depois de a modelagem estar aprovada.** Se a SPEC `.md` ainda não recebeu o "ok",
  não é hora de mock — veja a ordem dos portões na skill `specs`.
- **O mock fala de tela.** Decisão de modelagem é da SPEC; aqui ela é **referenciada**, no máximo,
  nunca reexplicada.

---

## Onde mora

`SPECS/<epico>/NNN-mock-<slug>.html` — ao lado da SPEC, mesmo prefixo numérico. O mock **não é uma
SPEC**: sem numeração própria, sem front-matter, fora da ordem de implementação do épico.

---

## Como o mock carrega o tema

O mock **não duplica o design system**. Ele faz `fetch` de `static/src/tema-dimap.dev.css` (fonte
única, SPEC design/004) e injeta num `<style type="text/tailwindcss">`, como os exemplos da skill
`componentes-frontend`.

- Exige servidor com root na raiz do projeto (Live Server). Via `file://` o fetch é bloqueado.
- **Tokens ainda não existentes** vão em `script[type="text/css"]` inerte e são **concatenados ao tema
  pelo loader dentro do MESMO bloco `text/tailwindcss`**. Bloco separado é processado sem o `@theme`
  do tema: as escalas `agua`/`rocha`/`madeira`/`sakura` viram "unknown utility class" no `@apply` e a
  folha inteira cai.
- **`@apply` só aceita utility.** Classe de `@layer components` — `.card-well`, `.glass-panel`,
  `.btn-onsen` — **não** é utility, nem estando no mesmo arquivo: `@apply card-well` derruba a folha
  do mesmo jeito, e o sintoma é a página abrir com o CSS pela metade. Peça do tema se **compõe no
  HTML** (`class="card-well quadro-glifo"`), nunca dentro do `@apply`.

---

## O fundo da página: o oficial, nunca um novo

Toda tela que **não é a home** roda sobre o **fundo da área administrativa** — a ortofoto
pré-gerada em tons de cinza, à deriva, sob a lente de água (SPEC design/010). O mock **não recria
esse fundo**: ele monta os mesmos partials que a aplicação usa — `templates/mapping/_mapa_admin.html`
e os que ele inclui (`_glifos_fundo.html`, `_fundo_ortofoto.html`, `_controle_fundo.html`) — mais o
`static/src/js/ui/controle_fundo.js`, por um módulo só:

```html
<!-- Fundo da área administrativa: os partials e o módulo da própria aplicação. -->
<script type="module">
  import { montarFundoAdmin } from "/.claude/skills/mock/examples/fundo-admin.js";
  montarFundoAdmin();
</script>
```

O conteúdo do mock fica **acima** dele, num `<div class="relative z-10">` — o fundo é `fixed` em
`z-0`/`z-[1]`.

**O fundo vem com o seu controle.** O `.fundo-controle` (liga/desliga, trocar, velocidade) é parte
do partial e aparece `fixed` no canto inferior direito, em `z-20`: não é sobra de mock nem peça a
demonstrar — é o produto. Não coloque conteúdo do mock embaixo dele, e não copie a molécula para o
arquivo só para "mostrar o fundo funcionando".

Nada além dessas linhas: nem as camadas da lente copiadas no `<body>`, nem o canvas da ortofoto
remontado à mão. Leaflet **não entra** num mock administrativo — o fundo deixou de ser mapa vivo
quando a ortofoto passou a ser pré-gerada. O `examples/fundo-admin.js` desta skill é o **único**
lugar em que um mock fala do fundo, e o que ele guarda é só o que o Django resolveria — o sorteio
da ortofoto e o `{% static %}` que o `fetch` cru do template não expande.

*Por quê:* fundo copiado é fundo que envelhece. Enquanto cada mock trazia as suas cinco camadas e o
seu `L.map`, uma troca no fundo do produto — como a dos tiles públicos pela ortofoto, e depois a do
WMS ao vivo pelo PNG pré-gerado — deixava para trás a coleção inteira de mocks, cada um provando um
design sobre um fundo que não existe mais.

A **home** é a exceção: ali o mapa é o produto, com as bases e a geometria do resultado — veja
`examples/mock_ui.html` da skill `componentes-frontend`. É o único mock que carrega Leaflet.

**O fundo é a exceção de si mesmo.** Quando o assunto da SPEC **é o próprio fundo** (design/010), o
mock não pode importá-lo pronto — a peça em julgamento é ela. Aí o arquivo monta o canvas e a
molécula do controle no próprio HTML e pode trazer uma seção de **andaime** (calibragem: escolher
ponto, amplitude, período) que não vai para o produto e é marcada como tal. Fora desse caso, andaime
não existe.

---

## O mock implementa Atomic Design — não é rascunho de tela

**Mock não é wireframe nem "tela desenhada em HTML".** Ele é o design system em exercício, e obedece
ao Atomic Design da skill `componentes-frontend` (§2 dela) **desde o primeiro rascunho**:

- **As seções por camada são obrigatórias, nesta ordem:** tokens → átomos → moléculas → organismos →
  tela montada. A página mostra cada camada separadamente **antes** da tela, porque o que se aprova é
  a peça reutilizável, não o arranjo dela numa tela. **Camada sem peça nova é omitida** — não se deixa
  seção vazia escrito "nenhum". A **tela montada** aparece sempre.
- **Cada nível é composição do nível imediatamente inferior.** Organismo que contém marcação solta em
  vez de moléculas já existentes está errado, mesmo que a tela pareça certa.
- **Nada de CSS ad hoc.** Toda pele nova é classe no `@layer components` com `@apply` **só de
  utilities**. Cor, sombra, blur, espaçamento ou tipografia fora dos tokens reprova o mock, por mais
  bonita que esteja a tela.
- **Peça que já existe é reutilizada, não redesenhada.** Antes de criar, confira o styleguide.

## JS de interface: pergunte, não faça malabarismo

O §3.1 do CLAUDE.md veda **JS modelando domínio** — estado de aplicação no cliente, regra de negócio,
UI montada a partir de JSON. Ele **não** veda três linhas de JS para o estado visual de um controle.

**Se o estado de interface sai simples em JS e só sai complexo em CSS — `:has()` encadeado, `checkbox`
escondido, seletor irmão frágil —, pare e pergunte ao usuário.** Ele aprova. Refazer CSS acrobático
cinco vezes custa mais que a linha de JS que resolvia de primeira.

CSS continua sendo a preferência **quando resolve simples**: o `checkbox` + `:has()` já usado no
projeto é bom onde está. O que muda é que a dificuldade vira **pergunta**, não mais CSS.

Segue vedado, sem pergunta: estado de domínio no cliente, UI montada a partir de JSON, validação que
decide, e qualquer persistência.

## O que o mock precisa mostrar

Cada peça nova **nos seus estados**, na condição real de uso — sobre o mapa vivo ou sobre o canvas
administrativo, nunca sobre fundo chapado:

- vazio × preenchido;
- fechado × aberto;
- criar × editar;
- e o **estado de falta**, quando existir: lista sem candidatos, unidade sem titular, resultado vazio.
  Campo em branco lê-se como "ainda não carregou" — o estado de falta é peça, não ausência.

---

## Template do mock

Ponto de partida obrigatório. Substitua `<épico>`/`<nº>` e omita as seções de camada sem peça nova.

```html
<!DOCTYPE html>
<html lang="pt-BR" data-theme="dimap">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SPEC <épico>/<nº> — <título> (mock de validação)</title>

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&family=Roboto+Mono:wght@400;500;700&display=swap" rel="stylesheet">

  <!-- Fundo da área administrativa: os partials e o módulo da própria aplicação, nunca recriados.
       Sem Leaflet: a ortofoto é pré-gerada (SPEC design/010), não mapa vivo. -->
  <script type="module">
    import { montarFundoAdmin } from "/.claude/skills/mock/examples/fundo-admin.js";
    montarFundoAdmin();
  </script>

  <link href="https://cdn.jsdelivr.net/npm/daisyui@5.7.4" rel="stylesheet" type="text/css" />
  <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>

  <!-- Tema (fonte única, SPEC design/004) + peças desta SPEC no MESMO bloco text/tailwindcss.
       Servir com root na RAIZ do projeto (Live Server); via file:// o fetch é bloqueado. -->
  <script>
    fetch("/static/src/tema-dimap.dev.css")
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.text(); })
      .then((css) => {
        const s = document.createElement("style");
        s.type = "text/tailwindcss";
        s.textContent = css + "\n" + document.getElementById("tokens-spec").textContent;
        document.head.appendChild(s);
      })
      .catch(() => (document.body || document.documentElement).insertAdjacentHTML(
        "afterbegin",
        "<p style='padding:1rem;color:#b00;font-family:monospace'>tema-dimap.dev.css não carregou — sirva a RAIZ do projeto.</p>"));
  </script>

  <!-- Peças desta SPEC, ainda fora do tema. Inerte, concatenado pelo loader acima.
       O que já está no tema NÃO se repete aqui. -->
  <script type="text/css" id="tokens-spec">
    @layer components {
      /* .<classe-nova> — <camada a que pertence> */
      .classe-nova { @apply /* só utilities */; }
    }
  </script>
</head>

<body class="min-h-screen">
  <!-- O fundo é montado no topo do <body> pelo módulo do <head>; o conteúdo fica acima dele. -->
  <div class="relative z-10">
    <h1>SPEC <épico>/<nº> — mock de validação</h1>

    <!-- 1 · TOKENS — omitir se nenhum token novo -->
    <section id="tokens">
      <!-- amostras do token novo: escala, cor, raio, sombra -->
    </section>

    <!-- 2 · ÁTOMOS — omitir se nenhum átomo novo -->
    <section id="atomos">
      <!-- cada átomo novo, nos seus estados -->
    </section>

    <!-- 3 · MOLÉCULAS — omitir se nenhuma molécula nova -->
    <section id="moleculas">
      <!-- composta pelos átomos acima; cada estado no seu bloco -->
    </section>

    <!-- 4 · ORGANISMOS — omitir se nenhum organismo novo -->
    <section id="organismos">
      <!-- composto pelas moléculas acima, sem marcação solta -->
    </section>

    <!-- 5 · TELA MONTADA — sempre presente -->
    <section id="tela">
      <!-- na condição real de uso: sobre o mapa vivo ou o canvas administrativo.
           Aqui entram os estados da tela inteira, um bloco por estado. -->

      <!-- página: <app>/<template>.html -->
      <!-- partial: <app>/partials/_<peca>.html — <gatilho HTMX, se for alvo de swap> -->
      <!-- /partial -->
      <!-- fica na página: <por quê em uma oração> -->
    </section>
  </div>
</body>
</html>
```

---

## Comentários no mock: só de interface

**O mock não é a SPEC em HTML.** O comentário dentro do arquivo serve a **duas coisas, e só essas**:

1. **demarcar camada e peça** — `<!-- 3 · Moléculas -->`, `<!-- .campo-onsen -->`;
2. **nomear o estado** que o bloco mostra — `<!-- aberto -->`, `<!-- estado: sem candidatos -->`;
3. **marcar o recorte de partials na tela montada** — ver abaixo.

### O recorte de partials se anota na tela montada

A tela montada diz **o que vira partial e o que fica na página**, com o caminho previsto. É o que
permite implementar lendo o mock, em vez de redecidir o recorte na hora:

```html
<!-- página: unidades/unidade.html -->
<main>
  <!-- partial: unidades/partials/_identidade_unidade.html -->
  <header>…</header>
  <!-- /partial -->

  <!-- partial: unidades/partials/_secao_direcao.html — alvo de hx-swap ao designar substituto -->
  <section>…</section>
  <!-- /partial -->

  <!-- fica na página: só arranjo, nunca é trocado sozinho -->
  <footer>…</footer>
</main>
```

Partial que existe **porque é alvo de HTMX** diz o gatilho na mesma linha; partial que existe só por
reúso não precisa dizer nada além do caminho.

**Não entra no mock:**

- narrativa de **modelagem ou regra de negócio** — está na SPEC. Se for indispensável situar o leitor,
  vale uma **referência curta** (`<!-- as 4 respostas: §3 da SPEC -->`), nunca a explicação;
- **justificativa** de decisão — de domínio é Caveat da SPEC; de tela está na própria tela;
- explicação do que a **classe faz** — o `@apply` diz, e o CSS mora no tema;
- cópia de **condição de pronto** ou de user story.

*Por quê:* comentário de modelagem no mock cria uma segunda fonte da mesma decisão, que diverge da SPEC
na primeira mudança — e engorda o arquivo que mais precisa ser relido a cada rodada de ajuste. O que se
aprova ali é a tela; o resto tem dono.

---

## Iteração: ajuste fino só no mock

Enquanto o design não foi aprovado, **itera-se no mock e em nada mais**:

- A SPEC `.md` **não se reabre** a cada rodada visual — reconciliar prosa com uma tela que ainda vai
  mudar é queimar token à toa.
- Os **testes não se escrevem** ainda: vêm depois da aprovação visual.
- Relate o que mudou em prosa, na conversa — não no arquivo.

Única razão para reabrir a SPEC aqui: o mock mostrou que a **modelagem** está errada. Aí a correção é
no `.md`, com nova aprovação, antes de continuar o mock.

---

## Aprovado o mock, o porte é obrigatório — em dois lugares

Aprovação **não** é licença para copiar o HTML do mock para dentro dos templates. O que foi aprovado
vira patrimônio do design system, e isso são **dois destinos obrigatórios**, ambos na mesma entrega da
implementação:

1. **CSS base — `static/src/tema-dimap.dev.css`.** Os blocos de token do mock migram para lá **tal e
   qual**, na seção da camada a que pertencem. É a fonte única (SPEC design/004): enquanto o token
   viver só no mock, ele não existe para a aplicação.
2. **Styleguide — `.claude/skills/componentes-frontend/examples/design_system.html`.** Cada peça nova é
   renderizada lá, na seção da sua camada (2 · Átomos, 3 · Moléculas, 4 · Organismos). É o **contrato
   visual do projeto**: componente que não está no styleguide não é encontrável e será reinventado — o
   que o Atomic Design existe para impedir.

Só depois disso os templates da aplicação usam as classes. O que o mock **repete** de SPECs anteriores
não se porta de novo: já está no tema.

**O mock é protótipo: sem versão, sem changelog, sem congelamento.** Ele existe para **testar a
interface**, então mostra sempre a **versão mais recente** dela — edita-se no lugar quantas vezes o
feedback pedir. Mexer no mock **não gera linha no `changelog` nem bump de versão da SPEC**; o
histórico de quando a tela era outra é do git.

O mock **permanece** no `SPECS/`, ao lado da SPEC que serve: não é descartado depois da entrega. Mas
ele não é a fonte viva da peça — quem quiser **usar** o componente vai ao styleguide, que é o contrato
visual do projeto.

*Por quê:* o mesmo motivo do TDD (§9 do CLAUDE.md), aplicado ao que teste automatizado não alcança. O
teste torna a regra verificável antes do código; o mock torna o **design** verificável antes do código.
E o porte obrigatório é o que impede cada SPEC de interface inventar seu próprio HTML, com a coerência
visual dependendo de disciplina individual em vez de peça compartilhada (§3.4 do CLAUDE.md).

---

## Checklist do mock

- [ ] A skill `componentes-frontend` foi lida — nenhuma peça do styleguide foi reinventada.
- [ ] A modelagem já foi aprovada — o mock não começou antes do "ok" na SPEC `.md`.
- [ ] Arquivo em `SPECS/<epico>/NNN-mock-<slug>.html`, mesmo prefixo da SPEC.
- [ ] Carrega o tema por `fetch` de `static/src/tema-dimap.dev.css` — sem duplicar design system.
- [ ] Token novo (se houver) concatenado ao tema **no mesmo** bloco `text/tailwindcss`.
- [ ] Segue o **template**: seções por camada na ordem — tokens → átomos → moléculas → organismos —
      **antes** da tela montada, que está sempre presente. Camada sem peça nova foi **omitida**, não
      deixada vazia.
- [ ] Cada nível composto pelo nível imediatamente inferior; nenhuma marcação solta dentro de organismo.
- [ ] Nenhum CSS ad hoc; pele nova só em `@layer components` com `@apply` de utilities.
- [ ] Peça nova mostrada em **todos** os seus estados, inclusive o estado de falta.
- [ ] Renderizado sobre a condição real de uso, não sobre fundo chapado — o fundo administrativo
      vem do `examples/fundo-admin.js` desta skill, sem nenhuma camada de lente, canvas de ortofoto
      ou Leaflet no arquivo.
- [ ] A tela montada **anota o recorte de partials** — `partial:` com caminho previsto, `fica na
      página:` no que não é, e o gatilho HTMX quando o partial existe para ser trocado.
- [ ] **Comentários só de interface** — camada, peça e estado. Nenhuma narrativa de modelagem, regra de
      negócio ou justificativa; no máximo uma referência curta à SPEC.
- [ ] Aprovado: tokens portados para `static/src/tema-dimap.dev.css` e peças renderizadas no styleguide
      — antes de qualquer template da aplicação usar as classes.
