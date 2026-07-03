---
spec: geocodificacao/003
versao: v6
atualizado_em: 2026-07-02
implementado: true
changelog:
  - v1: versão inicial
  - v2: PointGeometry documenta a forma de `coordinates` via alias `Position` (list[float]); campo segue `list[Any]` com validação rasa por `eh_ponto` (espelha Line/PolygonGeometry, que passam a citar os aliases de `coordinates.py`)
  - v3: pipeline do AddressGeocoder só orquestra (§10.4) — paridade vira `_definir_paridade`; `_buscar_com_numeracao` é quebrado em `_buscar_segmentos` + `_filtrar_com_numeracao`; a proporção da interpolação sai para `_definir_proporcao`
  - v4: `Paridade` + `intervalo_numeracao` saem de `models.py` (que fica só com DTOs) para um módulo local `numeracao.py`, espelhando o padrão de `address_match/numero.py` e `geometry/coordinates.py`
  - v5: interpolação sai do geocoder para `interpolacao.py` — classe callable `InterpoladorSegmento` (com `_definir_proporcao` como método privado), composta pelo AddressGeocoder como par do `SolverOrientacaoSegmento`
  - v6: patch pós-implementação (ver Patch 001) — corrige heurística de orientação, trata via de segmento único, lê o CRS da própria feature e tipa a dependência injetada como Callable
---

# SPEC geocodificacao/003 — Geocodificação de endereço (codlog + número → ponto)

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como desenvolvedor do domínio, quero um serviço que receba um `codlog` + um `número` de imóvel e
devolva o **ponto** geocodificado desse endereço — obtido por **interpolação** da numeração sobre o
segmento viário (face de quadra) correto do logradouro —, para que a UI possa renderizar o ponto do
endereço no Leaflet e, futuramente, salvá-lo num projeto.

## Critérios de aceite
- [ ] O serviço reside em `services/domain/address_geocod/` (terceiro irmão de `logradouro_geocod` e
      `lote_geocod`, já anunciado na SPEC 001), **não importa recursos de interface do Django**
      (views/request) e **compõe o `LogradouroGeocoder`** por injeção no construtor — **não** refaz a
      busca WFS por conta própria nem acopla ao `WfsFetcher` diretamente.
- [ ] A entrada é um DTO Pydantic com `codlog`, `numero` (imóvel, `int > 0`), o nome da camada de
      logradouros (`layer_name`), o **CRS de interpolação** (`interpolation_crs`, projetado, em metros)
      e o **CRS de saída** (`output_crs`, tipicamente 4326). `layer_name`, `interpolation_crs` e
      `output_crs` são resolvidos pela **orquestração** a partir do `settings` e injetados no DTO — o
      domínio **nunca** lê `settings`.
- [ ] Os segmentos do logradouro vêm da composição do `LogradouroGeocoder`, pedido **no CRS de
      interpolação** (projetado, ex.: EPSG:31983 SIRGAS 2000 / UTM 23S — nativo do GeoSampa e em
      metros), para que a interpolação normalizada seja **métrica** e não sofra a distorção lon/lat de
      graus. Isso é feito montando o `LogradouroGeocodInput` com `output_crs = interpolation_crs`.
- [ ] A **paridade** do número (par/ímpar) seleciona o par de colunas de numeração do segmento
      (`numero_inicial_par`/`numero_final_par` **ou** `numero_inicial_impar`/`numero_final_impar`,
      já disponíveis e tipados `int | None` em `SegmentoLogradouroAttributes`).
- [ ] Segmentos **sem numeração para a paridade buscada** (ambos `inicial` e `final` nulos naquele
      lado) são descartados antes da seleção.
