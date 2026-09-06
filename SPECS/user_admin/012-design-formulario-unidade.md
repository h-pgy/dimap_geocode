---
spec: user_admin/012
versao: v1
atualizado_em: 2026-08-06
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC user_admin/012 — Formulário de unidade: página própria e modal reaproveitável

- [x] **Testes (TDD) escritos** <!-- marque [x] e ponha testes_tdd: true quando os testes existirem e falharem; sem isso NÃO se escreve o código -->
- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como administrador da plataforma, quero cadastrar unidade tanto numa tela própria quanto num modal
aberto de dentro do cadastro de servidor, para não trocar de contexto quando descubro, no meio do
cadastro de uma pessoa, que a unidade dela ainda não existe no sistema.

## Critérios de aceite

- [x] Existe o **átomo botão de criação inline**: círculo de vidro com o sinal `+` em tinta ciana,
      altura casada com a do campo ao lado, que acende no hover. É o **mesmo** botão para qualquer
      "criar agora o que falta no catálogo" (unidade hoje; cargo, tipo de unidade, o que vier).
- [x] Existe a **molécula campo com criação inline**: rótulo overline + controle de vidro ocupando a
      linha + o botão acima, alinhados. Ela substitui o campo de unidade na lotação do servidor.
- [x] Existe o **modal de vidro**: a caixa é placa de **gelo espesso** (atrás dela há um formulário
      com tinta escura, não a água do mapa), e o fundo **embaça em vez de escurecer** — nenhum véu
      preto. Abre e fecha por `checkbox` nativo, pelo backdrop e pelo botão de cancelar, **sem
      JavaScript**.
- [x] Os campos de seleção deste formulário usam o **campo de seleção de vidro** da SPEC 011 —
      inclusive dentro do modal, e com a **página nova carregando o módulo** como a de servidor já
      faz — e a escolha da unidade superior dispara o `change` que busca a cor sugerida.
- [x] O **formulário de unidade** é um organismo com três seções em poço — identificação (nome,
      sigla), hierarquia (tipo, unidade superior) e identidade visual (a cor, no **disco de paleta
      que já existe**) — e os **mesmos campos** aparecem na página própria e dentro do modal, do
      mesmo partial.
- [x] A **página de criar unidade** renderiza esse organismo sobre o fundo administrativo, no mesmo
      esqueleto da página de servidor.
- [x] A **página de criar servidor** traz o botão de criação ao lado do campo de unidade e o modal
      com o formulário de unidade — e o modal fica **fora** do formulário do servidor: formulário
      dentro de formulário é HTML inválido.
- [x] Escolher a **unidade superior** traz a **cor sugerida**: o campo de cor é trocado por HTMX com
      o tom do pai já marcado; sem pai, volta a `agua-700`.
- [x] O design foi **aprovado no mock** que acompanha esta SPEC antes de qualquer código de
      aplicação.
- [x] Aprovado o mock, cada peça nova está nos **dois destinos obrigatórios** — tokens em
      `static/src/tema-dimap.dev.css` (fonte única) e componentes renderizados no styleguide
      `.claude/skills/componentes-frontend/examples/design_system.html`, cada um na seção da sua
      camada — **e os templates da aplicação usam essas classes**, sem marcação de utilities soltas
      resolvendo pele.
- [x] As **rotas de GET existem e renderizam na aplicação**: a página de unidade, a página de
      servidor com o modal e a troca do campo de cor são navegáveis no `runserver`.

## Contexto e decisões de arquitetura

Iteração de **interface**: tokens do design system, partials e views de leitura. Nenhum model novo —
`Unidade`, `TipoUnidade`, `CorUnidade` e `Unidade.cor_sugerida` já existem (SPECs `user_admin/001`,
`003` e `005`), e o disco de paleta nasceu na SPEC `007` justamente para esta tela.

**Depende da SPEC `user_admin/011`**, que precisa estar implementada antes: o gelo espesso da caixa do
modal e o campo de seleção de vidro usado aqui (inclusive dentro do modal) são dela.

**Um partial de campos, duas molduras.** O que se compartilha entre a página e o modal são as três
seções de campo; o `<form>`, o título e o rodapé são de quem inclui — o "cancelar" da página é
navegação e o do modal é fechar a placa. Enfiar essa diferença num `if` dentro do partial trocaria
duas molduras claras por uma peça que precisa saber onde está.

**O modal fica fora do formulário do servidor.** Formulário aninhado é HTML inválido e o navegador
descarta o interno. O gatilho é um `<label for>`, que alcança o modal em qualquer lugar do
documento, então a página do servidor termina com dois formulários irmãos.

