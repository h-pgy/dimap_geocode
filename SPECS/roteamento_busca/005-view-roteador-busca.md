---
spec: roteamento-busca/005
versao: v4
atualizado_em: 2026-06-28
implementado: true
changelog:
  - v1: versão inicial
  - v2: a view do roteador, o registro de seções e o partial agregador moram no app `search`
        (não no `core`) — alinhando ao §6 do CLAUDE.md; criação do app `search` faz parte da SPEC.
  - v3: nomes HTMX semânticos — alvo `#sugestoes-busca` e partial agregador `_sugestoes.html`.
  - v4: `SecaoResultado` movida de `logradouro_matcher/views.py` para `apps/search/secoes.py`
        como Pydantic `BaseModel` (não dataclass) — o contrato pertence ao `search`, que é quem
        agrega todas as seções; os matchers importam dali.
---

# SPEC roteamento-busca/005 — View do roteador na barra única (agrega seções de sugestões)

- [x] **Implementada**

## User story

Como usuário, quero digitar **qualquer coisa** na barra de pesquisa única da home e, a cada tecla
(com *delay*) ou ao finalizar a digitação, ver **sugestões agrupadas por tipo** (logradouro, lote,
endereço, …) logo abaixo da barra, para escolher rapidamente o resultado certo sem precisar dizer ao
sistema qual é o tipo da minha busca.

Nesta iteração, apenas as sugestões de **logradouro por codlog** são exibidas; as demais seções
entram em iterações seguintes, encaixando-se na mesma estrutura.

## Critérios de aceite

- [ ] A barra de pesquisa da home (`@templates/core/home.html`) passa a se chamar **`input_search`**
      (era `input_codlog`), com `type="search"` e `name="termo_pesquisa"`.
- [ ] A barra dispara HTMX em **dois gatilhos**: `keyup changed delay:300ms` **e** `search`,
      via `hx-post` para a rota do roteador no app `search`, com `hx-target="#sugestoes-busca"`.
- [ ] O CSRF é enviado por `hx-headers` (`X-CSRFToken`), e um `hx-on:htmx:config-request` injeta o
      parâmetro **`tipo_evento`** com o tipo do evento que disparou a requisição
      (`event.detail.triggeringEvent.type`).
- [ ] Existe um `<div id="sugestoes-busca">` na home para receber o *swap* das sugestões.
- [ ] O app `search` é **criado** (app fino: views, urls, templates próprios), registrado em
      `INSTALLED_APPS`, e sua pasta de templates é declarada com `@source` no CSS de entrada.
- [ ] A rota do roteador aceita apenas **POST**, está registrada no `urls.py` do app `search` e
      incluída no `urls.py` do projeto.
- [ ] A view do roteador monta a DTO **`RoteamentoQuery`** com `texto = termo_pesquisa` e
      `finished_typing = (tipo_evento == "search")` — ou seja, **`finished_typing=True` só quando o
      evento foi `search`**; em `keyup` é `False`.
- [ ] A view chama **`rotear_entrada`** (domínio, já pronto) e obtém os candidatos do resultado.
- [ ] Para **cada candidato**, a view consulta um **registro extensível** `TipoEntrada → section
      renderer` (no app `search`); se houver um renderer para aquele tipo, ele é chamado e devolve uma
      **seção pronta** (título + HTML do partial daquele tipo). Tipos sem renderer registrado são
      **ignorados sem erro**.
- [ ] Nesta entrega, **apenas `TipoEntrada.CODLOG`** está registrado, apontando para o renderer que
      reaproveita a busca de codlog existente (logradouro_matcher). Contribuinte, endereço e logradouro
      por nome **não** têm renderer ainda.
- [ ] A view renderiza um **partial agregador próprio do `search`** que itera as seções, cada uma num
      `<section>` com um **cabeçalho** (título do tipo) seguido do HTML da seção, injetado com `|safe`.
      A estrutura é extensível (uma `<section>` por tipo).
- [ ] Quando não há nenhuma seção a exibir (entrada vazia, impossível ou só tipos sem renderer), o
      partial agregador **limpa/esvazia** o painel de sugestões (sem quebrar).
