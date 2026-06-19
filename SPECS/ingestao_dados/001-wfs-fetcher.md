---
spec: ingestao-dados/001
versao: v3
atualizado_em: 2026-06-19
changelog:
  - v3: planeja a fiação da WfsRetryPolicy nos 3 management commands de ingestão (settings → DTO → run → WfsFetcher) — ver Patches
  - v2: planeja resiliência a timeout/conexão no WfsFetcher (retries limitados + backoff aleatório + WfsTimeoutError/WfsConnectionError) — ver Patches
  - v1: versão inicial
---

# SPEC ingestao-dados/001 — Integration WFS Fetcher (GeoSampa → MDSF)

## User story
Como desenvolvedor do domínio, quero um cliente WFS reutilizável e tipado que extraia
features paginadas de qualquer camada de um GeoServer (GeoSampa hoje, MDSF depois),
para que os matchers e scripts de ingestão (logradouros, lotes, endereços) consumam os
dados oficiais da PMSP por composição, sem cada um reimplementar paginação, montagem de
query e parsing do envelope WFS.

## Critérios de aceite
- [ ] Existe `services/integrations/wfs/` com a classe `WfsFetcher`, **callable** (`__call__` delega ao gerador de lotes).
- [ ] A classe **não importa Django** (nem `settings`, nem nada de `config/`): a configuração de conexão chega **por DTO Pydantic injetado** no `__init__`.
- [ ] Entrada modelada em Pydantic: `WfsFeatureRequest`, incluindo filtros CQL estruturados (`CqlFilter` + `CqlPredicate`) com **escape de literais**.
- [ ] Saída modelada em Pydantic no padrão WFS/GeoJSON: `WfsFeatureCollection` → `WfsFeature` → `WfsGeometry`.
- [ ] `fetch_feature_batches(request)` é um **gerador** que pagina automaticamente usando `numberMatched`, rendendo um `WfsFeatureCollection` por página.
- [ ] Erro HTTP propaga (`raise_for_status`); corpo não-JSON vira `ValueError` explícito.
- [ ] `CqlPredicate` escapa literais string (aspas simples duplicadas) e serializa em CQL válido; há escape-hatch `raw_cql` com aviso de risco.
- [ ] `WfsFeatureCollection` tolera `totalFeatures`/`numberMatched` ausentes ou não-inteiros (ex.: `"unknown"`), coagindo para `None`.
- [ ] Existe `tests/` na **raiz**, espelhando `services/integrations/wfs/`, com testes unitários `pytest` que **mockam a resposta da API** (sem rede).

## Contexto e decisões de arquitetura

**Camadas (§3).** Esta SPEC mexe só no **domínio** (`services/integrations/`). Não toca views,
templates nem models. É a peça fundacional que o CLAUDE.md já antecipa como referência a compor
(`@services/integrations/wfs` → cliente WFS).

**Por que config injetada (§3.3).** O exemplo de origem fazia `from api.config import settings`
dentro da classe. Aqui isso é **proibido**: o domínio não conhece Django. A orquestração (view ou
management command) lê as chaves do `config/` do Django, monta um `WfsConnectionConfig` (Pydantic)
e **injeta** no construtor. Trocar GeoSampa por MDSF é só passar outra config — nenhum código de
domínio muda.

**Por que dois (três) modelos Pydantic.**
- **Entrada (`WfsFeatureRequest`)** — o cliente não recebe dict solto nem `**kwargs` mágicos
  (§3.3: comunicação por DTO). O ponto sensível são os **filtros CQL**: viram query crua contra o
  GeoServer. Por isso CQL é **estruturado** (`CqlFilter`/`CqlPredicate`) com escape de literais,
  reduzindo risco de filtro malformado/injeção; quem precisar de CQL arbitrário usa `raw_cql`
  cientemente.
- **Saída (`WfsFeatureCollection`)** — o WFS devolve um envelope GeoJSON (`FeatureCollection`),
  formato de **protocolo externo**. Modelá-lo isola o resto do sistema do schema bruto: mudança de
  fonte (GeoSampa→MDSF) fica contida no parsing.
- **Config (`WfsConnectionConfig`)** — separa *como conectar* (domínio, endpoint, versão,
  namespace) de *o que pedir* (`WfsFeatureRequest`).

