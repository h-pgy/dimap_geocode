---
spec: infraestrutura/003
versao: v3
atualizado_em: 2026-07-07
implementado: true
changelog:
  - v1: versão inicial (já implementada — registro retroativo)
  - v2: "Patch 001 — warmup movido de AppConfig.ready() para os entrypoints web (wsgi/asgi): elimina o aquecimento duplicado do autoreloader do runserver e o pedágio em management commands"
  - v3: "Patch 002 — catálogos viram singletons de fato (via __new__): qualquer instanciação avulsa devolve a instância única já aquecida"
---

# SPEC infraestrutura/003 — Catalog isolado + warmup no startup do Django

- [x] **Implementada**

## User story
Como desenvolvedor, quero que os dados de lookup usados pelos matchers (logradouros e
contribuintes) sejam carregados uma única vez no startup do processo Django, para que a
primeira busca de cada usuário não pague o custo de I/O da carga do parquet e para que os
dois domínios sigam o mesmo padrão de acesso a dados.

## Critérios de aceite
- [x] `contribuinte_match` tem uma classe `Catalog` própria (`ContribuinteCatalog`), separada
      do `Matcher`, seguindo o mesmo padrão estrutural de `LogradouroCatalog`.
- [x] O `Matcher` de cada domínio recebe o `Catalog` por injeção de dependência no construtor
      (composição), não instancia dados diretamente.
- [x] Cada `__init__.py` de domínio instancia o catalog **uma única vez** no import do módulo
      e expõe essa instância (`logradouro_catalog`, `contribuinte_catalog`) para permitir o
      warmup — sem implementar lógica no `__init__.py` (só reexport).
- [x] Cada `Catalog` expõe um método `aquecer()` que força a leitura dos dados (acessa as
      `ttl_cached_property` internas), sem alterar o comportamento de cache (TTL) já existente.
- [x] O app Django "dono" de cada domínio (`apps/lote_matcher` para contribuinte,
      `apps/logradouro_matcher` para logradouro) implementa `AppConfig.ready()` chamando
      `catalog.aquecer()`, carregando os dados **antes** da primeira request.

## Contexto e decisões de arquitetura

`logradouros_match` já seguia o padrão desejado: `LogradouroCatalog` isola a leitura dos
parquets (`ttl_cached_property`) da lógica de matching, e `LogradouroMatcher` /
`LiteralLogradouroMatcher` recebem o catalog por composição. `contribuinte_match` não seguia
esse padrão — o `ContribuinteMatcher` lia o parquet diretamente numa `ttl_cached_property` do
próprio matcher, misturando persistência/I/O com a lógica de match (viola §10.1).

Isso também escondia um sintoma de performance: como a carga é *lazy* (só acontece no
primeiro acesso à property), a primeira sugestão de contribuinte depois do processo subir
pagava o custo de leitura do parquet dentro do ciclo de request/response — daí a sensação de
"primeira busca lenta, depois rápido".

A correção tem duas partes:
1. **Padronizar a estrutura** — extrair `ContribuinteCatalog`, no mesmo molde de
   `LogradouroCatalog`, e injetar no `ContribuinteMatcher`. `ContribuinteMatcher.__call__`
   passou a delegar a um `_pipeline` (convenção de §10.4: `__call__` fino, pipeline orquestra).
2. **Tirar a carga do ciclo de request** — cada `Catalog` ganhou um método `aquecer()` que
   força a leitura (acessando as `ttl_cached_property`). O `AppConfig.ready()` do app dono de
   cada domínio chama esse `aquecer()` no startup do processo Django, então quando a primeira
   request chega os dados já estão em cache.

**Camadas envolvidas:** domínio (`services/domain/*/catalog.py`, `matcher.py`, `__init__.py`)
e orquestração/infraestrutura (`apps/*/apps.py`, ponto de entrada do Django para o warmup).
Nenhuma lógica de negócio foi adicionada às `AppConfig` — elas só disparam o warmup já
implementado no domínio, o que é orquestração (§3.3).

