---
spec: infraestrutura/001
versao: v1
atualizado_em: 2026-06-26
changelog:
  - v1: versão inicial (extraída de roteamento-busca/004 v2)
  - v1.1: partial de erro agora usa componentes idiomáticos DaisyUI (alert-error)
---

# SPEC infraestrutura/001 — Middleware de tratamento centralizado de ValidationError

## User story
Como desenvolvedor, quero que erros de validação Pydantic sejam tratados de forma uniforme em todo o projeto, para não precisar repetir `try/except ValidationError` em cada view e garantir uma resposta de erro consistente ao usuário.

## Critérios de aceite
- [ ] Existe um middleware Django que intercepta `pydantic.ValidationError` em **qualquer view** do projeto.
- [ ] O middleware implementa `process_exception`: se a exceção for `ValidationError`, renderiza um partial HTML genérico de erro com status **422**; caso contrário, retorna `None` (não interfere).
- [ ] O partial de erro recebe a lista de erros do Pydantic (`exc.errors()`) e exibe mensagens legíveis ao usuário.
- [ ] O partial de erro é um fragmento HTML global (sem `{% extends %}`), em `templates/partials/`, reutilizável por qualquer app.
- [ ] O middleware está registrado em `MIDDLEWARE` no `settings.py`, após os middlewares padrão do Django.
- [ ] Nenhuma view do projeto precisa de `try/except ValidationError` — o middleware é o ponto único de tratamento.

## Contexto e decisões de arquitetura

**Por que middleware e não decorator?** O Django já possui o conceito de middleware como mecanismo
nativo para comportamentos transversais ao projeto (cross-cutting concerns). Cada middleware na
stack pode processar a resposta ou interceptar exceções de **todas** as views, sem precisar
decorar cada uma individualmente. É o mesmo padrão usado pelo próprio Django para CSRF
(`CsrfViewMiddleware`), segurança (`SecurityMiddleware`) e sessões (`SessionMiddleware`).

Um middleware que implementa `process_exception` recebe qualquer exceção não tratada por uma view.
Se reconhecer um `pydantic.ValidationError`, renderiza o partial de erro com 422. Se não
reconhecer, retorna `None` e deixa o Django seguir o fluxo normal de tratamento de exceção. Isso
significa:

- **Views ficam mais magras** — constroem o DTO e deixam o `ValidationError` propagar. Zero
  boilerplate de tratamento de erro.
- **Consistência garantida** — toda validação de DTO no projeto inteiro produz a mesma resposta
  de erro, com o mesmo template, sem risco de uma view esquecer o `try/except`.
- **Um único template de erro** — o partial genérico de validação vive em `templates/partials/`
  (nível global) e serve qualquer app.

O middleware mora no app `core` (infraestrutura de interface compartilhada) e é registrado **após**
os middlewares padrão do Django em `MIDDLEWARE`.

**Camadas envolvidas:** interface (middleware no app `core`, partial global em `templates/partials/`)
e configuração (`settings.py`).

## Peças de referência a compor
- `@config/settings.py` → lista `MIDDLEWARE`: onde o novo middleware será registrado.
- `@templates/base.html` → layout base com HTMX e DaisyUI já carregados: o partial de erro não precisa re-incluir esses scripts.

## Snippets sugeridos

### Middleware (app `core`)

```python
# direção de implementação — adaptar conforme necessário, sem violar §3 nem §10

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from pydantic import ValidationError


class PydanticValidationMiddleware:
    """Intercepta pydantic.ValidationError em qualquer view e devolve
    um partial HTML de erro com status 422."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_exception(
        self, request: HttpRequest, exception: Exception
    ) -> HttpResponse | None:
        if not isinstance(exception, ValidationError):
            return None
        return render(
            request,
            "partials/erro_validacao.html",
            {"erros": exception.errors()},
            status=422,
        )
```

### Partial de erro genérico (global)

```htmldjango
{# templates/partials/erro_validacao.html — fragmento HTMX, sem extends #}
{# Recebe: erros (list[dict] do Pydantic)                               #}
{# Usa o componente alert do DaisyUI (alert-error) — design system doc:  #}
{# https://daisyui.com/components/alert/                                 #}

<div role="alert" class="alert alert-error alert-vertical sm:alert-horizontal">
  <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 shrink-0 stroke-current" fill="none" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
  <div>
    <h3 class="font-bold">Dados inválidos</h3>
    <ul class="text-sm mt-1 list-disc list-inside">
      {% for erro in erros %}
        <li>
          {% if erro.loc|length > 1 %}
            <span class="font-semibold">{{ erro.loc|join:"." }}</span> —
          {% endif %}
          {{ erro.msg }}
        </li>
      {% endfor %}
    </ul>
  </div>
</div>
```

## Fora de escopo
- Tratamento de outros tipos de exceção (erros de domínio, erros de integração) — extensões futuras podem adicionar outros tipos ao middleware ou criar middlewares adicionais.
- Views que consomem o middleware — cada view é especificada na sua própria SPEC de funcionalidade.

## Notas de teste
Verificar que um `ValidationError` levantado em qualquer view resulta em status 422 e renderização do partial genérico de erro. Verificar que exceções não-`ValidationError` passam adiante sem interferência (middleware retorna `None`). Verificar que o partial de erro contém as mensagens de cada campo inválido. Verificar que o middleware está corretamente registrado em `MIDDLEWARE`.

## Patches

### v1.1 — Partial de erro idiomático DaisyUI
- O snippet do partial de erro agora usa o componente `alert` do DaisyUI com classe `alert-error alert-vertical sm:alert-horizontal`.
- Inclui ícone SVG de erro, título "Dados inválidos" e lista `<ul>` com campo (`erro.loc`) e mensagem (`erro.msg`) de cada erro.
- O primeiro elemento de `loc` (normalmente o tipo raiz do DTO) é ignorado com `erro.loc|length > 1` — só exibe a localização quando há um campo específico.
- Removido "Estilização final do partial de erro" do Fora de escopo — agora está definida nesta SPEC.