**Padrão callable preservado.** `__call__(request)` retorna o gerador de `fetch_feature_batches`,
mantendo a ergonomia da classe original (`for page in fetcher(request): ...`).

**Fluxo resumido.** `view/command` lê settings → monta `WfsConnectionConfig` + `WfsFeatureRequest`
→ instancia/chama `WfsFetcher` → itera lotes (`WfsFeatureCollection`) → entrega ao matcher/script.

## Peças de referência a compor

> Esta é uma SPEC **fundacional**: ela *cria* a peça que as próximas vão compor. Há pouco a
> reutilizar ainda; o que existe:

- `config/` (Django settings) → chaves de conexão WFS (`WFS_DOMAIN`, `WFS_ENDPOINT`, `WFS_SERVICE`,
  `WFS_VERSION`, `WFS_NAMESPACE`). **Lidas pela orquestração**, nunca pelo domínio — viram
  `WfsConnectionConfig` injetado.
- `requests` (stack §2, HTTP client síncrono) → usar por composição dentro do `WfsFetcher`.
- `services/utils` (quando existir) → eventual normalização de texto para montar valores de
  filtro; reutilizar, não recriar.

## Snippets sugeridos

```python
# direção de implementação — adaptar sem violar §3 (domínio sem Django) nem §10.
# services/integrations/wfs/models.py
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


# ---------- Config de conexão (injetada pela orquestração) ----------
class WfsConnectionConfig(BaseModel):
    domain: str
    endpoint: str
    namespace: str
    service: str = "WFS"
    version: str = "2.0.0"

    @property
    def url_base(self) -> str:
        return f"https://{self.domain}/{self.endpoint}"


# ---------- Filtros CQL (parte sensível: vira query crua) ----------
def _escape_cql_literal(value: str | int | float | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    # string: delimita com aspas simples e duplica aspas internas (ECQL)
    return "'" + value.replace("'", "''") + "'"


class CqlPredicate(BaseModel):
    field: str
    op: Literal["=", "<>", ">", "<", ">=", "<=", "LIKE", "ILIKE"]
    value: str | int | float | bool

    def to_cql(self) -> str:
        # para LIKE/ILIKE o chamador já inclui os curingas % no value
        return f"{self.field} {self.op} {_escape_cql_literal(self.value)}"


class CqlFilter(BaseModel):
    predicates: list[CqlPredicate] = Field(default_factory=list)
    logic: Literal["AND", "OR"] = "AND"
    raw_cql: str | None = None  # escape-hatch: bypassa o escape — usar com cautela

    def to_cql(self) -> str:
        if self.raw_cql is not None:
            return self.raw_cql
        return f" {self.logic} ".join(p.to_cql() for p in self.predicates)


# ---------- Entrada (request) ----------
class WfsFeatureRequest(BaseModel):
    nome_camada: str
    output_format: str = "application/json"
    count: int | None = None          # vira maxFeatures (WFS 1.x) / count (2.0) — ver Notas
    start_index: int | None = None
    cql_filter: CqlFilter | None = None
    srs_name: str | None = None
    property_names: list[str] | None = None
    extra_params: dict[str, str | int] = Field(default_factory=dict)

    def to_query_params(self) -> dict[str, str | int]:
        params: dict[str, str | int] = {"outputFormat": self.output_format}
        if self.count is not None:
            params["maxFeatures"] = self.count
        if self.start_index is not None:
            params["startIndex"] = self.start_index
        if self.cql_filter is not None:
            params["cql_filter"] = self.cql_filter.to_cql()
        if self.srs_name:
            params["srsName"] = self.srs_name
        if self.property_names:
            params["propertyName"] = ",".join(self.property_names)
        params.update(self.extra_params)
        return params


# ---------- Saída (padrão WFS/GeoJSON) ----------
class WfsGeometry(BaseModel):
    type: str
    coordinates: Any  # varia por tipo (Point/LineString/Polygon/Multi*)


class WfsFeature(BaseModel):
    type: Literal["Feature"]
    id: str | None = None
    geometry: WfsGeometry | None = None
    geometry_name: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class WfsFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"]
    features: list[WfsFeature] = Field(default_factory=list)
    total_features: int | None = Field(default=None, alias="totalFeatures")
    number_matched: int | None = Field(default=None, alias="numberMatched")
    number_returned: int | None = Field(default=None, alias="numberReturned")
    crs: dict[str, Any] | None = None
    bbox: list[float] | None = None

    model_config = {"populate_by_name": True}

    @field_validator("total_features", "number_matched", "number_returned", mode="before")
    @classmethod
    def _coerce_unknown(cls, v: Any) -> int | None:
        # GeoServer às vezes manda "unknown" antes de contar
        if isinstance(v, int):
            return v
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
```