- [ ] A view **buscar_codlog** existente (`logradouro_matcher`) é **refatorada para um wrapper fino**
      sobre o renderer compartilhado e **continua funcionando** para uso direto via HTMX (regressão).
- [ ] Respostas são **partials HTML** (§3.1) — nunca JSON. `ValidationError` propaga ao middleware
      (infraestrutura/001), sem `try/except` na view.
- [ ] Tipagem integral; `mypy` limpo.

## Contexto e decisões de arquitetura

Esta SPEC mexe na **camada de interface** (views + urls + templates), criando o app **`search`**
(orquestração da barra única) e refatorando a `buscar_codlog` no `logradouro_matcher`. O **domínio já
está pronto**: `rotear_entrada` (roteamento-busca/001) classifica a entrada e `match_codlog` (a busca
por codlog) resolve as sugestões. Nada de domínio novo aqui.

> **Localização (§6 do CLAUDE.md).** O §6 prevê o app `search` para a barra única — "aciona o
> roteamento e renderiza sugestões assíncronas". É exatamente o papel desta view, então ela nasce no
> `search`. O app ainda não existe e é **criado** nesta SPEC (app fino, sem regra de negócio). A barra
> de pesquisa em si segue na home (`core`), apenas apontando o `hx-post` para a rota do `search`.

### Fluxo

```
Home (core): <input id="input_search" name="termo_pesquisa">
  HTMX: hx-trigger="keyup changed delay:300ms, search"
        hx-post=search:rotear_busca  hx-target="#sugestoes-busca"
        hx-on:htmx:config-request -> parameters['tipo_evento'] = triggeringEvent.type
   │  (POST: termo_pesquisa, tipo_evento)
   ▼
search.views.rotear_busca (orquestração)
   • RoteamentoQuery(texto=termo_pesquisa, finished_typing = tipo_evento == "search")
   • result = rotear_entrada(query)
   • secoes = []
     for candidato in result.candidatos:
         render_secao = REGISTRO_SECOES.get(candidato.tipo)   # hoje só CODLOG
         if render_secao: secoes.append(render_secao(candidato))
   • render("search/partials/_sugestoes.html", {"secoes": secoes})
       └ uma <section> por seção: cabeçalho (titulo) + {{ secao.html|safe }}
```

### Section renderer compartilhado (decisão de despacho)

O ponto comum entre **(a)** o roteador, que recebe um **candidato** (`CodlogParse`), e **(b)** a view
direta `buscar_codlog`, que recebe um **POST** com `input_codlog`, é: *montar `CodlogMatchInput` →
chamar `match_codlog` → renderizar o partial da `ul` de sugestões para HTML*. Esse núcleo é extraído
para um **renderer compartilhado** no `logradouro_matcher`:

- `secao_codlog(candidato: CodlogParse) -> SecaoResultado` — **adapta** o candidato para
  `CodlogMatchInput` (`input_codlog = candidato.codlog`, `digito_verificador = candidato.digito_verificador or None`),
  roda o matcher e devolve uma `SecaoResultado(titulo=..., html=...)` com o partial já renderizado
  (`render_to_string` do `resultados_codlog.html`). É o que o **registro** do `search` aponta para
  `TipoEntrada.CODLOG`.
- `buscar_codlog(request)` (rota direta, mantida) vira **wrapper fino**: monta `CodlogMatchInput` a
  partir do POST, reaproveita o mesmo núcleo de render e devolve a `ul` como `HttpResponse`.

Assim **não** é preciso clonar/forjar `request` para chamar uma view a partir de outra: o roteador
chama funções Python diretamente, e cada tipo é uma responsabilidade isolada (§10.1) composta pelo
registro (§10.4).

### Registro extensível (orquestração no `search`)

Um `dict` `REGISTRO_SECOES: dict[TipoEntrada, SectionRenderer]` mapeia cada tipo de candidato ao seu
renderer. Hoje só `CODLOG` está presente. Adicionar contribuinte/endereço/logradouro-por-nome no
futuro = implementar o renderer no app de domínio correspondente e registrar a entrada — **sem tocar**
no laço da view nem no partial agregador. `SecaoResultado` é o **contrato** entre renderer e partial
(título do cabeçalho + HTML seguro da `ul`).

### Princípios aplicados (§3, §10, §11)