**O modal usa o gelo espesso da SPEC 011.** Atrás dele há um formulário com tinta escura, não a água
do mapa: é o caso da regra *fino sobre o mapa, espesso sobre interface*. A placa **compõe**
`.glass-panel-thick` no HTML e o token daqui carrega só o que é do modal — recopiar a receita faria a
espessura divergir da SPEC que a define.

**A lista de seleção não precisa de exceção dentro do modal.** Ela vive na top layer e é posicionada
a partir do gatilho, reagindo à rolagem (SPEC 011) — então a placa, que rola e cria contexto de
empilhamento próprio, não a corta nem a soterra. Nada a fazer aqui além de compor.

**Modal sem JavaScript e sem véu escuro.** O `checkbox` nativo do daisyUI dá abrir/fechar sem estado
no navegador (§7.2), e o foco vem do **embaçamento** do fundo, na mesma língua da
`.cinematic-blur-layer` — escurecer é proibido pelo §6 do design system. O custo aceito é não fechar
com `Esc` (isso exigiria `<dialog>` + JS).

**Conteúdo do modal renderizado no include.** A página do servidor já monta catálogos no contexto;
acrescentar tipos de unidade ali custa uma consulta e dispensa rota e `hx-get` de abertura. Buscar o
formulário sob demanda seria justificável se ele fosse caro — não é.

**Cor sugerida pelo pai vem do servidor.** `Unidade.cor_sugerida` já é a regra; resolvê-la no
navegador exigiria o mapa slug → hex em JavaScript, que é estado de UI duplicado. O campo de cor é
um partial próprio e a troca dele é o alvo do `hx-get` disparado pelo select da unidade superior —
mesmo motivo pelo qual o hex nunca vira classe montada no template (SPEC `007`).

**Sem gravação.** O POST é ato administrativo — autenticação, autorização por perfil e registro da
execução (§3.5) — e é a SPEC seguinte, como a `007` fez para o servidor. Consequência prática: o
`submit` não tem destino e a unidade criada no modal **não** aparece no campo do servidor; isso é
swap fora de banda e vem junto do POST.

## Mock de validação

`SPECS/user_admin/012-mock-formulario-unidade.html` — a SPEC só é aprovável com ele. O mock roda o
fundo administrativo à deriva, declara os tokens propostos num `script[type="text/css"]` inerte que
o loader concatena ao tema **no mesmo bloco** `text/tailwindcss`, e está organizado em Atomic Design
(tokens → átomos → moléculas → organismos, em seções separadas). O modal abre de verdade, pelo
`checkbox`. Exige servidor com root na raiz do projeto (Live Server) — via `file://` o fetch do tema
é bloqueado.

Cada peça aparece nos seus estados: botão de criação em repouso e em hover, campo com criação, modal
fechado × aberto, e o campo de cor nos dois resultados da sugestão (sem pai → `agua-700`; com pai → o
tom do pai já marcado). O campo de seleção de vidro e o gelo espesso da SPEC 011 estão copiados no
mock apenas para ele rodar sozinho.

## Peças de referência a compor

- `@static/src/tema-dimap.dev.css` → `.glass-panel`, `.card-well`, `.input-glass`, `.select-glass`,
  `.btn-onsen`, `.btn-glass`, `.form-field`, `.form-field-hint`, `.text-overline`, `.admin-shell` e
  todo o vocabulário da paleta (`.palette-field`, `.palette-disc`, `.paint-well`,
  `.paint-well-atual`): os tokens novos compõem esse vocabulário, não inauguram outro.
- `templates/user_admin/perfil_form.html` e `templates/user_admin/partials/_secao_lotacao.html` → o
  esqueleto da página administrativa e o campo de unidade que recebe o botão de criação.
- `templates/mapping/_mapa_admin.html` + `apps/mapping/context.py` → `contexto_fundo_admin`: o fundo
  à deriva da área administrativa, reusado tal e qual.
- `apps/user_admin/models` → `Unidade` (com `cor_sugerida`), `TipoUnidade`, `CorUnidade`.
- `apps/user_admin/paleta.py` → `HEX_POR_COR` / `hex_da_cor`: a borda que resolve slug → hex; é dela
  que sai a lista de tons do disco.
- `apps/user_admin/context.py` → os catálogos dos selects e o padrão de contexto por página.
- `@apps/core/middleware.py` → `PydanticValidationMiddleware`: a rota do campo de cor valida o
  parâmetro por DTO, sem `try/except` na view.
- **SPEC `user_admin/011`** → o **campo de seleção de vidro** (`data-select-onsen` + o módulo
  `static/src/js/ui/select_onsen.js`) e o **gelo espesso** (`.glass-panel-thick` e primitivos): esta
  SPEC os consome, não os redefine.
