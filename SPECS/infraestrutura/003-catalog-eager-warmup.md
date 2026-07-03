---
spec: infraestrutura/003
versao: v1
atualizado_em: 2026-07-01
implementado: true
changelog:
  - v1: versão inicial (já implementada — registro retroativo)
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

_Nenhum patch registrado até o momento._