- [ ] É escolhido o segmento cujo intervalo **contém** o número (`inicial <= numero <= final`). Se
      **nenhum** segmento do `codlog` for retornado, o domínio levanta `SegmentoNaoEncontradoError`; se
      houver segmentos mas **nenhum** contiver o número, levanta `NumeracaoNaoEncontradaError`. As duas
      exceções são **tipadas e do domínio** (neutras quanto a Django), para a orquestração distinguir as
      mensagens de aviso. Havendo **mais de um** segmento contendo o número, usa-se o **primeiro**.
- [ ] A **orientação do segmento é corrigida** antes de interpolar: quando a ordem das coordenadas da
      linha contraria o sentido **crescente** da numeração, a linha é invertida. A decisão usa o
      **segmento adjacente** (o anterior, ou o posterior se o escolhido for o primeiro da via) e compara
      distâncias entre extremidades — a mesma heurística do geocoder de referência, agora sobre objetos
      **GEOS**. A correção é uma **peça separada** (SRP, §10.1), composta pelo geocoder.
- [ ] A interpolação usa **objetos geométricos do GeoDjango** (`django.contrib.gis.geos`): a linha vira
      um `LineString` GEOS e o ponto é `linha.interpolate_normalized(proporcao)`, onde
      `proporcao = (numero - inicial) / (final - inicial)`. Quando `inicial == final` (não há intervalo),
      usa-se o **ponto médio** (`proporcao = 0.5`). **Nada de `shapely`/`geopandas` nem parsing manual de
      WKT/coordenadas fora do caminho GEOS/GDAL** (§11).
- [ ] O ponto interpolado (no CRS de interpolação) é **reprojetado** para o `output_crs` via GeoDjango
      (`Point.transform(output_crs)`) — reprojeção **centralizada no domínio**, nunca manual (§7.3).
- [ ] A saída é **uma** `GeoFeature` no envelope de três camadas: `geometry` (a nova `PointGeometry`
      centralizada), `attributes` (DTO `EnderecoAttributes` com a proveniência: `codlog`,
      `nome_logradouro`, `cd_tipo_logradouro`, `titulo`, `id_segmento` de origem e o `numero` buscado) e
      `crs` (= `output_crs`).
- [ ] `PointGeometry` é adicionada ao pacote `services/domain/geometry/` **compondo a primitiva
      `eh_ponto` já existente** (entregue pela SPEC 001), e exposta no `__init__.py` do pacote. Espelha
      `LineGeometry`/`PolygonGeometry` (validação estrutural rasa; sem converter em objeto geométrico).
- [ ] Tipagem estrita compatível com `mypy`; sem `from __future__`.

## Contexto e decisões de arquitetura
Mexe **apenas no domínio** (`services/`). É o item 2 do roadmap da Fase 1 (§14 do CLAUDE.md):
geocodificação de endereços por interpolação do número sobre o logradouro → **ponto**. É o terceiro
módulo de geocodificação, irmão de `logradouro_geocod` (codlog → linha) e `lote_geocod` (contribuinte
→ polígono), e **compõe** o primeiro.

**Composição, não reimplementação.** O geocoder de referência (`geocoder_example/`) fazia a própria
busca WFS por `codlog` (`get_segmentos`). Aqui isso é substituído pela composição do
`LogradouroGeocoder`, que **já** resolve `codlog → segmentos` com geometria e com os campos de
numeração (`numero_inicial/final_par/impar`) traduzidos e tipados `int | None`. O `AddressGeocoder`
recebe um `LogradouroGeocoder` pronto no construtor (§3.3, §10.4) e concentra apenas a lógica que é
sua: paridade, seleção do segmento, correção de orientação e interpolação. A orquestração monta o
`LogradouroGeocoder(build_fetcher(settings))` e injeta.