- `@.claude/skills/componentes-frontend/examples/design_system.html` → styleguide onde cada peça
  nova se registra.

## Snippets sugeridos

```css
/* tema-dimap.dev.css — tokens novos. @apply só de utilities; important é sufixo no Tailwind 4. */

/* Átomo: botão de criação inline. Mesma receita de gelo do .btn-glass, em tinta ciana e no
   tamanho que casa com a altura do controle ao lado. */
.btn-criar-inline {
  @apply w-10 h-10 shrink-0 p-0 rounded-full backdrop-blur-[10px] bg-white/50 border border-white/60 text-agua-700 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_4px_16px_rgba(7,58,84,0.2)] transition-all duration-300;
}
.btn-criar-inline:hover {
  @apply bg-white/70 text-agua-600 shadow-[0_4px_20px_rgba(72,202,228,0.4)];
}

/* Molécula: linha do campo com criação — o controle estica, o botão não. O .select-onsen entra na
   conta porque, aprimorado o campo, quem ocupa a linha é a casca da SPEC 011. */
.form-field-inline-action { @apply flex items-center gap-2; }
.form-field-inline-action > :where(select, input, .select-onsen) { @apply flex-1 min-w-0; }

/* Modal de vidro: o fundo EMBAÇA (nunca escurece) e a caixa é o gelo espesso da SPEC 011, composto
   no HTML — aqui fica só o que é do modal. O bg-transparent! derruba o véu escuro e o base-100
   opaco do daisyUI. */
.modal-glass { @apply bg-transparent! backdrop-blur-[6px]; }
.modal-box-glass { @apply bg-transparent! max-h-[85vh] overflow-y-auto; }
```

```html
<!-- Molécula: campo com criação inline (o botão é <label>: alcança o modal fora do formulário) -->
<div class="form-field">
  <span class="text-overline">Unidade</span>
  <div class="form-field-inline-action">
    {# data-select-onsen é da SPEC 011 e o campo já chega marcado de lá: aqui ele só ganha o botão. #}
    <select name="unidade" class="select select-glass" data-select-onsen>
      {% for unidade in unidades %}
        <option value="{{ unidade.pk }}">{{ unidade.sigla }} · {{ unidade.nome }}</option>
      {% endfor %}
    </select>
    <label for="modal-nova-unidade"
           class="btn btn-circle btn-criar-inline tooltip tooltip-left"
           data-tip="Cadastrar unidade que falta">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14M5 12h14"/></svg>
    </label>
  </div>
  <span class="form-field-hint">Não achou a unidade? Cadastre sem sair desta tela.</span>
</div>
```

```html
<!-- Organismo: campos da unidade — o partial compartilhado pela página e pelo modal -->
<div class="card-well p-5 flex flex-col gap-4">
  <p class="text-overline">Identificação</p>
  <div class="grid sm:grid-cols-3 gap-4">…</div>          {# nome (2 colunas), sigla #}
</div>

<div class="card-well p-5 flex flex-col gap-4">
  <p class="text-overline">Hierarquia</p>
  <div class="grid sm:grid-cols-2 gap-4">
    <div class="form-field">
      <span class="text-overline">Tipo</span>
      <select name="tipo" class="select select-glass" data-select-onsen>…</select>
    </div>
    <div class="form-field">
      <span class="text-overline">Unidade superior</span>
      {# A cor nasce da unidade superior: quem sabe a regra é o servidor (Unidade.cor_sugerida). #}
      {# O HTMX segue ouvindo o próprio select: a casca da SPEC 011 escreve nele e dispara change. #}
      <select name="pai" class="select select-glass" data-select-onsen
              hx-get="{% url 'user_admin:cor_sugerida_unidade' %}"
              hx-trigger="change"
              hx-target="#campo-cor-unidade"
              hx-swap="outerHTML">
        <option value="">— sem unidade superior (raiz) —</option>
        …
      </select>
      <span class="form-field-hint">Só tipo marcado como raiz dispensa unidade superior.</span>
    </div>
  </div>
</div>

<div class="card-well p-5 flex flex-col gap-4">
  <p class="text-overline">Identidade visual</p>
  {% include "user_admin/partials/_campo_cor_unidade.html" %}
</div>
```

