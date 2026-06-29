---
spec: roteamento_busca/008
versao: v3
atualizado_em: 2026-06-29
patches:
  - p1: DTOs de seleção movidos para schemas.py em cada app (fora do views.py)
  - p2: codlog normalizado para 5 dígitos no LogradouroCatalog (catalog.py)
implementado: true
changelog:
  - v1: versão inicial
  - v2: view de seleção de endereço passa a receber codlog + número (em vez de
    tipo_logradouro/logradouro/numero) — evita re-resolver o codlog já conhecido
  - v3: DTO LogradouroMatch renomeado para LogradouroMatchOutput (padroniza com
    CodlogMatchOutput/ContribuinteMatchOutput) — refletido no domínio e nesta SPEC
---

# SPEC roteamento_busca/008 — Seleção de sugestão clicável

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como usuário da busca simples, quero **clicar** numa sugestão da lista suspensa para
**selecioná-la** e disparar a busca de fato daquele elemento, para que (futuramente) sua
geometria seja plotada no mapa. Nesta iteração, a seleção apenas **registra no console do
servidor** qual foi o tipo escolhido e os dados do elemento.

## Critérios de aceite
- [ ] Cada `<li>` das listas de sugestão de **logradouro por nome**, **logradouro por codlog**
      e **lote por contribuinte** é clicável (aparência de clicável: `cursor-pointer` + hover) e
      dispara uma requisição HTMX `POST` no clique.
- [ ] Clicar numa sugestão de **logradouro** (tanto da lista por nome quanto da lista por codlog)
      chama a **view de seleção de logradouro**, passando o **codlog** do item — mesmo quando a
      busca original foi por nome. O servidor imprime no `stdout` o tipo `logradouro` e o codlog.
- [ ] Clicar numa sugestão de **lote** chama a **view de seleção de lote**, passando o número de
      contribuinte completo (**setor, quadra, lote** e dígito quando houver). O servidor imprime no
      `stdout` o tipo `lote` e o contribuinte.
- [ ] Existe uma **view de seleção de endereço** que recebe **codlog e número** e imprime no
      `stdout` o tipo `endereço` e os dados — ainda **sem** um template que a acione (stub para a
      próxima iteração). O codlog identifica o logradouro (linha) sobre o qual o número será
      interpolado, então não há necessidade de re-resolver o nome do logradouro.
- [ ] Há **uma view (e rota) por tipo** de entidade — a checagem de tipo é garantida estruturalmente
      por existir uma view dedicada a cada tipo, cada uma com seu DTO de entrada.
- [ ] A resposta de cada view é um **partial HTML** (HATEOAS) — sem JSON consumido por JS, sem regra
      de negócio no frontend. O CSRF é herdado do `hx-headers` do `<body>`.

## Contexto e decisões de arquitetura
Mexe em **interface/orquestração** (templates dos partials de sugestão + novas views por app de
entidade + rotas) e prepara o terreno para o **domínio** (resolução de geometria) numa iteração
futura. Nesta SPEC **não há resolução de geometria nem plotagem** — as views são *stubs* que
validam o DTO de seleção e dão `print()` no `stdout` do servidor.

Fluxo: o partial de sugestões já é renderizado em `#sugestoes-busca` (SPEC 005). Agora cada item da
lista ganha atributos HTMX (`hx-post` + `hx-vals`) que, no clique (gatilho *default* de `<li>` é
`click`), enviam ao servidor os identificadores daquele item. A view do tipo correspondente recebe
esses dados, monta um **DTO Pydantic de seleção** e, por ora, imprime tipo + dados.

Decisões:
- **Uma view por tipo de entidade**, em seu próprio app (`logradouro_matcher`, `lote_matcher`,
  `address_geocoder`). Isso garante a checagem de tipo (cada view só aceita o DTO do seu tipo) e
  antecipa a divergência de geometria (linha / polígono / ponto). Segue §10.1 (um domínio por
  módulo).
- **Logradouro por nome e por codlog convergem na mesma view** de seleção de logradouro: ambos
  resolvem para uma **linha** a partir do **codlog**, então os dois partials postam o `codlog` para
  a mesma rota. (Não confundir "logradouro vs codlog" — são duas *formas de busca* do **mesmo**
  tipo de saída.)
- **CSRF herdado:** o `base.html` já define `hx-headers='{"X-CSRFToken": ...}'` no `<body>`; como os
  `<li>` ficam dentro do `<body>`, herdam o token. **Não** é preciso passar `csrf_token` pelo
  `render_to_string` dos partials (que são renderizados sem `request`).
- **Validação:** as views constroem o DTO de seleção e deixam qualquer `ValidationError` borbulhar —
  o `PydanticValidationMiddleware` já devolve o partial 422 (ver skill `pydantic-validation-errors`).
  Sem `try/except` na view.
- **Alvo da resposta:** por ora um partial *placeholder* (a geometria/mapa é iteração futura). O
  alvo (`hx-target`/`hx-swap`) é decisão de implementação; sugere-se uma área de resultado dedicada
  na home, que mais adiante será substituída pelo partial do mapa (`apps/mapping`).

## Peças de referência a compor
- `@apps/search/views.py` (`secao_*`) e `@apps/logradouro_matcher/views.py` /
  `@apps/lote_matcher/views.py` → padrão de view fina que monta DTO, chama camada apropriada e
  renderiza partial. Reaproveitar o estilo.
- `@templates/base.html` → `hx-headers` de CSRF no `<body>`: os `<li>` herdam o token; nada a fazer
  além de confiar na herança (skill `htmx` → `hx-headers`).
