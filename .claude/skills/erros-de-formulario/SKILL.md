---
name: erros-de-formulario
description: Como um formulário HTMX do DIMAP GeoCoder devolve erro de validação com mensagem em português e o controle errado destacado. Use SEMPRE que escrever ou alterar uma view cujo alvo HTMX é o próprio `<form>` — criação/edição de servidor e afins. Complementar à skill pydantic-validation-errors, que cobre o caso genérico.
---

# Erros de formulário — `services.utils.erros_formulario`

## Quando usar esta skill, e não `pydantic-validation-errors`

O `PydanticValidationMiddleware` (skill `pydantic-validation-errors`) resolve o caso genérico:
qualquer view que levante `ValidationError` recebe de volta o partial `erro_validacao.html`, que o
HTMX troca **no alvo da requisição**.

Isso quebra quando o **alvo é o próprio `<form>`** com `outerHTML` — o caso de toda tela que
preenche um formulário e reenvia no mesmo lugar. O partial genérico substituiria a tela inteira por
uma lista de erros em inglês, sem nenhum campo para corrigir. Use esta skill sempre que a view for
desse tipo. Para as demais rotas, `pydantic-validation-errors` continua valendo — não migre view que
não é formulário para este padrão.

## O que já existe (não reimplementar)

| Peça | Localização |
|---|---|
| Contrato (`Formulario`, `CampoDeFormulario`, `RegraDeErro`, `TomDeRealce`, ...) | `services/utils/erros_formulario` |
| Regras padrão por tipo de erro Pydantic | `services/utils/erros_formulario/regras.py` |
| Tradutor (erro cru → `RecusaDeFormulario`) | `services/utils/erros_formulario/tradutor.py` |
| Leitor (POST cru → DTO ou recusa, sem `try/except` na view) | `services/utils/erros_formulario/leitor.py` |
| Ponte do `ValidationError` do Django | `apps/core/erros_formulario.py` → `de_validation_error` |
| Átomo de realce (`.campo-realce-erro/-alerta/-info/-sucesso`) | `static/src/tema-dimap.dev.css`, já no styleguide |

## 1 · Declarar o catálogo

Cada formulário declara, em código, ao lado do app que o renderiza, quais controles existem e como
cada tipo de erro se traduz. A regra padrão (`REGRAS_PADRAO`) já cobre `missing`,
`string_too_short`, `string_too_long`, `int_parsing` e `value_error` — só declare `regras=` quando o
formulário precisar de uma frase melhor que a genérica.

```python
# apps/<app>/formularios.py
from services.utils.erros_formulario import CampoDeFormulario, Formulario, LeitorDeFormulario, RegraDeErro

FORMULARIO_SERVIDOR = Formulario(
    campos=(
        CampoDeFormulario(controle="rf", rotulo="RF"),
        CampoDeFormulario(controle="nome", rotulo="Nome"),
        CampoDeFormulario(
            controle="email",
            rotulo="E-mail",
            regras={"value_error": RegraDeErro(mensagem="E-mail inválido: confira o endereço.")},
        ),
        CampoDeFormulario(controle="unidade", rotulo="Unidade"),
    )
)

ler_novo_servidor = LeitorDeFormulario(NovoServidor, FORMULARIO_SERVIDOR)
```

`controle=` é sempre o `name=` do input no template — o realce pergunta pelo mesmo nome. O sufixo
`_id` do DTO (`unidade_id`) já cai sozinho para bater com o `name="unidade"` do `<select>`; declare
o campo do catálogo pelo nome **sem** o sufixo.

## 2 · Ler o formulário pelo leitor, nunca construir o DTO direto na view

```python
@require_POST
def gravar(request: HttpRequest) -> HttpResponse:
    # NUNCA `NovoServidor(**request.POST.dict())` direto: o ValidationError subiria ao
    # PydanticValidationMiddleware, que troca o ALVO da requisição — aqui, o <form> inteiro.
    leitura = ler_novo_servidor(request.POST)
    if leitura.recusa is not None:
        return render(request, TEMPLATE_FORMULARIO, {"valores": request.POST, "recusa": leitura.recusa}, status=422)

    dto = leitura.dto
    # ... segue com dto, já validado
```

`leitura` é ou `dto`, ou `recusa` — nunca os dois, nunca nenhum. Não há `try/except` a escrever.

## 3 · Recusa vinda do model do Django (`ValidationError` de `full_clean`/`save`)

Passe pela ponte de `apps/core/erros_formulario.py` antes do tradutor — é o único módulo que importa
`django.core.exceptions.ValidationError`; o domínio em `services/` não o vê.

```python
from apps.core.erros_formulario import de_validation_error
from services.utils.erros_formulario import TradutorDeRecusa

tradutor = TradutorDeRecusa(FORMULARIO_SERVIDOR)

try:
    servidor.full_clean()
    servidor.save()
except DjangoValidationError as erro:
    recusa = tradutor(de_validation_error(erro))
    return render(request, TEMPLATE_FORMULARIO, {"valores": request.POST, "recusa": recusa}, status=422)
```

`de_validation_error` usa `error_dict` (não `message_dict`) para preservar o `code` de cada erro
como `tipo`. Quando o model já escreve a mensagem em português — caso típico de `unique` — ela
**vence** a regra do catálogo; para trocar essa frase, mexa no `error_messages` do model, não no
catálogo do formulário.

## 4 · Aplicar o realce no template

```html
{# O realce é do CONTROLE, não do `.form-field`: string vazia quando o campo não foi recusado. #}
<input type="text" name="rf" value="{{ valores.rf|default:'' }}"
       class="input input-glass {{ realce.rf }}" />
<select name="unidade" class="select select-glass {{ realce.unidade }}" data-select-onsen>
```

`realce` vem de `recusa.realce` — um `Mapping[str, str]` onde a chave ausente já renderiza string
vazia no Django, sem precisar de `|default:''` no filtro de classe. Para a tarja de mensagens gerais
(erro sem controle, como o `__all__` do Django), use `recusa.gerais`; para a lista completa,
`recusa.mensagens`.

## O que NÃO fazer

- Não construa o DTO do formulário direto na view (`MeuDTO(**request.POST.dict())`) quando a view
  devolve o próprio `<form>` — isso reintroduz o caminho do `PydanticValidationMiddleware` que este
  padrão existe para evitar.
- Não escreva `try/except ValidationError` fora do `LeitorDeFormulario` — ele já encapsula.
- Não invente `RegraDeErro` para tipo que a `REGRAS_PADRAO` já cobre.
- Não importe `django.core.exceptions` dentro de `services/utils/erros_formulario` — a ponte é
  sempre `apps/core/erros_formulario.py`.
- Não monte nome de classe CSS por concatenação — `TomDeRealce` já guarda a classe pronta.
