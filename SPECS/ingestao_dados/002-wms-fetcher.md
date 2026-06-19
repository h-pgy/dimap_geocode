---
spec: ingestao-dados/002
versao: v1
atualizado_em: 2026-06-18
changelog:
  - v1: versão inicial
---

# SPEC ingestao-dados/002 — Integration WMS Fetcher (imagem PNG por bbox)

## User story
Como desenvolvedor do domínio, quero um cliente WMS reutilizável e tipado que, dado um
bounding box e uma camada, devolva a imagem PNG correspondente daquela área, para que o
sistema gere **previews/thumbnails/exports** server-side de um resultado geocodificado
(ponto, linha ou lote) sobre o pano de fundo cartográfico do GeoSampa/MDSF, sem cada
consumidor reimplementar a montagem do `GetMap`.

> **Escopo de uso.** Esta integration é **extração server-side de imagem** (bytes PNG). É
> distinta do mapa interativo, onde o **Leaflet consome o WMS direto no cliente** (CLAUDE.md
> §1). Aqui o backend pede a imagem para uma área já resolvida.

## Critérios de aceite
- [ ] Existe `services/integrations/wms/` com a classe `WmsFetcher`, **callable** (`__call__` delega ao método de fetch).
- [ ] A classe **não importa Django** (nem `settings`): a configuração de conexão chega **por DTO Pydantic injetado** (`WmsConnectionConfig`).
- [ ] A integration é **fina**: recebe um **bbox já resolvido** + camada e devolve a imagem. **Não depende de `geopandas`** nem faz reprojeção/geração de bbox internamente (§3.2).
- [ ] O DTO de bounding box (`BoundingBox`) é **autocontido neste submódulo** (`services/integrations/wms/models.py`): CRS-aware e expõe `string_wms`. **Sem dependência de módulo externo.**
- [ ] Entrada modelada em Pydantic: `WmsMapRequest`, carregando o `bbox` (`BoundingBox`), camada, dimensões e flag `raster`.
- [ ] Saída modelada em Pydantic: `WmsImage` (bytes + content-type + dimensões + bbox + camada de proveniência).
- [ ] Seleção de servidor vetorial vs **raster** resolvida pela config a partir da flag do request.
- [ ] Exceções **específicas do módulo** em `services/integrations/wms/exceptions.py`: base `WmsError`; `WmsHttpError` (disparada quando `raise_for_status` falharia — **herda de `requests.HTTPError`**); `WmsResponseNotImageError` (HTTP 200 mas corpo não-imagem / `ServiceException`).
- [ ] `services/integrations/wms/__init__.py` expõe **apenas**: os models Pydantic de entrada/saída, as exceptions e a classe callable `WmsFetcher` — nada de helpers internos.
- [ ] Existe `tests/` na **raiz**, espelhando `services/integrations/wms/`, com testes unitários `pytest` que **mockam a resposta da API** (sem rede).

## Contexto e decisões de arquitetura

**Camadas (§3).** SPEC só de **domínio** (`services/integrations/`). Não toca views, templates
nem models.

**Decisões de arquitetura:**

1. **Config injetada, não `settings` (§3.3).** A orquestração (view/command) lê as chaves WMS do
   `config/`, monta `WmsConnectionConfig` e injeta no `WmsFetcher`. O domínio não conhece Django;
   trocar GeoSampa→MDSF é trocar a config, sem tocar no domínio.
2. **Integration fina, sem `geopandas` nem reprojeção (§3.2 + §2).** A integration recebe um
   `BoundingBox` **já resolvido** e só monta/dispara o `GetMap`. Geração de bbox a partir de
   geometria, reprojeção e padding são **lógica espacial** e não pertencem à integration; além
   disso `geopandas` **não está na stack** (a stack espacial é GEOS/GDAL/PROJ via GeoDjango). Essa
   resolução `geometria → bbox` é responsabilidade de quem chama, upstream.
   - **DTO autocontido (§3.3, contratos por submódulo).** O `BoundingBox` (valor + CRS + `string_wms`)
     é definido em `services/integrations/wms/models.py`, junto dos demais DTOs desta integration.
     Nenhum model de bbox é importado de outro módulo: cada submódulo é dono dos seus próprios
     contratos. Se um futuro gerador de bbox em `services/utils` produzir outro formato, é a
     **orquestração** que constrói o `BoundingBox` do WMS a partir dele — a dependência nunca aponta
     de `utils` para esta integration nem o contrário.