- **§3.1 HATEOAS:** view devolve *partials* HTML; nenhuma montagem de UI por JS/JSON. O JS é apenas o
  *callback* de `htmx:config-request` para anexar `tipo_evento` (uso permitido — §11).
- **§3.3 Isolamento:** a view só **orquestra** — traduz POST em `RoteamentoQuery` (DTO Pydantic),
  chama o domínio, despacha pelo registro e escolhe o partial. Sem regra de negócio.
- **§10.1 SRP / §10.4 Composição:** um renderer por tipo; o roteador compõe via registro.
- **§11:** `ValidationError` tratado pelo middleware (infra/001); partials prefixados com `_`; nova
  pasta de template registrada com `@source` se necessário.

## Peças de referência a compor

- `@services/domain/roteamento_busca` → `rotear_entrada`, `RoteamentoQuery`, `RoteamentoResult`,
  `Candidato`, `CodlogParse`, `TipoEntrada`: o roteador é consumido como está; a view monta a
  `RoteamentoQuery` e itera `result.candidatos` (cada candidato carrega `.tipo`).
- `@services/domain/codlog_match` → `match_codlog`, `CodlogMatchInput`: usados pelo renderer de codlog
  para resolver as sugestões a partir do candidato.
- `@apps/logradouro_matcher/views.py` → `buscar_codlog`: **refatorar** para wrapper fino sobre o
  renderer compartilhado, preservando a rota e o comportamento atual.
- `@templates/logradouro_matcher/partials/resultados_codlog.html` → a `ul` de sugestões de codlog:
  **reutilizada** tal como está, agora também via `render_to_string` dentro da seção.
- `@templates/core/home.html` → a barra de pesquisa (na home) a ser renomeada/instrumentada com HTMX,
  apontando o `hx-post` para a rota do app `search`.
- `@apps/core` e `@apps/logradouro_matcher` → padrão de **app fino** (views, urls, templates,
  `app_name`) a espelhar na criação do app `search`.
- **SPEC infraestrutura/001** (`PydanticValidationMiddleware`) → trata `ValidationError`; a view não
  faz `try/except`.
- **Skill `htmx`** → referência para `hx-on:htmx:config-request`, `hx-headers` e `hx-trigger` com
  múltiplos gatilhos/modificadores.

## Snippets sugeridos

### Barra de pesquisa na home (`templates/core/home.html`)

```htmldjango
{# direção — manter Tailwind/DaisyUI do projeto #}
<input type="search"
       id="input_search"
       name="termo_pesquisa"
       placeholder="Rua, endereço, codlog ou nº de contribuinte…"
       class="input input-bordered flex-1"
       hx-post="{% url 'search:rotear_busca' %}"
       hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'
       hx-trigger="keyup changed delay:300ms, search"
       hx-target="#sugestoes-busca"
       hx-on:htmx:config-request="event.detail.parameters['tipo_evento'] = event.detail.triggeringEvent.type">

<div id="sugestoes-busca" class="mt-6"></div>
```

### View do roteador (`apps/search/views.py`)

```python
# direção de implementação — adaptar sem violar §3 nem §10

from collections.abc import Callable
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.logradouro_matcher.views import SecaoResultado, secao_codlog
from services.domain.roteamento_busca import (
    Candidato, RoteamentoQuery, TipoEntrada, rotear_entrada,
)

SectionRenderer = Callable[[Candidato], SecaoResultado]

# registro extensível: hoje só CODLOG. Outros tipos entram aqui, sem mudar o laço.
REGISTRO_SECOES: dict[TipoEntrada, SectionRenderer] = {
    TipoEntrada.CODLOG: secao_codlog,
}


@require_POST
def rotear_busca(request: HttpRequest) -> HttpResponse:
    query = RoteamentoQuery(
        texto=request.POST.get("termo_pesquisa", ""),
        finished_typing=request.POST.get("tipo_evento") == "search",
    )
    result = rotear_entrada(query)
    secoes = [
        render_secao(candidato)
        for candidato in result.candidatos
        if (render_secao := REGISTRO_SECOES.get(candidato.tipo)) is not None
    ]
    return render(request, "search/partials/_sugestoes.html", {"secoes": secoes})
```