## Peças de referência a compor
- `@services/domain/logradouros_match/catalog.py` → `LogradouroCatalog`: modelo do padrão
  replicado em `contribuinte_match`.
- `@services/utils/cache.py` → `ttl_cached_property`: mecanismo de cache já usado nos dois
  domínios, reaproveitado sem alteração.
- `@services/domain/contribuinte_match/catalog.py` → `ContribuinteCatalog` (nova): mesma
  estrutura, com `enderecos_fiscais` como `ttl_cached_property` e `aquecer()`.

## Snippets sugeridos

```python
# services/domain/<dominio>/catalog.py
class XCatalog:
    @ttl_cached_property(ttl_seconds=...)
    def _dado(self) -> ...: ...

    def aquecer(self) -> None:
        _ = self._dado  # força a leitura fora do ciclo de request


# apps/<app_dono>/apps.py
class XConfig(AppConfig):
    def ready(self) -> None:
        from services.domain.<dominio> import x_catalog
        x_catalog.aquecer()
```

## Fora de escopo
- Migrar o cache de lookup para Redis (roadmap futuro, fora desta SPEC).
- Aplicar o mesmo padrão a `codlog_match` (mesmo problema estrutural, não pedido nesta
  iteração).
- Mudar o TTL de 3600s / 24h já existentes em cada domínio.

## Notas de teste
Verificar que `Catalog.aquecer()` popula o cache sem exigir uma chamada ao `Matcher`.
Verificar que `AppConfig.ready()` de `lote_matcher` e `logradouro_matcher` deixam
`contribuinte_catalog` / `logradouro_catalog` com cache populado logo após `django.setup()`,
antes de qualquer request. Verificar que o comportamento de matching não mudou (mesmos testes
de `test_matcher.py` antes e depois da extração do catalog).

## Patches

### Patch 001 (v2) — warmup só em processo que serve requests (entrypoints wsgi/asgi)

- [x] **Aplicado**

**Sintoma.** Ao subir o `runserver`, o warmup roda **4 vezes** (2 catálogos × 2 processos): o
autoreloader do Django cria um processo pai (watcher de arquivos) e um filho (que serve as
requests), e ambos executam `django.setup()` → `AppConfig.ready()` → `aquecer()`. O aquecimento
do pai é 100% desperdiçado (~17s a mais de startup, dominados pelo `ContribuinteCatalog`), e se
repete a cada restart do autoreload. Além disso, **todo management command** (`migrate`, `shell`,
comandos do pipeline de dados) também passa por `ready()` e paga o mesmo pedágio de ~17s, mesmo
quando nunca toca os catálogos.

**Causa.** O ponto de disparo escolhido na v1 — `AppConfig.ready()` — roda em *qualquer*
`django.setup()`, não apenas em processos que vão servir requests.

**Correção.** Mover o disparo do warmup de `AppConfig.ready()` para os **entrypoints web**
(`config/wsgi.py` e `config/asgi.py`), que são carregados **somente** por processos que servem
requests:

- filho do `runserver` (carrega `WSGI_APPLICATION = "config.wsgi.application"`) → aquece ✓
- servidor de produção (gunicorn/uvicorn importam `config.wsgi`/`config.asgi`) → aquece ✓
- pai do autoreloader (nunca carrega o handler) → não aquece ✓
- management commands (não importam wsgi/asgi) → não aquecem ✓

Isso resolve os dois sintomas com um único mecanismo e **sem heurística** de `sys.argv`/`RUN_MAIN`.
Os `ready()` de `apps/logradouro_matcher` e `apps/lote_matcher` (que só disparavam o warmup) são
removidos. Nada muda nos catálogos: as `ttl_cached_property` continuam lazy, então um processo que
não aqueceu (ex.: um script do pipeline que consulte um matcher) simplesmente paga a carga no
primeiro acesso — comportamento pré-v1, adequado para execução apartada do runtime web.

