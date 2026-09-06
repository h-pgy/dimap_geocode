---
spec: user_admin/007
versao: v2
atualizado_em: 2026-08-05
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: registra que os quatro testes levam o marker `banco`, não dois — a página de criar já monta
    os selects de unidade e cargos a partir das tabelas, então nem ela renderiza sem Postgres
    (ver Patch 001)
---

# SPEC user_admin/007 — Área administrativa: peças de formulário e fundo à deriva

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como administrador da plataforma, quero que as telas de cadastro (servidor, unidade e o que vier
depois) tenham as peças de formulário que faltam no design system — upload de arquivo, escolha de
cor, imagem de perfil em tamanho grande — e um fundo próprio da área administrativa, para que cada
tela nova seja montagem de peças existentes e não invenção de HTML.

## Critérios de aceite

- [ ] A área administrativa tem **fundo próprio**: mapa Leaflet com os tiles públicos padrão em
      **preto e branco**, sem nenhuma chamada ao GeoSampa, **à deriva lenta e contínua** e sem
      interação, sob a **mesma lente do mapa principal** (tinta de água, vinheta, desfoque de borda,
      luz fria). A deriva não roda com `prefers-reduced-motion: reduce` nem com a aba oculta.
- [ ] O conteúdo administrativo **rola sobre o fundo fixo** — a viewport travada do `base.html`
      (que existe porque a página do produto é o mapa) não se aplica aqui.
- [ ] Existe um **campo de upload em poço rebaixado**: o poço traz ícone, instrução e formatos
      aceitos, acende no hover/foco (sem mudar de cor) e o nome do arquivo escolhido aparece sem
      JavaScript. Soltar um arquivo sobre o poço funciona.
- [ ] Existe um **seletor de cor em disco de vidro**: o gatilho mostra a cavidade da cor atual e,
      aberto, exibe as cavidades de tinta **dispostas em círculo** em torno de um poço central que
      espelha a cor selecionada; a cavidade escolhida se marca com anel branco e brilho ciano. A
      escolha é um `radio` nativo — nenhum JavaScript participa.
- [ ] Existe a molécula de **imagem de perfil em versão grande**: foto ou avatar de iniciais, o que
      o domínio resolver, em moldura de vidro com anel na **cor da unidade**; na edição do servidor
      ela fica **à esquerda do nome**.
- [ ] O **formulário de perfil** é um organismo composto só por essas peças: cabeçalho de
      identidade, seções em poço (identificação, lotação, foto) e rodapé com ação primária e
      secundária — sem cor, sombra, espaçamento ou tipografia fora dos tokens.
- [ ] As páginas de **criar** e **editar** servidor renderizam esse organismo sobre o fundo
      administrativo, e a de criar não mostra a imagem grande (não há perfil ainda).
- [ ] O design foi **aprovado no mock** que acompanha esta SPEC antes de qualquer código de
      aplicação.
- [ ] Aprovado o mock, cada peça nova está **nos dois destinos obrigatórios**: os tokens em
      `static/src/tema-dimap.dev.css` (fonte única) e os componentes renderizados no styleguide
      `.claude/skills/componentes-frontend/examples/design_system.html`, cada um na seção da sua
      camada — só então os templates da aplicação usam as classes.

## Contexto e decisões de arquitetura

Iteração de **interface**: tokens do design system, partials e views de leitura. Nenhum model,
nenhuma regra nova — a escolha entre foto e avatar já é `resolver_imagem_perfil` (SPEC
`user_admin/006`), e a paleta já é `CorUnidade` (SPEC `user_admin/005`).

**Fundo próprio para o admin.** O mapa do produto é o WMS do GeoSampa e carrega semântica
territorial; na área administrativa não há território algum a mostrar. Tiles públicos em preto e
branco dão a mesma pele sem gastar requisição no GeoSampa e sem sugerir que aquele mapa significa
alguma coisa. A lente do §6 é copiada tal e qual: a identidade visual do produto não muda de seção
para seção.

**A deriva é utilitário de Leaflet, não animação de UI.** Reenquadramento contínuo a partir de um
centro fixo, amplitude pequena e ciclo longo, com o canvas em `pointer-events-none`: a cena fica
viva sem convidar ao arrasto. Pausa em `prefers-reduced-motion` e com a aba oculta — movimento
perpétuo é custo de bateria e gatilho vestibular.