```python
# services/integrations/wfs/fetcher.py
from __future__ import annotations
from typing import Generator
from json import JSONDecodeError
import requests

from .models import WfsConnectionConfig, WfsFeatureRequest, WfsFeatureCollection


class WfsFetcher:
    """Cliente WFS callable, paginado e agnóstico de Django (config injetada)."""

    def __init__(self, config: WfsConnectionConfig, *, verbose: bool = False) -> None:
        self.config = config
        self.verbose = verbose
        self.features_fetched_count = 0

    def _base_params(self, request: WfsFeatureRequest) -> dict[str, str | int]:
        return {
            "service": self.config.service,
            "version": self.config.version,
            "request": "GetFeature",
            "typeName": f"{self.config.namespace}:{request.nome_camada}",
            **request.to_query_params(),
        }

    def _get_page(self, request: WfsFeatureRequest, start_index: int) -> WfsFeatureCollection:
        params = self._base_params(request)
        params["startIndex"] = start_index
        if self.verbose:
            print(f"WFS GET {self.config.url_base} :: {params}")
        resp = requests.get(self.config.url_base, params=params)
        if resp.status_code != 200:
            resp.raise_for_status()
        try:
            payload = resp.json()
        except JSONDecodeError:
            raise ValueError(f"Resposta não é JSON válido: {resp.text[:500]}")
        return WfsFeatureCollection.model_validate(payload)

    def fetch_feature_batches(
        self, request: WfsFeatureRequest
    ) -> Generator[WfsFeatureCollection, None, None]:
        start_index = request.start_index or 0
        self.features_fetched_count = 0
        while True:
            page = self._get_page(request, start_index)
            if not page.features:
                break
            n = len(page.features)
            self.features_fetched_count += n
            start_index += n
            yield page
            if page.number_matched is not None and self.features_fetched_count >= page.number_matched:
                break

    def __call__(
        self, request: WfsFeatureRequest
    ) -> Generator[WfsFeatureCollection, None, None]:
        return self.fetch_feature_batches(request)
```

```python
# tests/services/integrations/wfs/test_fetcher.py  (espelha a árvore do domínio)
import pytest
from unittest.mock import patch, Mock

from services.integrations.wfs.models import WfsConnectionConfig, WfsFeatureRequest
from services.integrations.wfs.fetcher import WfsFetcher


@pytest.fixture
def config():
    return WfsConnectionConfig(domain="wfs.geosampa.test", endpoint="geoserver/ows", namespace="geoportal")


def _fake_response(json_payload, status=200, raise_json=False):
    resp = Mock()
    resp.status_code = status
    if raise_json:
        from json import JSONDecodeError
        resp.json.side_effect = JSONDecodeError("x", "x", 0)
        resp.text = "<html>erro</html>"
    else:
        resp.json.return_value = json_payload
    resp.raise_for_status.side_effect = Exception("HTTP error")
    return resp


def _page(features, number_matched):
    return {"type": "FeatureCollection", "numberMatched": number_matched, "features": features}


def _feat(i):
    return {"type": "Feature", "id": f"camada.{i}",
            "geometry": {"type": "Point", "coordinates": [0, 0]}, "properties": {"n": i}}


def test_single_page(config):
    with patch("services.integrations.wfs.fetcher.requests.get") as g:
        g.return_value = _fake_response(_page([_feat(1), _feat(2)], 2))
        pages = list(WfsFetcher(config)(WfsFeatureRequest(nome_camada="lote", count=10)))
    assert len(pages) == 1
    assert len(pages[0].features) == 2


def test_paginates_until_number_matched(config):
    responses = [_fake_response(_page([_feat(1), _feat(2)], 3)),
                 _fake_response(_page([_feat(3)], 3))]
    with patch("services.integrations.wfs.fetcher.requests.get", side_effect=responses):
        pages = list(WfsFetcher(config)(WfsFeatureRequest(nome_camada="lote", count=2)))
    assert sum(len(p.features) for p in pages) == 3


def test_empty_stops(config):
    with patch("services.integrations.wfs.fetcher.requests.get") as g:
        g.return_value = _fake_response(_page([], 0))
        assert list(WfsFetcher(config)(WfsFeatureRequest(nome_camada="lote"))) == []


def test_invalid_json_raises_valueerror(config):
    with patch("services.integrations.wfs.fetcher.requests.get") as g:
        g.return_value = _fake_response(None, raise_json=True)
        with pytest.raises(ValueError):
            list(WfsFetcher(config)(WfsFeatureRequest(nome_camada="lote")))
```