3. **Exceções específicas do módulo (`exceptions.py`).** Em vez de exceções genéricas, o módulo
   define `WmsError` (base — captura qualquer falha da integration), `WmsHttpError` (status de erro;
   quando `raise_for_status` falharia — **herda de `requests.HTTPError`**, capturável pelas duas) e
   `WmsResponseNotImageError` (HTTP 200 com `Content-Type` não-imagem). Isso importa porque o WMS
   frequentemente devolve um `ServiceException` em XML **com status 200**: só checar o status não
   basta, é preciso validar o `Content-Type`.
4. **Um único dict de parâmetros.** Todos os parâmetros do `GetMap` (incluindo `request`, `service`,
   `version`) são montados num único dict e passados ao `requests.get` via `params=`, evitando
   query string embutida na URL base.

**Parte sensível = bbox + CRS + ordem de eixos.** O bbox
**carrega seu CRS** (via `BoundingBox`) e o parâmetro WMS de projeção tem de concordar com ele.
Atenção ao *gotcha* de versão: WMS **1.3.0** usa `crs` e **respeita a ordem de eixos do CRS** (p.ex.
EPSG:4326 é lat/lon!); WMS **1.1.1** usa `srs` e é sempre lon/lat. Ver Notas de teste.

**Padrão callable preservado.** `__call__(request)` retorna `fetch_map(request)`.

**Fluxo resumido.** orquestração lê settings → `WmsConnectionConfig`; resolve a área de interesse
em um `BoundingBox` (a geração `geometria → bbox` é upstream) → monta `WmsMapRequest` → chama
`WmsFetcher` → recebe `WmsImage` (bytes) para preview/thumbnail/export.

## Peças de referência a compor
- `requests` (stack §2) → usar por composição dentro do `WmsFetcher`.
- `config/` (Django settings) → `WMS_URL`, `WMS_RASTER_URL`, `WMS_VERSION` (+ CRS/format padrão).
  **Lidas pela orquestração**, viram `WmsConnectionConfig` injetado — nunca lidas pelo domínio.

> O DTO `BoundingBox` é **criado nesta SPEC**, autocontido no submódulo — não é dependência externa.
> A **geração** de um bbox a partir de geometria (reprojeção + padding) é feita upstream pela
> orquestração e está **fora de escopo** aqui; eventual util compartilhado em `services/utils` é
> assunto de outra SPEC e não inverte a dependência desta integration.

## Snippets sugeridos

```python
# direção de implementação — adaptar sem violar §3 (domínio sem Django) nem §10.
# services/integrations/wms/models.py
from pydantic import BaseModel


class BoundingBox(BaseModel):
    """Bounding box CRS-aware. DTO autocontido desta integration (não importado de fora)."""
    minx: float
    miny: float
    maxx: float
    maxy: float
    crs: str = "EPSG:31983"   # SIRGAS 2000 / UTM 23S (São Paulo)

    @property
    def string_wms(self) -> str:
        # ordem minx,miny,maxx,maxy (lon/lat). Ver Notas: WMS 1.3.0 + EPSG:4326 inverte p/ lat/lon.
        return f"{self.minx},{self.miny},{self.maxx},{self.maxy}"


class WmsConnectionConfig(BaseModel):
    vector_url: str
    raster_url: str
    version: str = "1.3.0"
    default_crs: str = "EPSG:31983"
    image_format: str = "image/png"
    default_width: int = 256
    default_height: int = 256

    def base_url_for(self, *, raster: bool) -> str:
        return self.raster_url if raster else self.vector_url


class WmsMapRequest(BaseModel):
    layer: str
    bbox: BoundingBox                 # DTO local; .string_wms vai pro WMS
    width: int | None = None          # None → default da config
    height: int | None = None
    raster: bool = False              # escolhe servidor raster vs vetorial (só troca de URL)
    crs: str | None = None            # None → default_crs da config
    image_format: str | None = None
    transparent: bool = True
    styles: str = ""


class WmsImage(BaseModel):
    content: bytes
    content_type: str
    width: int
    height: int
    layer: str
    bbox: BoundingBox
```

```python
# services/integrations/wms/exceptions.py
import requests


class WmsError(Exception):
    """Base de todos os erros desta integration WMS — capture isto para pegar qualquer falha."""


class WmsHttpError(WmsError, requests.HTTPError):
    """Servidor WMS respondeu com status de erro (>= 400).

    Herda de requests.HTTPError, então pode ser capturada como WmsHttpError, como
    WmsError ou como requests.HTTPError.
    """


class WmsResponseNotImageError(WmsError):
    """HTTP 200, mas o corpo não é imagem (provável ServiceException XML do WMS)."""

    def __init__(self, message: str, *, content_type: str | None = None, body: str | None = None):
        super().__init__(message)
        self.content_type = content_type
        self.body = body
```