**Cores dinâmicas entram por variável CSS, não por classe montada.** A cor da unidade e as tintas da
paleta vêm do banco como slug (`agua-700`); `ring-{{ cor }}` no template é classe que o Tailwind não
enxerga no `@source` e some no build de produção. O app resolve slug → hex na borda (é o mesmo mapa
que `resolver_imagem_perfil` já exige para pintar o SVG) e escreve `--cor-unidade` / `--tinta` no
`style` do elemento; os tokens leem a variável.

**A paleta é fechada, então o espelhamento cabe em CSS.** São oito tons: o poço central e o swatch
do gatilho refletem o `radio` marcado por `:has()`, uma regra por tom no design system. Sincronizar
isso em JavaScript seria estado de UI no navegador, que o §7.2 não admite.

**O que o poço de upload não faz.** Prévia do arquivo recém-escolhido e realce de arraste exigiriam
`FileReader` e listeners de `dragover` — JavaScript de estado. O poço abraça um `file-input` nativo
(o próprio navegador escreve o nome do arquivo) e, na edição, a prévia mostrada é a **foto já
gravada**, servida pelo servidor. Soltar arquivo sobre o input continua funcionando por
comportamento nativo, só sem realce.

**Rotas de leitura.** Esta iteração renderiza as páginas; gravar servidor é ato administrativo e
entra com autenticação, autorização e registro na SPEC seguinte (§3.5) — ver "Fora de escopo".

## Mock de validação

`SPECS/user_admin/007-mock-area-administrativa.html` — a SPEC só é aprovável com ele: descrição em
prosa de vidro, poço e disco não é validável. O mock roda o fundo à deriva de verdade, declara os
tokens propostos num bloco `text/tailwindcss` e renderiza cada peça nos seus estados (poço vazio ×
com foto gravada, paleta fechada × aberta, avatar por foto × por iniciais, formulário de criar ×
editar). Exige servidor com root na raiz do projeto (Live Server) — via `file://` o fetch do tema é
bloqueado.

O mock é o design system em exercício, não um rascunho de tela: está organizado em **Atomic Design**
(tokens → átomos → moléculas → organismos, em seções separadas), cada nível composto pelo inferior,
sem CSS ad hoc.

Aprovado o design, o porte é obrigatório e vai a **dois destinos**, na mesma entrega: os blocos de
token migram **tal e qual** para `static/src/tema-dimap.dev.css` (fonte única — enquanto o token
viver só no mock, ele não existe para a aplicação) e cada peça é renderizada no styleguide
`.claude/skills/componentes-frontend/examples/design_system.html`, na seção da sua camada — sem
isso o componente não é encontrável e será reinventado na próxima tela. Só então os templates usam
as classes. O mock permanece no `SPECS/` como o artefato aprovado da iteração.

## Peças de referência a compor

- `@static/src/tema-dimap.dev.css` → `.glass-panel`, `.card-well`, `.input-glass`, `.btn-onsen`,
  `.btn-glass`, `.text-overline`, `.icon-bubble`, `.transition-glass`: os novos tokens compõem esse
  vocabulário, não inauguram outro.
- `templates/mapping/_mapa_fullscreen.html` → as quatro camadas da lente (tinta de água, vinheta,
  desfoque de borda, luz fria): copiadas tal e qual sob o canvas administrativo.
- `@static/src/js/mapa/` → padrão de módulo ES do mapa (função pura + `init` que registra o
  callback uma única vez). `criar_mapa.js` fica intocado: seus limites de zoom e controles são do
  produto, não do fundo.
- `@services/domain/avatar` → `resolver_imagem_perfil`: decide foto × avatar de iniciais a partir de
  nome, sobrenome, cores já resolvidas e URL da foto.
- `apps/user_admin/models` → `Perfil` (com `cor_unidade`), `CorUnidade` (os oito tons que a paleta
  oferece), `Unidade`, `CargoBase`, `CargoComissao`.
- `@.claude/skills/componentes-frontend/examples/design_system.html` → styleguide onde cada peça
  nova se registra.

## Snippets sugeridos