```python
# tests/services/integrations/wfs/test_models.py
from services.integrations.wfs.models import CqlPredicate, CqlFilter, WfsFeatureCollection


def test_cql_escapes_single_quote():
    assert CqlPredicate(field="nm", op="=", value="O'Brien").to_cql() == "nm = 'O''Brien'"


def test_cql_and_join():
    f = CqlFilter(predicates=[CqlPredicate(field="cod", op="=", value=123),
                              CqlPredicate(field="nm", op="LIKE", value="PAULISTA%")])
    assert f.to_cql() == "cod = 123 AND nm LIKE 'PAULISTA%'"


def test_collection_coerces_unknown():
    fc = WfsFeatureCollection.model_validate(
        {"type": "FeatureCollection", "numberMatched": "unknown", "features": []})
    assert fc.number_matched is None
```

## Fora de escopo
- Reprojeção, interseção, filtro por área e export (são lógica espacial do domínio em outras SPECs — §3.2).
- Persistência das features em models / PostGIS (outra SPEC, do épico de ingestão).
- Geração das variações de nome de logradouro/endereço.
- Async / cliente HTTP assíncrono (stack §2 fixa `requests` síncrono nesta fase).
- Leitura das settings do Django (é orquestração; a SPEC só define o DTO de config que ela injeta).

## Notas de teste
- **Sempre mockar `requests.get`** — nenhum teste bate na rede.
- Cobrir: página única; paginação multi-lote por `numberMatched`; resultado vazio; erro HTTP (`raise_for_status`); corpo não-JSON → `ValueError`.
- CQL: escape de aspas simples; junção `AND`/`OR`; `LIKE` com curinga; `raw_cql` (bypass).
- `WfsFeatureCollection`: `numberMatched`/`totalFeatures` ausentes ou `"unknown"` → `None`; parsing de `geometry` Point/LineString/Polygon.
- **Borda de versão WFS:** 1.x usa `maxFeatures`, 2.0.0 usa `count`. Os snippets usam `maxFeatures`; se a `version` da config for 2.0.0, validar qual o GeoServer aceita e, se preciso, mapear no `to_query_params` por versão (registrar em Patches).
- **Borda CQL+BBOX:** alguns GeoServers recusam `cql_filter` e `bbox` juntos; preferir embutir o bbox no CQL.

## Patches
<!-- correções/bugfixes após a SPEC em uso; cada patch incrementa a versão no front-matter -->

### 2026-06-19 (v2) — Resiliência a timeout/conexão no `WfsFetcher`

**Problema.** Rotinas de ingestão que puxam camadas grandes (lotes, endereços) sobrecarregam o
GeoServer upstream, que fica lento e pode estourar timeout ou recusar/derrubar a conexão. Hoje o
`requests.get` em `_get_page` **não passa `timeout=`** (espera indefinidamente) e **não há retry**:
uma página lenta ou uma falha transitória de conexão derruba toda a paginação. Queremos tolerar
lentidão/instabilidade transitória sem travar e sem risco de **loop infinito**.

**Decisão de arquitetura (onde os parâmetros moram).** A política de resiliência tem **quatro
parâmetros**, todos com **nomes semânticos** e **definidos no `settings` do Django**:

| Constante no `settings`         | Significado |
|---------------------------------|-------------|
| `WFS_REQUEST_TIMEOUT_SECONDS`   | timeout (connect+read) passado ao `requests.get` |
| `WFS_MAX_RETRIES`               | nº **máximo de retentativas** após a 1ª falha (limite duro) |
| `WFS_RETRY_WAIT_MIN_SECONDS`    | piso da espera aleatória entre tentativas |
| `WFS_RETRY_WAIT_MAX_SECONDS`    | teto da espera aleatória entre tentativas |

> **Tensão com §3.3 resolvida por injeção.** O `WfsFetcher` é domínio e **não pode ler `settings`**
> (a SPEC já proíbe: "a classe não importa Django"). Portanto o `settings` é lido pela
> **orquestração** (view / management command), que monta um DTO e o **injeta** no fetcher — exatamente
> como já se faz com `WfsConnectionConfig`. "Definido no settings" significa **origem** do valor; o
> domínio recebe o valor **já resolvido** via DTO.

**Novo DTO — `WfsRetryPolicy` (Pydantic, em `models.py`).** Responsabilidade única: descrever a
política de resiliência, separada de *como conectar* (`WfsConnectionConfig`) e *o que pedir*
(`WfsFeatureRequest`). Campos com nomes semânticos espelhando as constantes do settings:

```python
# direção — adaptar sem violar §3/§10
class WfsRetryPolicy(BaseModel):
    request_timeout_seconds: float = 30.0
    max_retries: int = 3                      # limite duro de retentativas
    retry_wait_min_seconds: float = 1.0
    retry_wait_max_seconds: float = 5.0

    @model_validator(mode="after")
    def _check_bounds(self) -> "WfsRetryPolicy":
        if self.max_retries < 0:
            raise ValueError("max_retries não pode ser negativo")
        if self.retry_wait_min_seconds < 0 or self.retry_wait_max_seconds < 0:
            raise ValueError("esperas não podem ser negativas")
        if self.retry_wait_max_seconds < self.retry_wait_min_seconds:
            raise ValueError("retry_wait_max_seconds deve ser >= retry_wait_min_seconds")
        return self
```

Defaults sensatos garantem que **callers atuais continuam funcionando** sem mudança (o policy é
opcional na injeção).

**Novas exceptions (em `exceptions.py`).** Conforme decidido, ambas herdam da exception própria já
existente `WfsHttpError`. São levantadas **apenas quando os retries se esgotam**, encadeando
(`raise ... from exc`) a última falha. Cada uma nomeia semanticamente o tipo de falha — um
`ConnectionError` não deve surgir como "timeout" e vice-versa:

```python
class WfsTimeoutError(WfsHttpError):
    """Levantada quando o GeoServer não respondeu dentro do timeout após esgotar os retries."""


class WfsConnectionError(WfsHttpError):
    """Levantada quando a conexão com o GeoServer falhou após esgotar os retries."""
```

Como `WfsHttpError.__init__` aceita `response=`, e numa falha de rede não há resposta, o `response`
fica `None`. Ambas exportadas no `__init__.py`.

**Composição no `WfsFetcher`.** O policy é **injetado** por composição (não lido de settings):

```python
def __init__(
    self,
    config: WfsConnectionConfig,
    *,
    retry_policy: WfsRetryPolicy | None = None,
    verbose: bool = False,
) -> None:
    self.config = config
    self.retry_policy = retry_policy or WfsRetryPolicy()
    self.verbose = verbose
    self.features_fetched_count = 0
```

**Onde o retry envolve (escopo cirúrgico).** O retry envolve **só a chamada de rede** — o
`requests.get(..., timeout=request_timeout_seconds)`. Dispara retry em **falhas de rede
transitórias**: `requests.exceptions.Timeout` **e** `requests.exceptions.ConnectionError`. **NÃO**
se reexecuta em `raise_for_status` (erro de status é determinístico, não transitório) nem em corpo
não-JSON (`WfsInvalidResponseError`): esses propagam na 1ª ocorrência, como já é hoje.