### Renderer compartilhado + wrapper (`apps/logradouro_matcher/views.py`)

```python
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from pydantic import BaseModel

from services.domain.codlog_match import CodlogMatchInput, match_codlog
from services.domain.roteamento_busca import CodlogParse


class SecaoResultado(BaseModel):
    titulo: str
    html: str


def _render_codlog(dto: CodlogMatchInput) -> str:
    resultados = match_codlog(dto)
    return render_to_string(
        "logradouro_matcher/partials/resultados_codlog.html",
        {"resultados": resultados},
    )


def secao_codlog(candidato: CodlogParse) -> SecaoResultado:
    dto = CodlogMatchInput(
        input_codlog=candidato.codlog,
        digito_verificador=candidato.digito_verificador or None,
    )
    return SecaoResultado(titulo="Logradouro (por codlog)", html=_render_codlog(dto))


@require_POST
def buscar_codlog(request: HttpRequest) -> HttpResponse:
    # wrapper fino p/ HTMX direto; ValidationError propaga ao middleware (infra/001)
    dto = CodlogMatchInput(**request.POST.dict())
    return HttpResponse(_render_codlog(dto))
```

### Partial agregador (`templates/search/partials/_sugestoes.html`)

```htmldjango
{# fragmento HTMX — uma <section> por tipo, extensível #}
{% if secoes %}
  <div class="space-y-4">
    {% for secao in secoes %}
      <section>
        <h3 class="text-sm font-semibold text-base-content/60">{{ secao.titulo }}</h3>
        {{ secao.html|safe }}
      </section>
    {% endfor %}
  </div>
{% endif %}
```

### Rota (`apps/search/urls.py`)

```python
app_name = "search"

urlpatterns = [
    path("buscar/", views.rotear_busca, name="rotear_busca"),
]
```

## Fora de escopo

- **Renderers (e domínio) de contribuinte, endereço e logradouro por nome (fuzzy):** apenas o
  **registro extensível** + o renderer de **codlog** entram agora.
- **Resolução de geometria** de cada tipo e renderização no **mapa Leaflet**.
- **Clique numa sugestão** para confirmar o match / disparar a busca final (apenas a lista é exibida).
- **Busca detalhada** (campos segmentados) e o **pop-up de endereço fiscal exato**.
- **Salvar em projeto / autenticação** — a busca é pública (§1).
- **Algoritmo do dígito verificador** (codlog/contribuinte): segue como placeholder no domínio.
- **Estilização final** das seções/`ul` (cores, DaisyUI detalhado) — refinada em SPEC de UI.
- Remoção do bloco de teste do middleware na home (independente desta SPEC).

## Notas de teste

- POST com `termo_pesquisa="163"` e `tipo_evento="keyup"` → 200; o agregador traz uma `<section>`
  "Logradouro (por codlog)" com a `ul` de sugestões; `finished_typing` foi `False`.
- POST com `tipo_evento="search"` → a `RoteamentoQuery` é montada com `finished_typing=True`.
- Entrada numérica ambígua (ex.: `termo_pesquisa="20"`, candidatos CODLOG **e** CONTRIBUINTE) →
  apenas a seção de **codlog** aparece; o candidato CONTRIBUINTE é ignorado sem erro.
- Nome de rua (ex.: `"rua itat"`, candidato LOGRADOURO, sem renderer) → nenhuma seção; o painel de
  sugestões é esvaziado.
- `termo_pesquisa=""` (status VAZIO) → nenhuma seção.
- GET na rota → 405.
- `input_codlog` inválido na rota direta `buscar_codlog` → 422 via middleware (regressão).
- `buscar_codlog` direto continua devolvendo a `ul` de sugestões como antes (regressão).
- O `digito_verificador` vazio do candidato vira `None` no `CodlogMatchInput` (não `""`).

## Patches

- 2026-06-28 (v4): `SecaoResultado` movida de `apps/logradouro_matcher/views.py` para
  `apps/search/secoes.py` como Pydantic `BaseModel`. A dataclass no matcher era errada de
  origem — o contrato de seção pertence ao `search` (agregador), e todos os matchers futuros
  importarão dali. Evita import circular: `secoes.py` não importa de nenhum outro app.
