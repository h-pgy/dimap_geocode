---
spec: match_logradouros/007
versao: v1
atualizado_em: 2026-07-08
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC match_logradouros/007 — Catalog isolado + warmup para `codlog_match`

- [x] **Implementada**

## User story
Como desenvolvedor, quero que o `codlog_match` siga o mesmo padrão de `Catalog` dos demais
domínios de lookup (logradouros e contribuintes) — dados isolados numa classe `Catalog`
singleton, injetada no matcher por composição e aquecida no startup do processo web — para que
a leitura do parquet saia do ciclo de request/response e o domínio pare de misturar I/O de
persistência com lógica de matching.

## Critérios de aceite
- [ ] `codlog_match` tem uma classe `CodlogCatalog` própria, separada do `CodlogMatcher`,
      seguindo o mesmo padrão estrutural de `LogradouroCatalog` / `ContribuinteCatalog`
      (singleton via `__new__` restrito à classe exata, `resetar_instancia()`, `ttl_cached_property`,
      `aquecer()` com log de tempo).
- [ ] O `CodlogMatcher` recebe o `CodlogCatalog` por injeção de dependência no construtor
      (composição) e **não** lê o parquet diretamente — a `ttl_cached_property` que lia
      `nomes_logradouros.parquet` sai do matcher e passa para o catalog.
- [ ] `CodlogMatcher.__call__` fica fino e delega a um `_pipeline` (convenção §10.4), preservando
      exatamente a lógica de matching atual (prefixo quando `len < 5`, igualdade quando `== 5`,
      `head(limite)`, mapeamento para `CodlogMatchOutput`).
- [ ] O `__init__.py` de `codlog_match` instancia o catalog **uma única vez** no import do módulo e
      expõe essa instância como `codlog_catalog` (só reexport, sem lógica no `__init__.py`).
- [ ] `codlog_catalog.aquecer()` passa a ser chamado no warmup agregado
      (`services/domain/warmup.py::aquecer_catalogos()`), junto de logradouros e contribuintes, de
      modo que a primeira busca por codlog após o startup já encontre o cache populado.
- [ ] O comportamento observável do matching não muda: os mesmos inputs produzem os mesmos
      `CodlogMatchOutput` de antes.
- [ ] O TTL do cache do `CodlogCatalog` é `24h`, padronizado com o `LogradouroCatalog` (que lê o
      mesmo `nomes_logradouros.parquet`), e não mais o `3600s` do matcher antigo.

## Contexto e decisões de arquitetura

**Camadas envolvidas:** domínio (`services/domain/codlog_match/`) e infraestrutura de startup
(`services/domain/warmup.py`, já chamado por `config/wsgi.py`/`asgi.py`). É um **refactor
estrutural + warmup**, sem regra de negócio nova.

Hoje o `CodlogMatcher` viola o mesmo ponto que a SPEC `infraestrutura/003` corrigiu em
`contribuinte_match`: ele lê `nomes_logradouros.parquet` numa `ttl_cached_property` do próprio
matcher (`_dataframe`), misturando persistência/I/O com a lógica de match (fere §3.2 e §10.1). Como
essa carga é *lazy*, a primeira busca por codlog depois do processo subir paga a leitura do parquet
dentro do ciclo de request. A SPEC 003 deixou explícito, em "Fora de escopo", que aplicar o padrão
`Catalog` a `codlog_match` ficaria para depois — é exatamente esta iteração.

A correção segue o molde já consolidado (skill `catalogos-lookup`):
1. **Extrair `CodlogCatalog`** — a leitura do parquet e a preparação da coluna auxiliar `_codlog5`
   vão para uma `ttl_cached_property` do catalog. O matcher recebe o catalog por composição
   (`catalog: CodlogCatalog | None = None`, default `CodlogCatalog()` → a instância singleton).