**CRS: interpola em projetado, entrega reprojetado (§7.3).** O exemplo original ignorava CRS. Aqui a
interpolação normalizada é feita no **CRS de interpolação projetado** (EPSG:31983, nativo do GeoSampa,
em metros) — pedindo os segmentos já nesse CRS ao `LogradouroGeocoder` — para que a proporção do número
seja **métrica**. O ponto resultante é **reprojetado** ao `output_crs` (4326, pronto para o Leaflet)
pelo próprio GeoDjango (`Point.transform`). Toda reprojeção passa por esse ponto único do domínio; nada
manual. Ambos os CRS são constantes de `settings` resolvidas pela orquestração e injetadas via DTO — o
domínio não fixa CRS como constante de módulo (mesmo princípio da SPEC 001, v10).

**Geometria vira GEOS só onde é necessário.** `logradouro_geocod`/`lote_geocod` repassam `coordinates`
cru (só validação rasa) porque são pass-through de exibição. Aqui a geometria é **operada**
(interpolação + reprojeção), então — e **só** aqui — a `LineGeometry` do segmento escolhido é
convertida num `LineString` GEOS. Isso é legítimo: §7 permite os objetos de `django.contrib.gis.geos`
e as funções espaciais do GeoDjango no domínio (são neutros quanto à interface); o que §11 proíbe é
parsing manual de WKT/coordenadas **fora** do caminho GEOS/GDAL — exatamente o que evitamos usando
GEOS.

**Correção de orientação como peça separada (SRP §10.1).** O segmento vem do GeoServer com a ordem de
coordenadas arbitrária, que pode contrariar o sentido crescente da numeração — o que inverteria o ponto
dentro da quadra. O `SolverOrientacaoSegmento` decide, olhando o segmento **adjacente** na via, se a
linha precisa ser invertida antes de interpolar. É a mesma heurística do exemplo (comparação de
distâncias entre extremidades), reescrita sobre GEOS e desacoplada do geocoder por composição.

**Erros tipados do domínio.** Duas falhas distintas precisam de mensagens distintas na UI: o `codlog`
não ter segmentos (`SegmentoNaoEncontradoError`) e o número não cair em nenhum segmento
(`NumeracaoNaoEncontradaError`). Ficam como exceções próprias do módulo (padrão já usado pelas
`integrations`), neutras quanto a Django; a **view** (fora desta SPEC) as captura e renderiza o aviso
apropriado — a autorização/orquestração é responsabilidade da interface (§3.3).

**Envelope reutilizado.** A saída usa o `GeoFeature[GeomT, AttrT]` genérico de
`services/domain/geometry/`, agora parametrizado por `PointGeometry` + `EnderecoAttributes`. A
`PointGeometry` completa a trinca de representações (linha/polígono já existem) **compondo** a primitiva
`eh_ponto` que a SPEC 001 já entregou pronta para este momento.

## Peças de referência a compor
- `@services/domain/logradouro_geocod` → `LogradouroGeocoder`, `LogradouroGeocodInput`,
  `SegmentoLogradouroFeature`, `SegmentoLogradouroAttributes`: **fonte dos segmentos** (codlog → linhas
  + numeração par/ímpar). Compor por injeção; pedir os segmentos no CRS de interpolação.
- `@services/domain/geometry` → `GeoFeature`, `PolygonGeometry`/`LineGeometry` (espelho) e a primitiva
  `eh_ponto` (em `coordinates.py`): base para a nova `PointGeometry` e para o envelope de saída.
- `@services/domain/lote_geocod` e `@services/domain/logradouro_geocod` → padrão de módulo de
  geocodificação (models/geocoder/__init__, `__call__` fino delegando a `pipeline`, passos em métodos
  próprios): **estilo a espelhar**.
- `@services/domain/address_match` → domínio de endereço já existente (`parse_numero_imovel`): o
  `numero` chega **já parseado** (int) pela camada de roteamento/seleção; esta SPEC não reparsa número.
- `django.contrib.gis.geos` (`LineString`, `Point`, `GEOSGeometry`, `MultiLineString`): objetos
  geométricos e `interpolate_normalized`/`transform`, permitidos no domínio por §7.