**Qual exception ao esgotar.** Despacha pela última falha capturada: `Timeout` → `WfsTimeoutError`;
`ConnectionError` → `WfsConnectionError`. Detalhe de hierarquia do `requests`:
`ConnectTimeout` herda de **ambos** `ConnectionError` e `Timeout`; por isso o teste de `Timeout` vem
**primeiro**, tratando um timeout-na-conexão como timeout (mais informativo).

**Loop limitado — sem infinito (regra inegociável).** A repetição é um `for` sobre um range
**finito** de `max_retries + 1` tentativas (1 original + as retentativas). A espera aleatória
(`random.uniform(retry_wait_min_seconds, retry_wait_max_seconds)`) ocorre **entre** tentativas —
nunca antes da 1ª, nunca após a falha final. Esgotado o range, levanta a exception correspondente.
Não há `while True` no caminho de retry.

**Três peças, responsabilidade única (§10.1).** Para o loop não acumular orquestração + decisão de
retry + tradução de exception, o tratamento de erro sai do `_request_with_retries`:
- `_request_with_retries` — só o loop enxuto: tenta `requests.get`/`return`; no `except`, delega.
- `_handle_network_failure` — decide o destino da falha: **primeiro** trata "excedeu `max_retries`"
  (chama a função que levanta); **em seguida** (não excedeu) faz o `sleep` e deixa o loop repetir.
- `_raise_network_error` — tradução semântica (`NoReturn`): `Timeout` → `WfsTimeoutError`,
  `ConnectionError` → `WfsConnectionError`. Tipá-la `NoReturn` deixa o mypy entender o fluxo.

```python
# direção — método novo, isolando a chamada de rede com resiliência
def _request_with_retries(self, params: dict[str, str | int]) -> requests.Response:
    policy = self.retry_policy
    for attempt_number in range(policy.max_retries + 1):   # range FINITO → sem loop infinito
        try:
            return requests.get(
                self.config.url_base,
                params=params,
                timeout=policy.request_timeout_seconds,
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            self._handle_network_failure(exc, attempt_number)
    # inalcançável: a última tentativa sempre retorna ou levanta (via _raise_network_error).
    raise AssertionError("loop de retry terminou sem retornar nem levantar")


def _handle_network_failure(
    self, exc: requests.exceptions.RequestException, attempt_number: int
) -> None:
    """Destino de uma falha de rede: esgotou os retries → levanta; senão → espera e repete."""
    policy = self.retry_policy
    if self.verbose:
        print(
            f"WFS falha de rede (tentativa {attempt_number + 1}/{policy.max_retries + 1}): {exc!r}"
        )
    if attempt_number >= policy.max_retries:           # excedeu o limite → levanta
        self._raise_network_error(exc)
    time.sleep(random.uniform(                          # ainda há retry → espera entre tentativas
        policy.retry_wait_min_seconds,
        policy.retry_wait_max_seconds,
    ))


def _raise_network_error(self, exc: requests.exceptions.RequestException) -> NoReturn:
    """Traduz a falha de rede na exception própria correspondente. Timeout primeiro:
    ConnectTimeout herda de ambos e é, na prática, um timeout."""
    total_attempts = self.retry_policy.max_retries + 1
    if isinstance(exc, requests.exceptions.Timeout):
        raise WfsTimeoutError(
            f"WFS não respondeu (timeout={self.retry_policy.request_timeout_seconds}s) "
            f"após {total_attempts} tentativas"
        ) from exc
    raise WfsConnectionError(
        f"Falha de conexão com o WFS após {total_attempts} tentativas"
    ) from exc
```

`_get_page` passa a chamar `_request_with_retries(params)` no lugar do `requests.get` direto;
o resto de `_get_page` (status, JSON, `model_validate`) e toda a paginação em
`fetch_feature_batches` **ficam intactos** — a resiliência é transparente para o gerador.

**Exports (`__init__.py`).** Acrescentar `WfsTimeoutError`, `WfsConnectionError` e `WfsRetryPolicy`
ao import e ao `__all__`, mantendo a regra de §7.2 (contratos expostos no nível superior).