```css
/* tema-dimap.dev.css — tokens novos. @apply só de utilities; a cor variável entra por CSS var. */

/* Casca da área administrativa: fundo fixo, conteúdo rolando. */
.admin-shell { @apply absolute inset-0 z-10 overflow-y-auto overscroll-contain; }

/* Poço de upload: o card-well com aresta tracejada; acende no hover/foco, não muda de cor. */
.upload-well {
  @apply rounded-2xl bg-white/30 border border-dashed border-white/60 shadow-[inset_0_2px_6px_rgba(7,58,84,0.15)] flex flex-col items-center gap-3 p-6 text-center transition-all duration-300;
}
.upload-well:hover,
.upload-well:focus-within { @apply bg-white/45 border-agua-500/60 shadow-[inset_0_2px_6px_rgba(7,58,84,0.15),0_0_22px_rgba(72,202,228,0.35)]; }

/* Cavidade de tinta: a tinta "molhada" vem em --tinta (hex resolvido na borda do app). */
.paint-well {
  @apply w-9 h-9 rounded-full border border-white/70 shadow-[inset_0_2px_5px_rgba(7,58,84,0.45),0_1px_0_rgba(255,255,255,0.6)] cursor-pointer transition-all duration-300 hover:scale-110;
  background-color: var(--tinta);
}
.paint-well:has(input:checked) { @apply scale-110 ring-2 ring-white/90 shadow-[inset_0_2px_5px_rgba(7,58,84,0.45),0_0_18px_rgba(72,202,228,0.85)]; }

/* Disco de vidro: as cavidades se distribuem pelo ângulo --a escrito no markup, então a paleta
   não depende de quantas cores existem. */
.palette-disc {
  @apply relative w-56 h-56 rounded-full backdrop-blur-[10px] bg-gradient-to-br from-white/65 via-white/45 to-white/30 border border-white/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_8px_32px_rgba(7,58,84,0.25),0_0_24px_rgba(72,202,228,0.25)];
}
.palette-disc .paint-well {
  @apply absolute top-1/2 left-1/2;
  transform: translate(-50%, -50%) rotate(var(--a)) translate(4.75rem) rotate(calc(-1 * var(--a)));
}
.paint-well-atual {
  @apply w-14 h-14 rounded-full border-2 border-white/80 shadow-[inset_0_3px_8px_rgba(7,58,84,0.5)];
}
/* Uma regra por tom: o poço central e o swatch do gatilho espelham o radio marcado. */
.palette-field:has(input[value="agua-700"]:checked)    .paint-well-atual { background-color: #0077b6; }
.palette-field:has(input[value="agua-800"]:checked)    .paint-well-atual { background-color: #023e8a; }
/* … demais tons de CorUnidade … */

/* Controles de vidro que faltavam: mesma receita do .input-glass, aplicada a select e file. */
.select-glass {
  @apply w-full rounded-xl bg-white/45 border-white/60 text-base-content backdrop-blur-[10px] transition-all duration-300 focus:bg-white/60 focus:border-agua-500 focus:outline-none focus:shadow-[0_0_0_3px_rgba(0,150,199,0.2),0_0_20px_rgba(72,202,228,0.35)];
}
.file-input-glass {
  @apply w-full rounded-xl bg-white/45 border-white/60 text-base-content backdrop-blur-[10px] transition-all duration-300 focus:outline-none focus:border-agua-500;
}

/* Campo de formulário: rótulo overline + controle + linha de ajuda. */
.form-field      { @apply flex flex-col gap-1.5; }
.form-field-hint { @apply text-xs text-base-content/60; }

/* Moldura da imagem de perfil: o anel é a cor da unidade, via --cor-unidade. */
.avatar-glass {
  @apply rounded-full overflow-hidden bg-white/40 border-2 border-white/70 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_8px_28px_rgba(7,58,84,0.28),0_0_22px_rgba(72,202,228,0.25)];
  outline: 3px solid var(--cor-unidade);
  outline-offset: 3px;
}
```

```html
<!-- Molécula: campo de upload em poço rebaixado -->
<div class="flex flex-col gap-1.5">
  <span class="text-overline">Foto do servidor</span>
  <label class="upload-well cursor-pointer">
    <span class="icon-bubble w-12 h-12 bg-agua-500/15 border-agua-600/30 text-agua-700">
      <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 16V4m0 0L8 8m4-4l4 4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2"/></svg>
    </span>
    <span class="text-sm font-medium">Arraste a foto ou clique para escolher</span>
    <input type="file" name="foto" accept="image/*" class="file-input file-input-ghost file-input-sm bg-white/45 border-white/60" />
    <span class="text-xs text-base-content/60">JPG ou PNG, até 2 MB</span>
  </label>
</div>
```