```html
<!-- Organismo: modal de unidade. Fica FORA do formulário do servidor — form aninhado é inválido. -->
<input type="checkbox" id="modal-nova-unidade" class="modal-toggle" />
<div class="modal modal-glass" role="dialog">
  <div class="modal-box glass-panel-thick modal-box-glass w-11/12 max-w-2xl p-6 sm:p-8">
    <form class="flex flex-col gap-6">
      <div>
        <h2 class="text-xl font-bold tracking-tight text-madeira-700">Nova unidade</h2>
        <p class="text-sm text-base-content/70 mt-1">A unidade cadastrada aqui fica disponível para a lotação do servidor.</p>
      </div>
      {% include "user_admin/partials/_campos_unidade.html" %}
      <div class="flex justify-end gap-3 pt-1">
        <label for="modal-nova-unidade" class="btn btn-ghost btn-glass">Cancelar</label>
        <button type="submit" class="btn btn-onsen">Salvar unidade</button>
      </div>
    </form>
  </div>
  <label class="modal-backdrop" for="modal-nova-unidade">Fechar</label>
</div>
```

```python
# apps/user_admin/schemas.py — o select da unidade superior manda "" quando é raiz.
def _vazio_para_nulo(valor: object) -> object:
    return None if valor == "" else valor


PaiOpcional = Annotated[int | None, BeforeValidator(_vazio_para_nulo)]


class SelecaoUnidadePai(BaseModel):
    pai: PaiOpcional = None
```

```python
# apps/user_admin/views.py — GET do campo de cor: o ValidationError é do middleware, não da view.
def cor_sugerida_unidade(request: HttpRequest) -> HttpResponse:
    selecao = SelecaoUnidadePai.model_validate(request.GET.dict())
    return render(request, TEMPLATE_CAMPO_COR, contexto_cor_sugerida(selecao.pai))
```

```python
# apps/user_admin/context.py
def contexto_cor_sugerida(pai_pk: int | None) -> dict[str, Any]:
    pai = Unidade.objects.filter(pk=pai_pk).first() if pai_pk else None
    # Instância não gravada só para não repetir aqui o default que o model já decide.
    return {"tons": tons_da_paleta(Unidade(pai=pai).cor_sugerida)}
```

```python
# apps/user_admin/paleta.py — os tons do disco: o ângulo distribui as cavidades pelo círculo, então
# a molécula não depende de quantas cores a paleta oferece.
class TomPaleta(BaseModel):
    slug: str
    hex: str
    rotulo: str
    angulo: int
    selecionado: bool


def tons_da_paleta(cor_selecionada: str) -> list[TomPaleta]:
    passo = GRAUS_CIRCULO // len(CorUnidade)
    return [
        TomPaleta(
            slug=cor.value,
            hex=HEX_POR_COR[cor],
            rotulo=cor.label,
            angulo=indice * passo,
            selecionado=cor.value == cor_selecionada,
        )
        for indice, cor in enumerate(CorUnidade)
    ]
```

## Fora de escopo

- **Gravar** unidade: o POST é ato administrativo e entra com autenticação, autorização por perfil e
  registro da execução (§3.5) na SPEC seguinte. Aqui o `submit` não tem destino.
- **Inserir a unidade nova no campo do servidor** depois de salvar (swap fora de banda) e fechar o
  modal em resposta ao servidor — dependem do POST.
- Validar hierarquia na tela (nível, vedas de tipo-filho, tipo que exige pai): a regra é o
  `clean()` do model e se manifesta na gravação.
- Editar e listar unidades; criar **tipo** de unidade pelo modal; modal dentro de modal (cadastrar a
  unidade superior a partir do formulário de unidade).
- Fechar o modal com `Esc` (exigiria `<dialog>` e JavaScript de estado).
- Qualquer mudança no campo de seleção de vidro ou na espessura do vidro: são da SPEC 011, e aqui
  entram por composição.

## Testes (TDD)

O que é visual — a placa de gelo do modal, o embaçamento do fundo, o brilho do botão — se valida no
mock. Os testes abaixo fixam o **contrato HTTP/partial**. Todos tocam o banco (os selects são
montados a partir das tabelas) e levam o marker `banco`, declarado no front-matter.

- `test_pagina_criar_unidade_renderiza_o_formulario` — GET devolve 200 com as três seções
  (identificação, hierarquia, identidade visual) e o disco de paleta.
- `test_pagina_criar_perfil_traz_o_modal_de_unidade` — a página de servidor traz o botão de criação
  e o modal com os campos de unidade.
- `test_modal_de_unidade_nao_aninha_formulario` — na página de servidor os dois formulários são
  irmãos: nenhum `<form>` abre dentro de outro.
- `test_campo_de_cor_assume_a_cor_da_unidade_superior` — GET com `pai` devolve o partial do campo com
  o tom do pai marcado.
- `test_campo_de_cor_sem_unidade_superior_volta_ao_tom_padrao` — sem `pai` (inclusive `pai=`, como o
  select manda na opção raiz), o tom marcado é `agua-700`.

## Patches

_Nenhum patch registrado até o momento._