2. **Tirar a carga do ciclo de request** — o `CodlogCatalog` ganha `aquecer()`, adicionado ao
   `aquecer_catalogos()` central. Como o warmup já roda **somente** em `config/wsgi.py`/`asgi.py`
   (decisão do Patch 001 da SPEC 003), **não** é preciso mexer em nenhum `AppConfig.ready()` — basta
   somar uma linha ao warmup agregado.
3. **Singleton de fato** — `CodlogCatalog` sequestra `__new__` como os outros dois catálogos, para
   que o default `CodlogCatalog()` do matcher nunca crie uma cópia fria que pague a carga em request.

**Fronteira catalog × matcher.** Seguindo o padrão do `ContribuinteCatalog` (que expõe o
`DataFrame` preparado e deixa o matcher montar o filtro), o `CodlogCatalog` expõe o `DataFrame` já
com `_codlog5` pré-calculado; a **decisão de prefixo vs. igualdade** continua no matcher, que é onde
a lógica de match deve morar. O catalog cuida só de "carregar + preparar o índice".

**Nota sobre o parquet compartilhado.** `nomes_logradouros.parquet` também é lido pelo
`LogradouroCatalog` (em `_rows`). Esta SPEC **mantém os dois catálogos independentes** — cada
domínio (`codlog_match` e `logradouros_match`) tem o seu, preservando as fronteiras de módulo (§10.1)
e evitando que `codlog_match` passe a depender de `logradouros_match`. Unificar as duas leituras para
deduplicar memória é decisão separada e fica **fora de escopo** (ver abaixo).

## Peças de referência a compor
- `@services/domain/logradouros_match/catalog.py` → `LogradouroCatalog`: modelo do padrão
  (singleton via `__new__`, `resetar_instancia()`, `aquecer()`) a replicar.
- `@services/domain/contribuinte_match/catalog.py` → `ContribuinteCatalog`: referência do catalog
  que **recebe `nome_arquivo` no `__init__`** com guard `hasattr` (o mesmo caso do codlog, que tem
  `NOME_ARQUIVO_PADRAO`) e que **expõe o `DataFrame` preparado** para o matcher filtrar.
- `@services/utils/cache.py` → `ttl_cached_property`: mecanismo de cache reaproveitado sem alteração.
- `@services/utils/io.py` → `read_parquet_from_data`: leitura do parquet, já usada pelo matcher atual.
- `@services/domain/warmup.py` → `aquecer_catalogos()`: ponto central de warmup ao qual o novo
  `codlog_catalog.aquecer()` é somado.
- `@services/domain/codlog_match/matcher.py` → `CodlogMatcher`: matcher a refatorar (lógica de
  `_filtrar` / `_mapear_resultados` preservada, apenas passando a ler do catalog).

## Snippets sugeridos

```python
# services/domain/codlog_match/catalog.py
import time
from typing import ClassVar

import pandas as pd

from services.utils.cache import ttl_cached_property
from services.utils.io import read_parquet_from_data

NOME_ARQUIVO_PADRAO = "nomes_logradouros.parquet"
DATA_TTL_SECONDS = 24 * 60 * 60  # padronizado com LogradouroCatalog (mesmo parquet)


class CodlogCatalog:
    _instancia: ClassVar["CodlogCatalog | None"] = None

    def __new__(cls, *args: object, **kwargs: object) -> "CodlogCatalog":
        # singleton só na classe exata: subclasses (fakes de teste) constroem normalmente
        if cls is not CodlogCatalog:
            return super().__new__(cls)
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
        return cls._instancia

    @classmethod
    def resetar_instancia(cls) -> None:
        cls._instancia = None

    def __init__(self, nome_arquivo: str = NOME_ARQUIVO_PADRAO) -> None:
        # __init__ roda a cada "construção" do singleton — só a primeira grava o arquivo
        if not hasattr(self, "_nome_arquivo"):
            self._nome_arquivo = nome_arquivo

    @ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
    def logradouros(self) -> pd.DataFrame:
        df = pd.DataFrame(read_parquet_from_data(self._nome_arquivo))
        df["_codlog5"] = df["codlog"].str[:5]
        return df

    def aquecer(self) -> None:
        print("[CodlogCatalog] aquecendo cache...")
        inicio = time.perf_counter()
        _ = self.logradouros
        duracao = time.perf_counter() - inicio
        print(f"[CodlogCatalog] cache aquecido em {duracao:.2f}s")
```