```html
<!-- Molécula: seletor de cor (paleta de aquarela) -->
<div class="palette-field dropdown dropdown-bottom flex flex-col gap-1.5">
  <span class="text-overline">Cor da unidade</span>
  <div tabindex="0" role="button" class="btn btn-ghost btn-glass w-fit gap-3 px-3">
    <span class="paint-well paint-well-atual w-7 h-7 pointer-events-none"></span>
    <svg class="w-4 h-4 icon-glow" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>
  </div>
  <div tabindex="0" class="dropdown-content z-30 mt-2">
    <div class="palette-disc">
      <span class="paint-well-atual absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"></span>
      {% for tom in tons %}
        <label class="paint-well" style="--a: {{ tom.angulo }}deg; --tinta: {{ tom.hex }}" title="{{ tom.rotulo }}">
          <input type="radio" name="cor" value="{{ tom.slug }}" class="sr-only" {% if tom.selecionado %}checked{% endif %} />
        </label>
      {% endfor %}
    </div>
  </div>
</div>
```

```html
<!-- Molécula: imagem de perfil grande, à esquerda do nome (edição) -->
<div class="flex items-center gap-5">
  <div class="avatar-glass w-28 h-28 shrink-0" style="--cor-unidade: {{ cor_unidade_hex }}">
    {% if imagem.tipo == "foto" %}
      <img src="{{ imagem.valor }}" alt="Foto de {{ perfil.nome }}" class="w-full h-full object-cover" />
    {% else %}
      {{ imagem.valor|safe }}
    {% endif %}
  </div>
  <div class="min-w-0">
    <h1 class="text-2xl font-bold tracking-tight text-madeira-700 truncate">{{ perfil.nome }} {{ perfil.sobrenome }}</h1>
    <p class="text-code text-sm mt-1">RF {{ perfil.rf }}</p>
    <div class="flex flex-wrap gap-2 mt-2">
      <span class="badge badge-info badge-soft">{{ perfil.unidade.sigla }}</span>
      <span class="badge badge-ponto badge-sm">{{ perfil.cargo_base }}</span>
    </div>
  </div>
</div>
```

```js
// static/src/js/mapa/deriva.js — utilitário de Leaflet (§7.2): reenquadra devagar, para quando
// a aba some ou quando o usuário pediu menos movimento.
const PERIODO_MS = 150000;
const AMPLITUDE_GRAUS = 0.008;
const INTERVALO_FRAME_MS = 50;

export function derivarMapa(mapa, centro, zoom) {
  const reduzido = window.matchMedia("(prefers-reduced-motion: reduce)");
  let ultimoFrame = 0;
  function passo(agora) {
    requestAnimationFrame(passo);
    if (document.hidden || reduzido.matches) return;
    if (agora - ultimoFrame < INTERVALO_FRAME_MS) return;
    ultimoFrame = agora;
    const fase = (agora % PERIODO_MS) / PERIODO_MS * 2 * Math.PI;
    const lat = centro[0] + AMPLITUDE_GRAUS * Math.sin(fase);
    const lng = centro[1] + AMPLITUDE_GRAUS * Math.sin(2 * fase) / 2;
    mapa.setView([lat, lng], zoom, { animate: false });
  }
  requestAnimationFrame(passo);
}
```

```html
<!-- Organismo: fundo administrativo (mesma lente do mapa principal, tiles públicos em P&B) -->
<div id="map-admin" class="fixed inset-0 z-0 pointer-events-none grayscale brightness-[1.05] contrast-[0.95]"></div>
<div class="fixed inset-0 z-[1] pointer-events-none mix-blend-multiply bg-[#bfeaf5]/60"></div>
<div class="fixed inset-0 z-[1] pointer-events-none bg-[radial-gradient(ellipse_at_center,transparent_55%,rgba(0,119,182,0.25)_100%)]"></div>
<div class="fixed inset-0 z-[1] pointer-events-none backdrop-blur-[1.5px] [mask-image:radial-gradient(ellipse_at_center,transparent_45%,black_95%)]"></div>
<div class="fixed inset-0 z-[1] pointer-events-none bg-[radial-gradient(ellipse_at_50%_38%,rgba(255,255,255,0.18),transparent_60%)]"></div>
```