- `@apps/core/middleware.py` (`PydanticValidationMiddleware`) + skill `pydantic-validation-errors` →
  views constroem DTO sem `try/except`; erro vira 422 automaticamente.
- DTOs já existentes que descrevem os campos disponíveis nos partials:
  `ContribuinteMatchOutput` (setor, quadra, lote, digito, codlog, logradouro, numero…),
  `CodlogMatchOutput` (codlog, dv, …) e `LogradouroMatchOutput` (codlog, tipo_codigo, nome_logradouro).
- skill `htmx` → `hx-post`, `hx-vals` (parâmetros extras no POST), gatilho *default* `click` em
  `<li>`, `hx-target`/`hx-swap`.

## Snippets sugeridos
```html
<!-- resultados_codlog.html / resultados_logradouro.html: <li> de logradouro posta o codlog -->
<li
  class="py-3 flex items-baseline gap-4 cursor-pointer hover:bg-base-200"
  hx-post="{% url 'logradouro_matcher:selecionar' %}"
  hx-vals='{"codlog": "{{ r.codlog }}"}'
  hx-target="#resultado-busca"
  hx-swap="innerHTML"
>
  ...
</li>
```

```html
<!-- resultados_contribuinte.html: <li> de lote posta o contribuinte completo -->
<li
  class="py-3 flex items-baseline gap-4 cursor-pointer hover:bg-base-200"
  hx-post="{% url 'lote_matcher:selecionar' %}"
  hx-vals='{"setor": "{{ r.setor }}", "quadra": "{{ r.quadra }}", "lote": "{{ r.lote }}", "dv": "{{ r.digito|default:'' }}"}'
  hx-target="#resultado-busca"
  hx-swap="innerHTML"
>
  ...
</li>
```

```python
# apps/logradouro_matcher/views.py — view de seleção (stub: só print)
from pydantic import BaseModel  # DTO de seleção; local definitivo é decisão de implementação


class LogradouroSelection(BaseModel):
    codlog: str


@require_POST
def selecionar(request: HttpRequest) -> HttpResponse:
    selecao = LogradouroSelection(codlog=request.POST.get("codlog", ""))
    print(f"[SELEÇÃO] tipo=logradouro {selecao!r}")  # iteração futura: resolver linha no domínio
    return render(request, "logradouro_matcher/partials/_selecao.html", {"selecao": selecao})
```

```python
# config/urls.py — incluir as rotas dos apps de entidade (hoje só core e search estão incluídos)
path("logradouro/", include("apps.logradouro_matcher.urls")),
path("lote/",       include("apps.lote_matcher.urls")),
path("endereco/",   include("apps.address_geocoder.urls")),
```

> Os DTOs de seleção (`LogradouroSelection`, e os equivalentes de lote com setor/quadra/lote/dv e de
> endereço com codlog/numero) são o **contrato de entrada** da futura resolução
> de geometria no domínio. Reaproveitar, quando fizer sentido, as restrições já expressas em
> `ContribuinteMatchInput`/`CodlogMatchInput` (padrões de dígitos, dependência quadra→lote).

## Fora de escopo
- **Resolução de geometria** (linha / polígono / ponto) e qualquer chamada ao domínio para
  geocodificar/encontrar o elemento — as views só imprimem nesta iteração.
- **Plotagem no mapa** (`apps/mapping` / Leaflet / WMS).
- **Template e fluxo de sugestão de endereço**: a view de endereço é criada como *stub*, mas nenhum
  partial a aciona ainda.
- **Caso especial do endereço fiscal exato** (pop-up ponto vs. polígono).
- **Salvar em projeto** e qualquer fluxo de autenticação.

## Notas de teste
<Só para referência futura — não implementar agora.>
- Clique numa sugestão de logradouro por **nome** posta o `codlog` correto (e não o nome) para a
  rota de logradouro; idem para a lista por **codlog**.
- Clique numa sugestão de lote posta setor/quadra/lote/dv corretos; item sem dígito posta `dv` vazio
  e o DTO aceita `dv=None`.
- DTO de seleção inválido (ex.: codlog vazio) cai no middleware e devolve 422 (não 500).
- A requisição do `<li>` herda o CSRF do `<body>` (sem `403`).
- View de endereço imprime corretamente tipo+dados quando chamada diretamente (sem template).

## Patches

### p1 — DTOs de seleção em `schemas.py`
Os DTOs `LogradouroSelection`, `LoteSelection` e `EnderecoSelection` ficam em
`apps/<app>/schemas.py` (um módulo por app), não embutidos no `views.py`. As views
importam de lá. Padrão a seguir em toda nova view de seleção.

### p2 — codlog normalizado para 5 dígitos no `LogradouroCatalog`
**Problema:** o parquet armazena `codlog` como 6 chars (5 dígitos + 1 DV concatenados).
O `CodlogMatcher` já fatia corretamente (`[:5]` e `[5]`), mas o `LogradouroCatalog._rows`
repassava o valor bruto de 6 chars para `LogradouroMatchOutput.codlog`. Como resultado,
o template `resultados_logradouro.html` postava um codlog de 6 dígitos que falhava no
padrão `^\d{1,5}$` do `LogradouroSelection`, gerando 422.

**Correção:** `LogradouroCatalog._rows` agora fatia `c[:5]` ao instanciar `LogradouroRow`,
mantendo `LogradouroMatchOutput.codlog` sempre com 5 dígitos — consistente com
`CodlogMatchOutput.codlog`.