O warmup agregado vira uma função de domínio (os entrypoints em `config/` só a chamam —
orquestração, sem lógica):

```python
# services/domain/warmup.py (reexportada em services/domain/__init__.py)
from services.domain.contribuinte_match import contribuinte_catalog
from services.domain.logradouros_match import logradouro_catalog


def aquecer_catalogos() -> None:
    logradouro_catalog.aquecer()
    contribuinte_catalog.aquecer()


# config/wsgi.py (idem em config/asgi.py, após criar `application`)
application = get_wsgi_application()

from services.domain import aquecer_catalogos

aquecer_catalogos()
```

**Critérios observáveis.**
- `manage.py runserver` imprime cada `[XCatalog] aquecendo cache...` **uma única vez** (2 linhas
  no total, não 4).
- `manage.py check` / `migrate` / `shell -c "pass"` não imprimem nenhuma linha de aquecimento e
  sobem sem o pedágio de ~17s.
- Primeira request após o startup continua rápida (cache já populado no processo que serve).

### Patch 002 (v3) — catálogos como singletons de fato (via `__new__`)

- [x] **Aplicado**

**Motivação.** Os catálogos eram "singletons por convenção": a instância canônica vive no
`__init__.py` de cada domínio, mas nada impedia instanciações avulsas — e elas existem: os
matchers têm default `catalog or XCatalog()` no construtor, que cria uma **cópia fria** (cache
por instância) sempre que alguém constrói um matcher sem injetar o catálogo. Com o warmup do
Patch 001 valendo só para a instância canônica, uma cópia fria paga a carga do parquet dentro
do ciclo de request — exatamente o que a SPEC veio eliminar.

**Correção.** `LogradouroCatalog` e `ContribuinteCatalog` implementam o padrão **Singleton**
sequestrando `__new__`: a primeira construção cria e guarda a instância na classe; construções
seguintes devolvem a mesma instância. Consequências:

- `XCatalog()` em qualquer ponto do código devolve a instância única (aquecida, se o processo
  serviu warmup) — o default dos matchers deixa de ser um risco.
- No `ContribuinteCatalog`, o `__init__` roda a cada "construção" (comportamento do protocolo
  Python); o parâmetro `nome_arquivo` é gravado **apenas na primeira** construção (guard com
  `hasattr`) para não sobrescrever o estado do singleton — "first wins".
- **O singleton vale só para a classe exata:** subclasses (os `FakeCatalog` dos testes, com
  construtores e dados próprios) constroem instâncias normais — sem o bypass, uma subclasse
  receberia a instância da classe base ou viraria singleton ela mesma, quebrando os fakes.
- **Isolamento de testes:** cada classe ganha um classmethod `resetar_instancia()` que descarta
  a instância única (a próxima construção nasce fria). Um fixture **autouse** no
  `tests/conftest.py` reseta os dois catálogos entre testes — sem isso, o cache TTL do primeiro
  teste (dados sintéticos) vazaria para todos os demais. Fora de testes, `resetar_instancia()`
  não é chamado.

```python
class LogradouroCatalog:
    _instancia: ClassVar["LogradouroCatalog | None"] = None

    def __new__(cls, *args: object, **kwargs: object) -> "LogradouroCatalog":
        # singleton só na classe exata: subclasses (fakes de teste) constroem normalmente
        if cls is not LogradouroCatalog:
            return super().__new__(cls)
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
        return cls._instancia

    @classmethod
    def resetar_instancia(cls) -> None:
        cls._instancia = None
```

**Critérios observáveis.**
- `XCatalog() is XCatalog()` → `True` nos dois catálogos.
- Construir um matcher sem injetar catálogo (`LogradouroMatcher()`) não dispara nova leitura de
  parquet se o processo já aqueceu.
- Suíte de testes existente continua verde (isolamento garantido pelo reset autouse).