```python
# services/integrations/wms/__init__.py
# Expõe apenas a API pública: models de entrada/saída, exceptions e a classe callable.
from .models import BoundingBox, WmsConnectionConfig, WmsMapRequest, WmsImage
from .exceptions import WmsError, WmsHttpError, WmsResponseNotImageError
from .fetcher import WmsFetcher

__all__ = [
    # models (entrada/saída)
    "BoundingBox", "WmsConnectionConfig", "WmsMapRequest", "WmsImage",
    # exceptions
    "WmsError", "WmsHttpError", "WmsResponseNotImageError",
    # callable
    "WmsFetcher",
]
```

```python
# services/integrations/wms/fetcher.py
import requests

from .models import WmsConnectionConfig, WmsMapRequest, WmsImage
from .exceptions import WmsHttpError, WmsResponseNotImageError


class WmsFetcher:
    """Cliente WMS callable e fino: bbox + camada -> imagem (bytes). Sem Django, sem geopandas."""

    IMAGE_PREFIX = "image/"

    def __init__(self, config: WmsConnectionConfig, *, verbose: bool = False) -> None:
        self.config = config
        self.verbose = verbose

    def _build_params(self, request: WmsMapRequest) -> dict[str, str | int]:
        width = request.width or self.config.default_width
        height = request.height or self.config.default_height
        # WMS 1.3.0 usa "crs"; para 1.1.1 trocar a chave por "srs" (ver Notas).
        return {
            "service": "WMS",
            "version": self.config.version,
            "request": "GetMap",
            "layers": request.layer,
            "styles": request.styles,
            "crs": request.crs or self.config.default_crs,
            "bbox": request.bbox.string_wms,
            "width": width,
            "height": height,
            "format": request.image_format or self.config.image_format,
            "transparent": str(request.transparent).lower(),
        }

    def fetch_map(self, request: WmsMapRequest) -> WmsImage:
        base_url = self.config.base_url_for(raster=request.raster)
        params = self._build_params(request)
        resp = requests.get(base_url, params=params)
        if self.verbose:
            print(f"[WmsFetcher] {resp.url}")
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            # WmsHttpError herda de requests.HTTPError; preserva a response p/ inspeção
            raise WmsHttpError(str(exc), response=resp) from exc
        content_type = resp.headers.get("Content-Type", "")
        if not content_type.startswith(self.IMAGE_PREFIX):
            # WMS devolve ServiceException (XML) mesmo com HTTP 200
            raise WmsResponseNotImageError(
                "Resposta WMS não é imagem (provável ServiceException)",
                content_type=content_type, body=resp.text[:1000],
            )
        return WmsImage(
            content=resp.content, content_type=content_type,
            width=int(params["width"]), height=int(params["height"]),
            layer=request.layer, bbox=request.bbox,
        )

    def __call__(self, request: WmsMapRequest) -> WmsImage:
        return self.fetch_map(request)
```

```python
# composição upstream (orquestração / serviço de alto nível) — NÃO dentro da integration:
# minx, miny, maxx, maxy = resolve_area(geometria, padding_metros=10)  # lógica espacial, em outro lugar
# bbox = BoundingBox(minx=minx, miny=miny, maxx=maxx, maxy=maxy, crs="EPSG:31983")
# image = wms_fetcher(WmsMapRequest(layer="...", bbox=bbox, raster=False))
```

