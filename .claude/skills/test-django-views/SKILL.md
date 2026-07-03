---
name: test-django-views
description: Pipeline para smoke test manual de views Django/HTMX do DIMAP GeoCoder (o "validar a implementação" do fluxo de SPEC, CLAUDE.md §13 — não é escrever testes automatizados). Use sempre que acabar de implementar ou alterar uma view e precisar confirmar o comportamento real (status code, HTML do partial, caminhos de erro) antes de reportar a tarefa como concluída, sem depender de browser.
---

# Smoke test de views Django — `django.test.Client` via `manage.py shell -c`

## Quando usar

Depois de implementar/alterar uma view (§13 do CLAUDE.md: "validar a implementação — smoke test
manual" vem **antes** de qualquer teste automatizado, que só é escrito sob pedido explícito). Serve
para:

- Confirmar que a view responde o **status code** e o **partial HTML** esperados no caminho feliz.
- Percorrer os **caminhos de erro** (exceções de domínio → aviso semântico, `ValidationError` do
  Pydantic → 422) sem precisar simular cada caso na mão em um browser.
- Inspecionar o payload exato que vai para o template (ex.: o JSON embutido que o Leaflet consome).

**Não substitui** `uv run mypy`/`ruff check` nem os testes de domínio via `pytest` — é o passo de
validação funcional da view/orquestração, que aqueles não cobrem.

## Pipeline recomendado: `django.test.Client`, sem subir servidor

Para a grande maioria dos casos (views HTMX que recebem POST/GET e devolvem um partial), o caminho
mais rápido é o **`Client` de teste do Django** dentro do shell do projeto — roda no mesmo processo,
**não abre socket real** e, importante, **não aplica CSRF** por padrão (evita todo o ruído de
cookie/token que apareceria batendo com `curl` num servidor de verdade).

```bash
uv run python manage.py shell -c "
from django.test import Client
c = Client()
r = c.post('/endereco/selecionar/', {'codlog': '156566', 'numero': '300'})
print('STATUS', r.status_code)
print(r.content.decode()[:2000])
"
```

- `c.post(url, {...})` — envia os campos como `request.POST` (form-encoded), do jeito que o HTMX
  manda via `hx-vals`/formulário.
- `c.get(url, {...})` — idem para querystring.
- `r.status_code` e `r.content.decode()` — inspeciona status e o HTML/JSON renderizado.
- O aquecimento de caches que aparece no stdout (`[LogradouroCatalog] aquecendo cache...` etc.) é
  normal — vem do carregamento do Django, não é erro.

### Cobrindo vários cenários numa única chamada

Empilhe várias requisições no mesmo script para cobrir caminho feliz + erros de domínio + validação
de entrada de uma vez, com um separador entre cada saída:

```bash
uv run python manage.py shell -c "
from django.test import Client
c = Client()

# caminho feliz
r = c.post('/endereco/selecionar/', {'codlog': '156566', 'numero': '300'})
print('FELIZ', r.status_code)
print(r.content.decode()[:500])
print('---')

# erro de domínio: número fora da faixa de numeração
r = c.post('/endereco/selecionar/', {'codlog': '156566', 'numero': '999999'})
print('NUMERACAO', r.status_code)
print(r.content.decode()[:500])
print('---')

# erro de domínio: codlog sem segmentos
r = c.post('/endereco/selecionar/', {'codlog': '999999', 'numero': '10'})
print('SEGMENTO', r.status_code)
print(r.content.decode()[:500])
print('---')

# erro de validação Pydantic (ver skill pydantic-validation-errors)
r = c.post('/endereco/selecionar/', {'codlog': '156566', 'numero': 'abc'})
print('VALIDACAO', r.status_code)   # 422 esperado
print(r.content.decode()[:500])
"
```

Isso valida, num só comando: o status 200 + geometria certa no caminho feliz, cada exceção de
domínio caindo no aviso semântico correto (`mapping/_aviso.html`), e o 422 automático do
`PydanticValidationMiddleware` — sem precisar de browser nem de dados de sessão/CSRF.

## Limitações do `Client()`

É uma chamada WSGI simulada no mesmo processo: não abre porta, não executa JS, não enforce CSRF.
Não serve para verificar renderização real do Leaflet/JS, comportamento real de CSRF/cookies, ou
arquivos estáticos servidos — para isso, hoje, use um browser normalmente. O pipeline via
`runserver` + `curl` foi tentado nesta skill e removido: não ficou bom (atrito de CSRF ao bater
com `curl` cru); esse caso vai ser resolvido melhor numa iteração futura desta skill.

## O que não fazer

- Não tente montar token CSRF manualmente por `curl` para simular um POST — use `Client()` (que já
  ignora CSRF) para esse tipo de verificação de view.
- Não confunda este smoke test com os testes automatizados de `pytest` — este pipeline é manual,
  sob demanda, e não fica versionado como suíte de testes (CLAUDE.md §13).
