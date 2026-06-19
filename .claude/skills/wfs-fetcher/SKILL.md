---
name: wfs-fetcher
description: Como usar o integrador WFS (services/integrations/wfs) do DIMAP GeoCoder para extrair features paginadas de um GeoServer (GeoSampa/MDSF). Use ao escrever scripts de ingestão, matchers ou qualquer código que consuma dados oficiais da PMSP via WFS — montagem de WfsConnectionConfig/WfsFeatureRequest, filtros CQL, paginação e tratamento de erros/retries.
---

# WFS Fetcher — `services.integrations.wfs`

Cliente WFS reutilizável, tipado e **agnóstico de Django**. Pagina automaticamente as features
de qualquer camada de um GeoServer (GeoSampa hoje, MDSF depois) e devolve um
`WfsFeatureCollection` Pydantic por página.

## Regras de fronteira (não violar)

- **O domínio nunca lê settings.** `WfsFetcher` não importa Django. A configuração de conexão e a
  política de retry chegam por **DTOs injetados** no construtor. Quem lê `settings` é a
  **orquestração** (management command / view). Ver §3.3 do CLAUDE.md.
- **Importe sempre pelo nível superior** `services.integrations.wfs` — nunca alcance submódulos
  internos (`.fetcher`, `.models`). Tudo que você precisa está exposto no `__init__.py`.
- **Não monte URLs nem params à mão.** Use os DTOs (`WfsFeatureRequest`, `CqlFilter`).
- **Consuma como gerador.** O fetcher é callable e pagina sob demanda; não materialize tudo de uma
  vez se a camada for grande.

## O que é exportado

```python
from services.integrations.wfs import (
    WfsFetcher,             # cliente callable, paginado
    WfsConnectionConfig,    # COMO conectar (domain/endpoint/namespace/service/version)
    WfsFeatureRequest,      # O QUE pedir (camada, filtro, count, propriedades…)
    WfsFeatureCollection,   # envelope de saída (GeoJSON FeatureCollection)
    WfsRetryPolicy,         # resiliência (timeout, retries, backoff aleatório)
    CqlFilter, CqlPredicate,# filtros CQL estruturados com escape de literais
    WfsHttpError, WfsInvalidResponseError, WfsTimeoutError, WfsConnectionError,
    utils,                  # helpers cql_eq, cql_like, … (atalhos de CqlFilter)
)
```

## Uso básico

```python
from services.integrations.wfs import WfsConnectionConfig, WfsFeatureRequest, WfsFetcher

config = WfsConnectionConfig(
    domain="wfs.geosampa.prefeitura.sp.gov.br",
    endpoint="geoserver/ows",
    namespace="geoportal",      # vira typeName "geoportal:<camada>"
    # service="WFS", version="2.0.0" são defaults
)

request = WfsFeatureRequest(
    nome_camada="logradouro",
    count=10_000,                       # tamanho da página (vira maxFeatures)
    property_names=["codlog", "nm_logradouro"],  # só os campos que precisa
)

fetcher = WfsFetcher(config)

# fetcher é callable → retorna um GERADOR de WfsFeatureCollection (uma por página)
for page in fetcher(request):
    for feature in page.features:
        props = feature.properties          # dict[str, Any]
        geom = feature.geometry             # WfsGeometry | None (type + coordinates)
        ...
```

A paginação é automática: o gerador usa `numberMatched` e o tamanho de cada página para parar
sozinho (ou quando uma página vier vazia). `fetcher.features_fetched_count` acumula o total.

## Filtros CQL (parte sensível — vira query crua)

Filtros viram CQL contra o GeoServer. **Não concatene strings**: use `CqlFilter`/`CqlPredicate`
(escapam aspas simples automaticamente) ou os atalhos em `utils`.

```python
from services.integrations.wfs import CqlFilter, CqlPredicate, WfsFeatureRequest, utils

# Atalhos para um predicado só:
f = utils.cql_eq("codlog", 12345678)
f = utils.cql_like("nm_logradouro", "PAULISTA%")   # curinga % é por sua conta

# Composto (AND/OR):
f = CqlFilter(
    predicates=[
        CqlPredicate(field="cd_tipo", op="=", value="AV"),
        CqlPredicate(field="nm_logradouro", op="ILIKE", value="PAULISTA%"),
    ],
    logic="AND",   # ou "OR"
)

request = WfsFeatureRequest(nome_camada="logradouro", cql_filter=f)
```

Ops válidos: `=`, `<>`, `>`, `<`, `>=`, `<=`, `LIKE`, `ILIKE`. Literais string são delimitados e
têm aspas simples duplicadas (ECQL) — `O'Brien` → `'O''Brien'`.

**Escape-hatch `raw_cql`:** `CqlFilter(raw_cql="...")` bypassa o escape. Risco de injeção/filtro
malformado — só com input confiável.

> Borda conhecida: alguns GeoServers recusam `cql_filter` + `bbox` juntos. Prefira embutir o bbox
> no próprio CQL.