```python
# tests/services/integrations/wms/test_fetcher.py  (espelha a árvore do domínio)
import pytest
import requests
from unittest.mock import patch, Mock

from services.integrations.wms.models import (
    WmsConnectionConfig, WmsMapRequest, BoundingBox,
)
from services.integrations.wms.exceptions import WmsHttpError, WmsResponseNotImageError
from services.integrations.wms.fetcher import WmsFetcher


BBOX = BoundingBox(minx=333000, miny=7390000, maxx=334000, maxy=7391000, crs="EPSG:31983")


@pytest.fixture
def config():
    return WmsConnectionConfig(vector_url="https://wms.test/ows",
                               raster_url="https://wms.test/raster")


def _resp(*, status=200, content_type="image/png", content=b"\x89PNG...", text=""):
    r = Mock()
    r.status_code = status
    r.headers = {"Content-Type": content_type}
    r.content = content
    r.text = text
    r.url = "https://wms.test/ows?..."
    # replica o comportamento real de requests.Response.raise_for_status()
    if status >= 400:
        r.raise_for_status.side_effect = requests.HTTPError(f"{status} Server Error", response=r)
    else:
        r.raise_for_status.return_value = None
    return r


def _req(**kw):
    return WmsMapRequest(layer="cam:lote", bbox=BBOX, **kw)


def test_returns_image_bytes(config):
    with patch("services.integrations.wms.fetcher.requests.get", return_value=_resp()) as g:
        img = WmsFetcher(config)(_req())
    assert img.content.startswith(b"\x89PNG")
    assert img.content_type == "image/png"
    params = g.call_args.kwargs["params"]
    assert params["request"] == "GetMap"
    assert params["bbox"] == BBOX.string_wms


def test_http_error_raises_wms_http_error(config):
    with patch("services.integrations.wms.fetcher.requests.get",
               return_value=_resp(status=500, content_type="text/plain", text="boom")):
        with pytest.raises(WmsHttpError) as exc:
            WmsFetcher(config)(_req())
    # também capturável como requests.HTTPError
    assert isinstance(exc.value, requests.HTTPError)


def test_service_exception_on_200_raises(config):
    # WMS devolve XML de exceção com HTTP 200
    with patch("services.integrations.wms.fetcher.requests.get",
               return_value=_resp(content_type="application/vnd.ogc.se_xml",
                                   text="<ServiceExceptionReport/>")):
        with pytest.raises(WmsResponseNotImageError):
            WmsFetcher(config)(_req())


def test_raster_flag_picks_raster_url(config):
    with patch("services.integrations.wms.fetcher.requests.get", return_value=_resp()) as g:
        WmsFetcher(config)(_req(raster=True))
    assert g.call_args.args[0] == config.raster_url


def test_dimensions_default_from_config(config):
    with patch("services.integrations.wms.fetcher.requests.get", return_value=_resp()) as g:
        WmsFetcher(config)(_req())
    params = g.call_args.kwargs["params"]
    assert params["width"] == config.default_width
    assert params["height"] == config.default_height
```

```python
# tests/services/integrations/wms/test_models.py
from services.integrations.wms.models import BoundingBox, WmsConnectionConfig


def test_bbox_string_wms():
    bb = BoundingBox(minx=1, miny=2, maxx=3, maxy=4)
    assert bb.string_wms == "1.0,2.0,3.0,4.0"
    assert bb.crs == "EPSG:31983"


def test_config_picks_url():
    cfg = WmsConnectionConfig(vector_url="https://v", raster_url="https://r")
    assert cfg.base_url_for(raster=False) == "https://v"
    assert cfg.base_url_for(raster=True) == "https://r"
```

## Fora de escopo
- Geração de bbox a partir de geometria, reprojeção e padding — é lógica espacial feita upstream (eventual util em `services/utils`, outra SPEC). Aqui o `BoundingBox` chega pronto (§3.2).
- Persistência/armazenamento das imagens geradas (preview/thumbnail) — outra SPEC.
- O mapa interativo Leaflet que consome WMS no **cliente** (CLAUDE.md §1) — esta SPEC é server-side.
- `GetFeatureInfo`, `GetCapabilities` e outras operações WMS (só `GetMap` aqui).
- Cache de tiles/imagens.
- Async / cliente HTTP assíncrono (stack §2 fixa `requests` síncrono nesta fase).

## Notas de teste
- **Sempre mockar `requests.get`** — nenhum teste bate na rede.
- Cobrir: imagem OK (`image/png` → `WmsImage` com bytes); erro HTTP → `WmsHttpError` (e conferir que
  é capturável como `requests.HTTPError`); **`ServiceException` com HTTP 200** (content-type
  não-imagem) → `WmsResponseNotImageError`; flag `raster` escolhe `raster_url`; dimensões default
  vindas da config; montagem dos params (`request=GetMap`, `bbox` = `string_wms`, `format`, `crs`).
- **Borda de versão WMS:** 1.3.0 usa `crs` e **respeita ordem de eixos do CRS** (EPSG:4326 = lat/lon!);
  1.1.1 usa `srs` e é lon/lat. Garantir que `BoundingBox.string_wms` produz a ordem coerente com
  a `version`/`crs`. Se a fonte exigir 1.1.1, mapear a chave `crs`→`srs` no `_build_params` (registrar
  em Patches).
- **`BoundingBox` (DTO local):** testar `string_wms` (formato `minx,miny,maxx,maxy`) e os defaults de
  CRS — ver `test_models.py`.

## Patches