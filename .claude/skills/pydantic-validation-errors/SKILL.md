---
name: pydantic-validation-errors
description: Como erros de validação Pydantic são tratados no DIMAP GeoCoder. Use esta skill sempre que uma view precisar sinalizar um ValidationError ao usuário, ou quando for implementar qualquer view que receba DTOs Pydantic — o tratamento já está pronto, não é necessário try/except.
---

# Erros de Validação Pydantic — padrão do projeto

## Como funciona

Qualquer `pydantic.ValidationError` levantado em qualquer view é interceptado automaticamente pelo
`PydanticValidationMiddleware` (registrado em `settings.py`). O middleware renderiza o partial
`templates/partials/erro_validacao.html` com status **422** e a lista de erros do Pydantic.

O HTMX está configurado em `base.html` para fazer **swap normal em respostas 422**, então o
partial é inserido no alvo da requisição como se fosse uma resposta 2xx.

## O que já existe (não reimplementar)

| Peça | Localização |
|---|---|
| Middleware | `apps/core/middleware.py` → `PydanticValidationMiddleware` |
| Partial de erro | `templates/partials/erro_validacao.html` |
| Registro do middleware | `config/settings.py` → lista `MIDDLEWARE` |
| Config do HTMX | `templates/base.html` → `htmx.config.responseHandling` |

## Como uma view usa o padrão

A view **não precisa de `try/except`**. Basta construir o DTO normalmente — se a validação
falhar, o middleware intercepta:

```python
# apps/algum_app/views.py
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from pydantic import BaseModel


class BuscaDTO(BaseModel):
    codlog: int
    nome: str


def buscar(request: HttpRequest) -> HttpResponse:
    dto = BuscaDTO.model_validate(request.GET.dict())  # lança ValidationError se inválido
    # ... lógica normal com dto
    return render(request, "partials/_resultado.html", {"dto": dto})
```

Se `model_validate` levantar `ValidationError`, o middleware responde com o partial de erro e
status 422. A view nunca vê a exceção.

## O que o partial exibe

- Título fixo "Dados inválidos"
- Lista com cada erro: campo (`erro.loc`) e mensagem (`erro.msg`)
- Se o erro não tiver campo específico (erro de raiz), só a mensagem é exibida
- Estilo: componente `alert alert-error` do DaisyUI

## Por que o HTMX precisa de configuração especial

HTMX 2.x não faz swap em respostas não-2xx por padrão. A configuração abaixo (já em `base.html`)
habilita o swap apenas para 422, mantendo o comportamento padrão para os demais erros:

```javascript
htmx.config.responseHandling = [
  {code: "204", swap: false},
  {code: "[23]..", swap: true},
  {code: "422", swap: true},   // ← ValidationError do Pydantic
  {code: "[45]..", swap: false, error: true},
];
```

## O que NÃO fazer

- Não escreva `try/except ValidationError` em nenhuma view — o middleware é o ponto único.
- Não crie um partial de erro por app — `erro_validacao.html` é global e reutilizável.
- Não altere o status de retorno do middleware — 422 é o código semântico correto para
  erros de validação de entrada e é o que o HTMX está configurado para reconhecer.