```python
# services/domain/codlog_match/matcher.py  (refatorado — lógica de match inalterada)
import pandas as pd

from .catalog import CodlogCatalog
from .models import CodlogMatchInput, CodlogMatchOutput


class CodlogMatcher:
    def __init__(self, catalog: CodlogCatalog | None = None) -> None:
        self._catalog = catalog or CodlogCatalog()

    def __call__(self, payload: CodlogMatchInput) -> list[CodlogMatchOutput]:
        return self._pipeline(payload)

    def _pipeline(self, payload: CodlogMatchInput) -> list[CodlogMatchOutput]:
        df = self._filtrar(payload.input_codlog)
        return self._mapear_resultados(df.head(payload.limite))

    def _filtrar(self, input_codlog: str) -> pd.DataFrame:
        df = self._catalog.logradouros
        if len(input_codlog) < 5:
            return df[df["_codlog5"].str.startswith(input_codlog)]
        return df[df["_codlog5"] == input_codlog]

    # _mapear_resultados permanece exatamente como está hoje
```

```python
# services/domain/codlog_match/__init__.py  (só reexport)
from .catalog import CodlogCatalog
from .matcher import CodlogMatcher
from .models import CodlogMatchInput, CodlogMatchOutput

_catalog = CodlogCatalog()
match_codlog = CodlogMatcher(catalog=_catalog)
codlog_catalog = _catalog

__all__ = [
    "CodlogCatalog",
    "CodlogMatcher",
    "match_codlog",
    "codlog_catalog",
    "CodlogMatchInput",
    "CodlogMatchOutput",
]
```

```python
# services/domain/warmup.py
from services.domain.codlog_match import codlog_catalog
from services.domain.contribuinte_match import contribuinte_catalog
from services.domain.logradouros_match import logradouro_catalog


def aquecer_catalogos() -> None:
    logradouro_catalog.aquecer()
    contribuinte_catalog.aquecer()
    codlog_catalog.aquecer()
```

## Fora de escopo
- **Unificar a leitura de `nomes_logradouros.parquet`** entre `CodlogCatalog` e `LogradouroCatalog`
  para deduplicar memória. Esta SPEC mantém os catálogos independentes por fronteira de módulo;
  eventual unificação é decisão à parte.
- **Usar o `digito_verificador`** no filtro. O `CodlogMatchInput.digito_verificador` e o ponto de
  extensão `_validar_dv` continuam como estão — esta SPEC não altera o critério de matching.
- **Migrar o cache de lookup para Redis** (roadmap futuro, já descartado para este app).

## Notas de teste
- Verificar que `CodlogCatalog().logradouros` popula o cache lendo o parquet e que `aquecer()`
  força essa leitura sem passar pelo matcher.
- Verificar que `CodlogCatalog() is CodlogCatalog()` → `True` (singleton) e que construir
  `CodlogMatcher()` sem injetar catalog não dispara nova leitura de parquet quando o processo já
  aqueceu.
- Verificar que o matching não mudou: reexecutar os casos existentes de `codlog_match` (prefixo com
  `len < 5`, código exato com `len == 5`, respeito ao `limite`) antes e depois da extração e comparar
  os `CodlogMatchOutput`.
- Ao mexer no isolamento de testes: somar `CodlogCatalog.resetar_instancia()` ao fixture `autouse`
  de `tests/conftest.py` (hoje reseta só `LogradouroCatalog` e `ContribuinteCatalog`), para o cache
  TTL de um teste não vazar para os demais.

## Patches

_Nenhum patch registrado até o momento._