- Configuração: `settings.WFS_LAYER_LOGRADOUROS` e `settings.MAP_OUTPUT_CRS` (já existem) **+ um novo
  CRS de interpolação/canônico projetado** (ex.: `MAP_INTERPOLATION_CRS = 31983`) a ser adicionado ao
  `settings` e lido **pela orquestração** — o domínio o recebe via DTO.
- Referência de porte: `@geocoder_example/` (`geocoder.py`, `orientacao_segmento.py`, `models.py`,
  `exceptions.py`) — lógica original em geopandas/shapely, aqui reescrita em GEOS e por composição.

## Snippets sugeridos

```python
# services/domain/geometry/models.py — acrescentar PointGeometry (espelha Line/Polygon)
from .coordinates import eh_ponto  # primitiva já entregue pela SPEC 001


class PointGeometry(BaseModel):
    """GeoJSON de ponto gerado no domínio. `coordinates` tem a forma `Position` (list[float] de
    tamanho 2) — ver `coordinates.py`. Validação estrutural rasa via `eh_ponto` (que também rejeita
    bool e posições 3D), por isso o campo é `list[Any]` e não `list[float]`: o alias documenta a
    forma sem delegar a checagem ao Pydantic (que coagiria bool→float e aceitaria posições 3D)."""
    type: Literal["Point"]
    coordinates: list[Any]

    @model_validator(mode="after")
    def _validar_forma(self) -> "PointGeometry":
        if not eh_ponto(self.coordinates):
            raise ValueError("coordinates não tem a forma de Point")
        return self
```

```python
# services/domain/geometry/__init__.py — passa a expor PointGeometry
from .models import GeoFeature, LineGeometry, PointGeometry, PolygonGeometry
from .serializers import to_geojson_feature_collection

__all__ = [
    "GeoFeature", "LineGeometry", "PointGeometry", "PolygonGeometry",
    "to_geojson_feature_collection",
]
```

```python
# services/domain/address_geocod/models.py — só DTOs Pydantic (contratos de entrada/saída)
from pydantic import BaseModel, Field

from services.domain.geometry import GeoFeature, PointGeometry


class AddressGeocodInput(BaseModel):
    codlog: str                 # repassado ao LogradouroGeocodInput (que valida a forma)
    numero: int = Field(gt=0)   # número do imóvel, já parseado (int) upstream
    layer_name: str             # camada de logradouros (settings, via orquestração)
    interpolation_crs: int      # CRS projetado p/ interpolar (ex.: 31983), via orquestração
    output_crs: int             # CRS de saída (ex.: 4326), via orquestração


class EnderecoAttributes(BaseModel):
    """Proveniência do ponto geocodificado (camada `attributes` da feature)."""
    codlog: str
    nome_logradouro: str
    cd_tipo_logradouro: str
    numero: int
    id_segmento: str            # segmento que originou a interpolação
    titulo: str | None = None


EnderecoFeature = GeoFeature[PointGeometry, EnderecoAttributes]
```

```python
# services/domain/address_geocod/numeracao.py — paridade + tradução paridade → colunas de numeração
from enum import Enum


class Paridade(Enum):
    IMPAR = 1
    PAR = 2


def intervalo_numeracao(
    attrs: object, paridade: Paridade
) -> tuple[int | None, int | None]:
    """Par (inicial, final) da numeração do lado par/ímpar do segmento. Compartilhado pelo
    geocoder e pelo solver de orientação — evita duplicar a tradução paridade → colunas."""
    if paridade is Paridade.PAR:
        return attrs.numero_inicial_par, attrs.numero_final_par  # type: ignore[attr-defined]
    return attrs.numero_inicial_impar, attrs.numero_final_impar  # type: ignore[attr-defined]
```

```python
# services/domain/address_geocod/exceptions.py
class SegmentoNaoEncontradoError(Exception):
    """Nenhum segmento retornado para o codlog informado."""


class NumeracaoNaoEncontradaError(Exception):
    """Há segmentos, mas nenhum cujo intervalo contém o número buscado."""
```

