---
name: test-django-views
description: Pipeline para smoke test manual de views Django/HTMX do DIMAP GeoCoder — o passo de validação funcional que complementa a suíte de testes definida na SPEC (política de testes/TDD do CLAUDE.md); não substitui nem dispensa os testes automatizados. Use sempre que acabar de implementar ou alterar uma view e precisar confirmar o comportamento real (status code, HTML do partial, caminhos de erro) antes de reportar a tarefa como concluída, sem depender de browser.
---

# Smoke test de views Django — `django.test.Client` via `manage.py shell -c`

## Quando usar

Depois de implementar/alterar uma view. O projeto é **TDD** (política de testes do CLAUDE.md): a
validação principal é a suíte que a SPEC definiu e que foi **escrita antes** do código. Este smoke
test é o **passo complementar**, para o que o teste automatizado cobre mal — o HTML do partial
renderizado e o comportamento real da interface. Serve para:

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

## O smoke test escreve no banco de DESENVOLVIMENTO — sempre em transação desfeita

`manage.py shell -c` abre o **banco real de desenvolvimento**, não o `test_<db>` que o pytest cria e
descarta. Fixture montada solta no shell (unidade, tipo de unidade, perfil, cargo) **fica gravada**
e vira lixo permanente no sistema — foi assim que unidades como `U-login`/`U9600001` apareceram na
listagem.

Toda fixture do smoke test nasce e morre dentro de uma `transaction.atomic()` que termina em
rollback forçado:

```bash
uv run python manage.py shell -c "
from django.db import transaction
from django.test import Client
from apps.unidades.models import TipoUnidade, Unidade

class Desfazer(Exception):
    pass

try:
    with transaction.atomic():
        tipo = TipoUnidade.objects.create(
            nome='Tipo Smoke',
            nivel=10,
            pode_ser_raiz=True,
            nivel_minimo_titular=1,
        )
        unidade = Unidade.objects.create(nome='Unidade Smoke', sigla='SMOKE', tipo=tipo)

        r = Client().get('/unidades/')
        print('STATUS', r.status_code)
        print(r.content.decode()[:2000])

        # Nada do que foi criado acima sobrevive a esta linha.
        raise Desfazer
except Desfazer:
    pass
"
```

- O `Client()` roda no mesmo processo e na mesma conexão, então as requisições **enxergam** as
  fixtures dentro da transação — inclusive views que abrem `atomic()` própria (viram savepoint).
- A exceção própria (`Desfazer`) é o que garante o rollback sem engolir erro de verdade: qualquer
  outra exceção continua subindo e aparecendo no stdout.
- **Só leitura** (GET de página, busca, render de partial): não precisa de transação — mas também
  não custa nada abrir uma.

## O que não fazer

- Não crie fixture (unidade, perfil, cargo) direto no shell sem `transaction.atomic()` + rollback:
  o banco do shell é o de desenvolvimento, e o registro fica lá para sempre.
- Não tente montar token CSRF manualmente por `curl` para simular um POST — use `Client()` (que já
  ignora CSRF) para esse tipo de verificação de view.
- Não confunda este smoke test com os testes automatizados de `pytest` — este pipeline é manual e
  não fica versionado como suíte. Ele **não dispensa** os testes da SPEC, que no TDD vêm antes do
  código (política de testes do CLAUDE.md).