**Orquestração (fora desta SPEC, mas anotado).** A view / management command lê
`WFS_REQUEST_TIMEOUT_SECONDS`, `WFS_MAX_RETRIES`, `WFS_RETRY_WAIT_MIN_SECONDS`,
`WFS_RETRY_WAIT_MAX_SECONDS` do `settings`, monta `WfsRetryPolicy(...)` e injeta no `WfsFetcher`.

**Notas de teste do patch (mockar tudo — sem rede, sem dormir de verdade).**
- Mockar `time.sleep` e `random.uniform` (assertar que dorme dentro de
  `[retry_wait_min_seconds, retry_wait_max_seconds]` e que **não** dorme após a falha final).
- **Sucesso após falhas transitórias:** `requests.get` com `side_effect=[Timeout, ConnectionError, resposta_ok]`
  e `max_retries=3` → retorna a página; `requests.get` chamado **3 vezes**.
- **Esgota retries (timeout) → `WfsTimeoutError`:** `side_effect=Timeout` sempre, `max_retries=2` →
  levanta `WfsTimeoutError`; `requests.get` chamado **exatamente 3 vezes** (1 + 2) — prova do
  **limite duro**.
- **Esgota retries (conexão) → `WfsConnectionError`:** `side_effect=ConnectionError` sempre →
  levanta `WfsConnectionError`.
- **`ConnectTimeout` → `WfsTimeoutError`:** confirma o despacho "Timeout primeiro".
- **`max_retries=0`:** uma única tentativa; falha → exception correspondente sem nenhum `sleep`.
- **Encadeamento:** `__cause__` da exception levantada é a última falha capturada.
- **Não-retry:** `raise_for_status`/corpo não-JSON continuam levantando `WfsHttpError`/
  `WfsInvalidResponseError` **na 1ª tentativa**, sem retry.
- **DTO:** `WfsRetryPolicy` rejeita `max_retries` negativo e `retry_wait_max_seconds <
  retry_wait_min_seconds`.

### 2026-06-19 (v3) — Fiação da `WfsRetryPolicy` nos commands de ingestão

**Problema.** O patch v2 criou a `WfsRetryPolicy` e fez o `WfsFetcher` aceitá-la por injeção, mas
**ninguém a injeta ainda**: os três management commands de ingestão constroem só o
`WfsConnectionConfig` e chamam `run(config, request, verbose=...)`. Sem o policy, todo fetch usa os
**defaults** do `WfsFetcher` — os parâmetros não são configuráveis por ambiente. Este patch
**operacionaliza** a nota "Orquestração (fora desta SPEC, mas anotado)" do v2: ler os quatro
parâmetros do `settings` e injetá-los até o fetcher.

**Commands afetados (orquestração — leem `settings`, montam DTO, §3.3).**
- `apps/address_geocoder/management/commands/extrair_enderecos_fiscais.py`
- `apps/address_geocoder/management/commands/extrair_segmentos_logradouros.py`
- `apps/logradouro_matcher/management/commands/extrair_nomes_logradouros.py`

**Onde cada parâmetro entra (caminho completo).**
```
config/settings.py (env → constante UPPER_CASE)
   → command monta WfsRetryPolicy(...)            [orquestração]
       → run(config, request, retry_policy=...)    [script, repassa]
           → WfsFetcher(config, retry_policy=...)   [domínio, já pronto desde v2]
```

**1) `config/settings.py` — quatro constantes novas.** Seguindo o padrão §10.3/§11 já presente no
arquivo (campo no `_Settings` com `alias` + reextração para constante `UPPER_CASE`). Defaults
**idênticos** aos da `WfsRetryPolicy`, para que "não configurar nada" preserve o comportamento atual:

```python
# dentro de _Settings(BaseSettings):
    wfs_request_timeout_seconds: float = Field(default=30.0, alias="WFS_REQUEST_TIMEOUT_SECONDS")
    wfs_max_retries: int = Field(default=3, alias="WFS_MAX_RETRIES")
    wfs_retry_wait_min_seconds: float = Field(default=1.0, alias="WFS_RETRY_WAIT_MIN_SECONDS")
    wfs_retry_wait_max_seconds: float = Field(default=5.0, alias="WFS_RETRY_WAIT_MAX_SECONDS")

# reextração (após _env = _Settings(), junto das demais WFS_*):
WFS_REQUEST_TIMEOUT_SECONDS = _env.wfs_request_timeout_seconds
WFS_MAX_RETRIES = _env.wfs_max_retries
WFS_RETRY_WAIT_MIN_SECONDS = _env.wfs_retry_wait_min_seconds
WFS_RETRY_WAIT_MAX_SECONDS = _env.wfs_retry_wait_max_seconds
```
> A validação de limites (min ≤ max, não-negativos) **continua na `WfsRetryPolicy`** — o `settings`
> só carrega os valores; o DTO valida ao ser instanciado no command. Não duplicar regra.
> Anotar os quatro novos nomes no `.env.example` (o `settings` referencia esse arquivo).