```python
# services/domain/address_geocod/orientacao.py — porte do SolverOrientacaoSegmento em GEOS
import json
import math

from django.contrib.gis.geos import GEOSGeometry, LineString, MultiLineString

from services.domain.geometry import LineGeometry
from services.domain.logradouro_geocod import SegmentoLogradouroFeature

from .numeracao import Paridade, intervalo_numeracao


def linha_geos(line: LineGeometry, srid: int) -> LineString:
    """LineGeometry -> LineString GEOS. MultiLineString é fundido (merged) quando contíguo;
    senão toma-se a parte mais longa. Único ponto de conversão coords -> objeto geométrico."""
    geom = GEOSGeometry(json.dumps({"type": line.type, "coordinates": line.coordinates}), srid=srid)
    if isinstance(geom, MultiLineString):
        fundido = geom.merged
        geom = fundido if isinstance(fundido, LineString) else max(geom, key=lambda p: p.length)
    return geom  # type: ignore[return-value]


class SolverOrientacaoSegmento:
    """Decide se a linha do segmento precisa ser invertida para casar com o sentido crescente
    da numeração, olhando o segmento adjacente. Composto pelo AddressGeocoder."""

    def __call__(
        self,
        escolhido: SegmentoLogradouroFeature,
        candidatos: list[SegmentoLogradouroFeature],
        paridade: Paridade,
        srid: int,
    ) -> LineString:
        linha = linha_geos(escolhido.geometry, srid)
        if self._orientacao_correta(escolhido, candidatos, paridade, srid, linha):
            return linha
        return LineString(list(linha.coords)[::-1], srid=srid)

    def _is_primeiro(self, escolhido, candidatos, paridade) -> bool:
        inicial, _ = intervalo_numeracao(escolhido.attributes, paridade)
        menor = min(intervalo_numeracao(c.attributes, paridade)[0] for c in candidatos)
        return inicial == menor

    def _adjacente(self, escolhido, candidatos, paridade) -> SegmentoLogradouroFeature:
        inicial, final = intervalo_numeracao(escolhido.attributes, paridade)
        if self._is_primeiro(escolhido, candidatos, paridade):
            # posteriores: começam onde este termina; o mais próximo é o adjacente
            posteriores = [c for c in candidatos if intervalo_numeracao(c.attributes, paridade)[0] >= final]
            return min(posteriores, key=lambda c: intervalo_numeracao(c.attributes, paridade)[0])
        anteriores = [c for c in candidatos if intervalo_numeracao(c.attributes, paridade)[1] <= inicial]
        return max(anteriores, key=lambda c: intervalo_numeracao(c.attributes, paridade)[1])

    def _orientacao_correta(self, escolhido, candidatos, paridade, srid, linha) -> bool:
        adjacente = self._adjacente(escolhido, candidatos, paridade)
        outra = linha_geos(adjacente.geometry, srid)
        if self._is_primeiro(escolhido, candidatos, paridade):
            ref, proximo, distante = linha.coords[-1], outra.coords[0], outra.coords[-1]
        else:
            ref, proximo, distante = linha.coords[0], outra.coords[-1], outra.coords[0]
        return math.dist(ref, distante) >= math.dist(ref, proximo)
```

