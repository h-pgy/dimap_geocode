---
spec: ingestao-dados/001
versao: v1
atualizado_em: 2026-06-18
changelog:
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