## Resiliência (timeout + retries)

Camadas grandes sobrecarregam o GeoServer. `WfsRetryPolicy` (injetada, opcional) controla
timeout e retentativas com backoff aleatório. **Sem ela, usa defaults** (timeout 30s, 3 retries):

```python
from services.integrations.wfs import WfsRetryPolicy, WfsFetcher

policy = WfsRetryPolicy(
    request_timeout_seconds=30.0,
    max_retries=3,              # limite DURO: 1 tentativa + 3 retentativas; sem loop infinito
    retry_wait_min_seconds=1.0,
    retry_wait_max_seconds=5.0, # deve ser >= min, senão ValueError na construção
)
fetcher = WfsFetcher(config, retry_policy=policy, verbose=True)
```

Só **falhas de rede transitórias** (`Timeout`, `ConnectionError`) disparam retry. Esgotados os
retries:

- timeout → `WfsTimeoutError`
- conexão → `WfsConnectionError`

(ambas herdam de `WfsHttpError`, com `__cause__` apontando a última falha real).

Erros **não** transitórios propagam na 1ª ocorrência, sem retry:

- status HTTP de erro → `WfsHttpError`
- corpo não-JSON → `WfsInvalidResponseError`

## Orquestração: lendo o settings (management command / view)

O **domínio recebe os DTOs prontos**. A orquestração lê `settings` e injeta. Padrão real do
projeto (`apps/logradouro_matcher/management/commands/extrair_nomes_logradouros.py`):

```python
from django.conf import settings
from services.integrations.wfs import WfsConnectionConfig, WfsRetryPolicy

config = WfsConnectionConfig(
    domain=settings.WFS_DOMAIN,
    endpoint=settings.WFS_ENDPOINT,
    namespace=settings.WFS_NAMESPACE,
    service=settings.WFS_SERVICE,
    version=settings.WFS_VERSION,
)
retry_policy = WfsRetryPolicy(
    request_timeout_seconds=settings.WFS_REQUEST_TIMEOUT_SECONDS,
    max_retries=settings.WFS_MAX_RETRIES,
    retry_wait_min_seconds=settings.WFS_RETRY_WAIT_MIN_SECONDS,
    retry_wait_max_seconds=settings.WFS_RETRY_WAIT_MAX_SECONDS,
)
# command só faz parsing + chama o script; o script repassa config/policy ao WfsFetcher
result = run(config, request, retry_policy=retry_policy, verbose=...)
```

Trocar GeoSampa por MDSF = passar outra `WfsConnectionConfig`. Nenhum código de domínio muda.

## Composição em scripts/domínio (padrão recomendado)

Não acople seu extractor diretamente ao `WfsFetcher`: dependa do **callable** (mais testável).
Padrão usado em `services/scripts/logradouros`:

```python
from collections.abc import Callable, Iterable
from services.integrations.wfs import WfsFeatureCollection, WfsFeatureRequest

WfsBatches = Callable[[WfsFeatureRequest], Iterable[WfsFeatureCollection]]

class MeuExtractor:
    def __init__(self, fetcher: WfsBatches) -> None:   # recebe o callable, não a classe
        self.fetcher = fetcher

    def __call__(self, request) -> list[...]:
        wfs_request = WfsFeatureRequest(nome_camada=request.layer_name, count=10_000)
        for page in self.fetcher(wfs_request):
            ...
```

No `run(...)`: `extractor = MeuExtractor(WfsFetcher(config, retry_policy=retry_policy))`.
Em teste: injete um fake que devolve páginas prontas — sem rede.

## Saída: `WfsFeatureCollection`

```
WfsFeatureCollection
├─ type: "FeatureCollection"
├─ features: list[WfsFeature]
│    ├─ id: str | None
│    ├─ geometry: WfsGeometry | None  (type: str, coordinates: Any)
│    └─ properties: dict[str, Any]
├─ total_features / number_matched / number_returned: int | None
│    (tolera "unknown"/ausente → None)
├─ crs: dict | None
└─ bbox: list[float] | None
```

## Notas de teste

- **Mocke `requests.get`** — nenhum teste bate na rede. Patch em
  `services.integrations.wfs.fetcher.requests.get`.
- Em testes de retry, mocke também `time.sleep` e `random.uniform` (não durma de verdade).
- Cubra: página única; multi-página por `numberMatched`; vazio; `raise_for_status` → `WfsHttpError`;
  não-JSON → `WfsInvalidResponseError`; esgotar retries → `WfsTimeoutError`/`WfsConnectionError`.
- Para o domínio, prefira injetar um fake callable (ver composição acima) em vez de mockar HTTP.

## Borda de versão WFS

`to_query_params` emite `maxFeatures` (WFS 1.x). GeoSampa responde a `maxFeatures` mesmo com
`version="2.0.0"`. Se um GeoServer exigir `count` (2.0.0 estrito), mapear por versão e registrar
em Patches na SPEC `SPECS/ingestao_dados/001-wfs-fetcher.md`.