```python
# services/domain/address_geocod/interpolacao.py — proporção do número + ponto interpolado/reprojetado
from django.contrib.gis.geos import LineString, Point

from services.domain.logradouro_geocod import SegmentoLogradouroFeature

from .numeracao import Paridade, intervalo_numeracao


class InterpoladorSegmento:
    """Interpola o ponto do número sobre a linha do segmento (no CRS de interpolação) e o reprojeta
    ao CRS de saída. Peça separada (SRP §10.1), composta pelo AddressGeocoder — par do
    SolverOrientacaoSegmento."""

    def __call__(
        self,
        linha: LineString,
        escolhido: SegmentoLogradouroFeature,
        numero: int,
        paridade: Paridade,
        interpolation_crs: int,
        output_crs: int,
    ) -> Point:
        proporcao = self._definir_proporcao(escolhido, numero, paridade)
        ponto: Point = linha.interpolate_normalized(proporcao)
        ponto.srid = interpolation_crs
        ponto.transform(output_crs)   # reprojeção centralizada (§7.3)
        return ponto

    def _definir_proporcao(
        self, escolhido: SegmentoLogradouroFeature, numero: int, paridade: Paridade
    ) -> float:
        # proporção normalizada do número no intervalo; sem intervalo (inicial == final) -> meio
        inicial, final = intervalo_numeracao(escolhido.attributes, paridade)
        if final == inicial:
            return 0.5
        return (numero - inicial) / (final - inicial)  # type: ignore[operator]
```

```python
# services/domain/address_geocod/geocoder.py
from django.contrib.gis.geos import Point

from services.domain.geometry import PointGeometry
from services.domain.logradouro_geocod import (
    LogradouroGeocodInput,
    LogradouroGeocoder,
    SegmentoLogradouroFeature,
)

from .exceptions import NumeracaoNaoEncontradaError, SegmentoNaoEncontradoError
from .interpolacao import InterpoladorSegmento
from .models import AddressGeocodInput, EnderecoAttributes, EnderecoFeature
from .numeracao import Paridade, intervalo_numeracao
from .orientacao import SolverOrientacaoSegmento


class AddressGeocoder:
    def __init__(self, logradouro_geocoder: LogradouroGeocoder) -> None:
        self._segmentos = logradouro_geocoder                 # composição (§10.4)
        self._corrigir_orientacao = SolverOrientacaoSegmento()
        self._interpolar = InterpoladorSegmento()

    def __call__(self, entrada: AddressGeocodInput) -> EnderecoFeature:
        return self.pipeline(entrada)                         # porta de entrada fina (§10.4)

    def pipeline(self, entrada: AddressGeocodInput) -> EnderecoFeature:
        paridade = self._definir_paridade(entrada.numero)
        segmentos = self._buscar_segmentos(entrada)
        candidatos = self._filtrar_com_numeracao(segmentos, paridade)
        escolhido = self._segmento_do_numero(candidatos, entrada.numero, paridade)
        linha = self._corrigir_orientacao(
            escolhido, candidatos, paridade, entrada.interpolation_crs
        )
        ponto = self._interpolar(
            linha, escolhido, entrada.numero, paridade,
            entrada.interpolation_crs, entrada.output_crs,
        )
        return self._montar_feature(ponto, escolhido, entrada)

    def _definir_paridade(self, numero: int) -> Paridade:
        return Paridade.PAR if numero % 2 == 0 else Paridade.IMPAR

    def _buscar_segmentos(
        self, entrada: AddressGeocodInput
    ) -> list[SegmentoLogradouroFeature]:
        # compõe o LogradouroGeocoder pedindo os segmentos JÁ no CRS de interpolação (métrico)
        segmentos = self._segmentos(LogradouroGeocodInput(
            codlog=entrada.codlog,
            layer_name=entrada.layer_name,
            output_crs=entrada.interpolation_crs,
        ))
        if not segmentos:
            raise SegmentoNaoEncontradoError(entrada.codlog)
        return segmentos

    def _filtrar_com_numeracao(
        self, segmentos: list[SegmentoLogradouroFeature], paridade: Paridade
    ) -> list[SegmentoLogradouroFeature]:
        # mantém só os segmentos com numeração para a paridade buscada (ambos os lados não nulos)
        return [
            s for s in segmentos
            if all(v is not None for v in intervalo_numeracao(s.attributes, paridade))
        ]

    def _segmento_do_numero(
        self, candidatos: list[SegmentoLogradouroFeature], numero: int, paridade: Paridade
    ) -> SegmentoLogradouroFeature:
        contem = [
            s for s in candidatos
            if intervalo_numeracao(s.attributes, paridade)[0] <= numero  # type: ignore[operator]
            <= intervalo_numeracao(s.attributes, paridade)[1]            # type: ignore[operator]
        ]
        if not contem:
            raise NumeracaoNaoEncontradaError(numero)
        return contem[0]   # mais de um: usa o primeiro (§critérios)

    def _montar_feature(
        self, ponto: Point, escolhido: SegmentoLogradouroFeature, entrada: AddressGeocodInput
    ) -> EnderecoFeature:
        a = escolhido.attributes
        return EnderecoFeature(
            geometry=PointGeometry(type="Point", coordinates=[ponto.x, ponto.y]),
            attributes=EnderecoAttributes(
                codlog=a.codlog,
                nome_logradouro=a.nome_logradouro,
                cd_tipo_logradouro=a.cd_tipo_logradouro,
                numero=entrada.numero,
                id_segmento=a.id_segmento,
                titulo=a.titulo,
            ),
            crs=entrada.output_crs,
        )
```