```html
<!-- Organismo: formulário do servidor (criar e editar compartilham o mesmo esqueleto) -->
<div class="admin-shell">
  <div class="max-w-3xl mx-auto px-4 py-24">
    <div class="glass-panel p-6 sm:p-8 flex flex-col gap-6">
      {% include "user_admin/partials/_identidade_perfil.html" %}   {# só na edição #}

      <div class="card-well p-5 flex flex-col gap-4">
        <p class="text-overline">Identificação</p>
        <div class="grid sm:grid-cols-2 gap-4">…</div>       {# RF, nome, sobrenome #}
      </div>

      <div class="card-well p-5 flex flex-col gap-4">
        <p class="text-overline">Lotação</p>
        <div class="grid sm:grid-cols-2 gap-4">…</div>       {# unidade, cargo base, cargo em comissão #}
      </div>

      {% include "user_admin/partials/_campo_upload_foto.html" %}

      <div class="flex justify-end gap-3 pt-2">
        <button type="button" class="btn btn-ghost btn-glass">Cancelar</button>
        <button type="submit" class="btn btn-onsen">Salvar servidor</button>
      </div>
    </div>
  </div>
</div>
```

## Fora de escopo

- **Gravar** servidor ou unidade: o POST é ato administrativo e entra com autenticação,
  autorização por perfil e registro da execução (§3.5) na SPEC seguinte. Aqui as páginas
  renderizam e o `submit` não tem destino.
- Autenticação, login e proteção das rotas — mesma SPEC do item acima.
- Formulário de **unidade**: o seletor de cor nasce aqui como molécula registrada no styleguide,
  mas a tela que o usa vem depois.
- Prévia local do arquivo escolhido e realce de arraste no poço (exigiriam JS de estado).
- Corte/enquadramento da foto enviada.
- Índice/listagem de servidores e navegação da área administrativa.

## Testes (TDD)

O que é visual se valida no mock (estados, viewports, `prefers-reduced-motion`), não em teste
automatizado. Os testes abaixo fixam o **contrato HTTP/partial** das páginas. Dois deles tocam o
banco (perfil, unidade e cargos são obrigatórios para montar a página de edição) e carregam o
marker `banco`, declarado no front-matter.

- `test_pagina_criar_perfil_renderiza_o_formulario` — GET devolve 200 com as seções de
  identificação e lotação e o poço de upload, e **sem** a imagem grande de perfil.
- `test_pagina_admin_nao_carrega_o_wms_do_geosampa` — a página administrativa traz o canvas de
  deriva e nenhuma configuração de WMS do GeoSampa.
- `test_editar_perfil_sem_foto_mostra_avatar_de_iniciais` (`banco`) — o cabeçalho traz o SVG de
  iniciais na cor da unidade do servidor.
- `test_editar_perfil_com_foto_mostra_a_foto` (`banco`) — a mesma molécula, no ramo da foto,
  aponta para a URL do arquivo gravado.

## Patches

### Patch 001 (v2) — os quatro testes levam o marker `banco`

- [x] **Aplicado**

**Sintoma.** A SPEC previa dois testes na suíte padrão (`test_pagina_criar_perfil_renderiza_o_formulario`
e `test_pagina_admin_nao_carrega_o_wms_do_geosampa`) e dois com o marker `banco`. Os dois primeiros
não rodam sem Postgres: ambos fazem `GET` na página de **criar** servidor, e ela monta os selects de
unidade, cargo base e cargo em comissão a partir das tabelas — o template itera os querysets e o
`pytest-django` bloqueia o acesso ao banco em teste sem `django_db`.

**Correção.** Os quatro testes levam `banco`. A alternativa — testar as duas primeiras asserções
por `render_to_string` com contexto sintético — trocaria o contrato HTTP que a SPEC quer fixar
("GET devolve 200") por um contrato de template, e deixaria a rota e a view fora do teste.

O `markers_obrigatorios` do front-matter não muda: já era `[banco]`.

### Patch 002 (v2) — a rota de mídia em dev entra aqui

- [x] **Aplicado**

A SPEC `user_admin/006` deixou "a rota que serve o arquivo de mídia" para o front-end do épico, que
é esta SPEC: sem ela o `<img>` da foto gravada aponta para uma URL que devolve 404 e o critério de
aceite da imagem de perfil não se verifica na tela. `config/urls.py` passa a servir `MEDIA_URL` pelo
`django.conf.urls.static.static` **apenas com `DEBUG`** — em produção o arquivo de mídia é do
servidor web, não do Django.