**2) As três funções `run(...)` em `services/scripts/*` — repassam o policy.** Hoje cada `run` faz
`fetcher = WfsFetcher(config, verbose=verbose)`. Acrescentar um parâmetro **opcional** que é apenas
encaminhado — o script **não lê settings nem constrói o policy** (isso é orquestração); ele só passa
adiante. `None` mantém o default (o `WfsFetcher` já faz `retry_policy or WfsRetryPolicy()`), então a
mudança é **retrocompatível**:

```python
from services.integrations.wfs import WfsConnectionConfig, WfsFetcher, WfsRetryPolicy

def run(
    config: WfsConnectionConfig,
    request: <RequestDoScript>,
    retry_policy: WfsRetryPolicy | None = None,
    verbose: bool = False,
) -> <ResultDoScript>:
    fetcher = WfsFetcher(config, retry_policy=retry_policy, verbose=verbose)
    ...  # resto inalterado
```
Aplicar idêntico aos três: `logradouros`, `enderecos_fiscais`, `segmentos_logradouros`.

**3) Cada command — monta o policy a partir do `settings` e injeta.** Espelha o que já se faz com
`WfsConnectionConfig` (mesmo arquivo, logo acima). Direção (exemplo do `extrair_nomes_logradouros`):

```python
from services.integrations.wfs import WfsConnectionConfig, WfsRetryPolicy

    def handle(self, *args: object, **options: object) -> None:
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
        request = NomesLogradourosRequest(...)
        result = run(config, request, retry_policy=retry_policy, verbose=bool(options["verbose"]))
        ...
```
Os outros dois commands recebem o mesmo bloco `retry_policy = WfsRetryPolicy(...)` e passam
`retry_policy=retry_policy` no `run(...)`, mantendo intactos os respectivos `request`/mensagens.

**Decisão: duplicar o bloco vs. extrair helper.** Mantém-se a **duplicação** do `WfsRetryPolicy(...)`
nos três commands, espelhando a duplicação já existente do `WfsConnectionConfig(...)` — é
orquestração fina e local, e um helper compartilhado entre apps distintos (`address_geocoder` e
`logradouro_matcher`) criaria acoplamento sem ganho real nesta fase. Se um dia virar quatro+ commands,
reavaliar um pequeno builder em `config/` (registrar em novo patch).

**Fora de escopo deste patch.**
- Flags de CLI para sobrescrever os parâmetros por execução (`--max-retries` etc.): o controle é por
  ambiente/`settings`; abrir patch próprio se necessário.
- Qualquer mudança no `WfsFetcher`/`WfsRetryPolicy` — já prontos no v2.

**Notas de teste do patch.**
- **`run` repassa o policy:** com `requests.get` mockado, chamar `run(config, request,
  retry_policy=WfsRetryPolicy(max_retries=0))` e, via `patch` em `WfsFetcher`, assertar que recebeu
  o `retry_policy` (ou, integrado: `Timeout` no `requests.get` + `max_retries=0` → `WfsTimeoutError`
  numa única tentativa).
- **`run` sem policy:** `retry_policy=None` continua funcionando (usa default) — protege a
  retrocompatibilidade.
- **Command → policy:** teste de management command (`call_command`) com `settings` sobrescritos
  (`override_settings`) montando o `WfsRetryPolicy` esperado; mockar o `run` e assertar que foi
  chamado com o `retry_policy` correspondente aos `settings`. Sem rede.
- **Defaults do settings:** sem env, `WFS_MAX_RETRIES == 3` etc. (batem com os defaults do DTO).