```python
# services/domain/address_geocod/__init__.py — só reexporta (§11)
from .exceptions import NumeracaoNaoEncontradaError, SegmentoNaoEncontradoError
from .geocoder import AddressGeocoder
from .models import AddressGeocodInput, EnderecoAttributes, EnderecoFeature
from .numeracao import Paridade

__all__ = [
    "AddressGeocoder",
    "AddressGeocodInput",
    "EnderecoAttributes",
    "EnderecoFeature",
    "NumeracaoNaoEncontradaError",
    "Paridade",
    "SegmentoNaoEncontradoError",
]
```

## Fora de escopo
- A **view/partial HTMX** que consome o serviço, a leitura de `settings` (camada + CRS), a construção
  do `LogradouroGeocoder`/`WfsFetcher` e a **captura das exceções** para renderizar aviso — orquestração,
  virá em SPEC de interface. A `address_geocoder:selecionar` segue hoje como *stub* (SPEC
  roteamento_busca/009); ligá-la a este serviço é iteração à parte.
- **Plotagem no mapa** (`apps/mapping` / Leaflet / WMS) e a **cor de ponto** (`MAP_COR_PONTO` ainda não
  existe no `settings`).
- **Adicionar o `MAP_INTERPOLATION_CRS` ao `settings`**: é ajuste de configuração/orquestração; a SPEC
  apenas assume o CRS injetado via DTO.
- O **caso especial do endereço fiscal exato** (pop-up ponto × polígono, item 4 do roadmap) — outra
  iteração; aqui só existe o caminho "endereço solto → interpolação".
- **Persistência** (GeoDjango `GeometryField`, CRS canônico de armazenamento) e **export** — não há
  gravação; o ponto é só devolvido para renderização.
- **Parsing do número** (marcadores/sufixos) — já feito por `services/domain/address_match`
  (`parse_numero_imovel`); o `numero` chega como `int`.
- **Match fuzzy / roteamento** — o `codlog` chega resolvido.

## Notas de teste
<Só para referência futura — não implementar agora.>
- Injetar um **fake `LogradouroGeocoder`** (callable que devolve `SegmentoLogradouroFeature` prontos,
  sem rede) — não é preciso mockar WFS, basta a fronteira de composição.
- Paridade: número par usa colunas `_par`; ímpar usa `_impar`. Segmento com o lado buscado nulo é
  descartado, mesmo que o outro lado tenha numeração.
- Seleção: número dentro de `[inicial, final]` acha o segmento; número fora de todos →
  `NumeracaoNaoEncontradaError`; codlog sem segmentos → `SegmentoNaoEncontradoError`; múltiplos
  segmentos contendo o número → retorna o primeiro.
