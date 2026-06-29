---
spec: roteamento-busca/004
versao: v3
atualizado_em: 2026-06-26
changelog:
  - v1: versão inicial
  - v2: centraliza tratamento de ValidationError via middleware Django (projeto inteiro)
  - v3: extrai middleware para SPEC infraestrutura/001; esta SPEC cobre apenas a view
---

# SPEC roteamento-busca/004 — View de busca de logradouro por codlog

## User story
Como usuário, quero submeter um código de logradouro (codlog) pela interface web e receber a lista de logradouros correspondentes renderizada na página, para localizar rapidamente o logradouro desejado sem precisar consultar outras ferramentas.

## Critérios de aceite
- [ ] A rota aceita apenas requisições **POST**.
- [ ] Os campos do corpo da requisição correspondem aos atributos de `CodlogMatchInput` (`input_codlog`, `digito_verificador` opcional, `limite` opcional).
- [ ] A view instancia `CodlogMatchInput` a partir dos dados do POST — se a validação falhar, o `ValidationError` **propaga livremente** (sem `try/except` na view; o middleware de infraestrutura/001 cuida).
- [ ] Se a validação passar, a view chama `match_codlog` (instância singleton de `CodlogMatcher`) com o DTO de entrada.
- [ ] A resposta de sucesso é um **partial HTML** (não uma página completa) contendo a lista de resultados (`CodlogMatchOutput`), renderizado por um template próprio.
- [ ] Cada item do resultado exibe pelo menos: `codlog`, `dv` e `nome_completo`.
- [ ] Se a lista de resultados estiver vazia, o partial exibe uma mensagem indicando que nenhum logradouro foi encontrado.
- [ ] A rota está registrada no `urls.py` do app `logradouro_matcher` e incluída no `urls.py` do projeto (`config/urls.py`).
- [ ] O partial de resultados é consumível via HTMX (atributos `hx-post`, `hx-target`, `hx-swap` no formulário que o invoca).

## Contexto e decisões de arquitetura

Esta SPEC mexe na **camada de interface**: view + template + urls no app `logradouro_matcher`, mais a inclusão da rota em `config/urls.py`. A camada de domínio **já está pronta** — esta SPEC apenas a consome.

O tratamento de `ValidationError` é centralizado pelo middleware especificado em **infraestrutura/001** — a view não faz `try/except`, apenas constrói o DTO e deixa a exceção propagar se os dados forem inválidos.

### Fluxo

```
POST (form HTMX) → middleware stack → view logradouro_matcher
  → CodlogMatchInput(**request.POST)
    → ValidationError? → propaga → middleware (infra/001) → partial erro (422)
    → sucesso → match_codlog(dto) → list[CodlogMatchOutput]
      → renderiza partial com resultados (200)
```

### Princípios aplicados (§3 do AGENTS.md)

- **§3.1 — HATEOAS via HTMX:** a view retorna um partial HTML, nunca JSON.
- **§3.2 — Models como persistência:** nenhum model é criado ou alterado.
- **§3.3 — Isolamento entre camadas:** a view faz somente orquestração — traduz `request.POST`
  em DTO Pydantic, chama o domínio, escolhe o template e responde. Nenhuma lógica de negócio.

**Sobre o template:** o partial de resultados é um fragmento HTML (sem `{% extends %}`) pensado
para ser injetado via `hx-swap`. Itera sobre a lista de `CodlogMatchOutput` e exibe as informações
de cada logradouro.

## Peças de referência a compor
- `@services/domain/codlog_match` → `match_codlog` (instância singleton de `CodlogMatcher`): invocar com o DTO de entrada para executar a busca.
- `@services/domain/codlog_match` → `CodlogMatchInput`: importar e usar para parsing/validação dos dados do POST.
- `@services/domain/codlog_match` → `CodlogMatchOutput`: tipo dos itens da lista de resultados, passados ao template. Propriedade `nome_completo` disponível.
- `@apps/core/views.py` → padrão de view existente (function-based view com `render`): seguir o mesmo estilo.
- `@templates/base.html` → layout base com HTMX e DaisyUI já carregados: o partial não precisa re-incluir esses scripts.
- **SPEC infraestrutura/001** → `PydanticValidationMiddleware`: deve estar implementado e registrado antes desta view; garante o tratamento automático de `ValidationError` com status 422.

## Snippets sugeridos

### View (app `logradouro_matcher`)

```python
# direção de implementação — adaptar conforme necessário, sem violar §3 nem §10

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from services.domain.codlog_match import CodlogMatchInput, match_codlog


@require_POST
def buscar_codlog(request: HttpRequest) -> HttpResponse:
    # ValidationError propaga → middleware (infra/001) devolve 422 automaticamente
    dto = CodlogMatchInput(**request.POST.dict())
    resultados = match_codlog(dto)
    return render(
        request,
        "logradouro_matcher/partials/resultados_codlog.html",
        {"resultados": resultados},
    )
```

### Partial de resultados

```htmldjango
{# templates/logradouro_matcher/partials/resultados_codlog.html #}
{% if resultados %}
  {% for r in resultados %}
    {# cada item exibe codlog, dv e nome_completo #}
  {% endfor %}
{% else %}
  {# mensagem de nenhum resultado encontrado #}
{% endif %}
```

## Fora de escopo
- Middleware de validação — especificado em infraestrutura/001.
- Estilização final dos partials (layout, cores, componentes DaisyUI detalhados) — será refinada em SPEC de UI.
- Formulário de busca na página (o formulário que dispara o POST via HTMX pertence ao app `search` ou `core`, não a esta SPEC).
- Busca por nome de logradouro (texto livre / fuzzy) — módulo e SPEC separados.
- Persistência de resultados ou integração com projetos.
- Renderização da geometria do logradouro no mapa Leaflet.
- Autenticação — esta rota é pública (§1 do AGENTS.md: busca avulsa não exige login).

## Notas de teste
Verificar que POST com `input_codlog` válido retorna status 200 e HTML com resultados. Verificar que POST com `input_codlog` inválido (vazio, >5 dígitos, caracteres não numéricos) retorna status 422 via middleware. Verificar que GET na rota retorna 405 (Method Not Allowed). Verificar que o partial de resultados vazios exibe a mensagem correta. Verificar que `limite` é respeitado (enviar `limite=1` e conferir que só 1 resultado aparece). Verificar que os campos `codlog`, `dv` e `nome_completo` aparecem no HTML de cada resultado.

## Patches

_Nenhum patch registrado até o momento._