- Interpolação: `inicial == final` → ponto médio (`proporcao = 0.5`); caso geral confere a proporção
  (ex.: `numero` no meio do intervalo → ~meio da linha). Conferir que o ponto sai **reprojetado** no
  `output_crs` (coordenadas plausíveis em 4326 para São Paulo, ~`[-46.6, -23.5]`).
- Orientação: montar segmento + adjacente com coords em ordem **invertida** em relação à numeração e
  confirmar que o solver inverte a linha (o ponto interpolado cai do lado correto da quadra); e o caso
  já correto passa sem inverter. Cobrir o ramo "primeiro segmento da via" (usa o **posterior** como
  adjacente) e o ramo comum (usa o **anterior**).
- `PointGeometry`: aceita `[lon, lat]` (2 números) e rejeita posição com 1 ou 3 números / `bool`
  (reusando `eh_ponto`). `GeoFeature[PointGeometry, EnderecoAttributes]` é instanciável.
- Borda MultiLineString: segmento cuja geometria é `MultiLineString` contíguo é fundido antes de
  interpolar; conferir que `linha_geos` devolve `LineString`.

## Patches

### Patch 001 (v6) — correção de orientação, via de segmento único, CRS pela feature e tipagem da injeção

Descoberto ao escrever os testes unitários (pedidos após a entrega). Quatro mudanças, nenhuma
altera o contrato dos DTOs (`AddressGeocodInput`/`EnderecoFeature` inalterados):

1. **Bugfix — correção de orientação não invertia.** A heurística portada (snippet original do
   `SolverOrientacaoSegmento`) comparava **uma** extremidade de `escolhido` contra as **duas** do
   segmento adjacente; num traçado colinear isso nunca detecta a inversão, e o ponto caía do lado
   errado da quadra. Passa a comparar **as duas extremidades de `escolhido`** contra o adjacente
   (cada uma via a extremidade mais próxima dele — robusto à orientação do próprio adjacente):
   decide qual ponta carrega a numeração baixa. O caso midpoint (`proporção == 0.5`) mascarava o bug
   no smoke test por ser direção-independente.

2. **Bugfix — via de segmento único quebrava.** `_adjacente` fazia `min()`/`max()` sobre lista
   vazia quando o `escolhido` não tem vizinho (logradouro de segmento único). Agora `_adjacente`
   devolve `SegmentoLogradouroFeature | None`; sem vizinho, `__call__` mantém a ordem de origem
   (não há como inferir orientação sem adjacente).

3. **Refactor — CRS vem da própria feature.** `linha_geos` deixa de receber `srid` como parâmetro e
   lê `feature.crs` (o envelope `GeoFeature` já carrega o CRS). O `interpolation_crs` fica com **um
   único ponto de uso** — a busca dos segmentos em `_buscar_segmentos` — e daí em diante o CRS
   "viaja" com a geometria (`feature.crs` → `linha.srid` → `ponto.srid`). O `SolverOrientacaoSegmento`
   e o `InterpoladorSegmento` deixam de receber o CRS. Também: o SRID é atribuído **após** construir
   o `GEOSGeometry` (que assume 4326 ao desserializar GeoJSON e recusa `srid` divergente no
   construtor), apenas rotulando as coordenadas cruas sem reprojetar.

4. **Refactor — dependência injetada tipada como Callable.** O construtor do `AddressGeocoder` passa
   a tipar `logradouro_geocoder` como `SegmentosDeCodlog = Callable[[LogradouroGeocodInput],
   list[SegmentoLogradouroFeature]]` (em vez do concreto `LogradouroGeocoder`), espelhando o padrão
   `WfsBatches` de `LogradouroGeocoder`/`LoteGeocoder` — mantém a composição desacoplada e testável
   por injeção (§3.3, §10.4).

Validação: `mypy`/`ruff` limpos; suíte unitária do módulo verde; teste de integração contra o WFS
real (Av. Paulista, 300 — codlog 156566) devolvendo ponto plausível em São Paulo.
