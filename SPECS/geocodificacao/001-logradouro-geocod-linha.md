---
spec: geocodificacao/001
versao: v11
atualizado_em: 2026-06-29
implementado: false
changelog:
  - v1: versão inicial
  - v2: LineGeometry passa a validar a forma do GeoJSON (lista de posições) em vez de coordinates Any
  - v3: validação fatorada em primitivas compostas (ponto ⊂ linha ⊂ coleção de linhas), reusáveis por ponto/polígono
  - v4: eh_ponto exige exatamente 2 números (dados 2D); posições 3D rejeitadas
  - v5: cadeia completa de primitivas (eh_colecao_de_linhas vira eh_poligono; +eh_multipoligono), pacote de geometria coerente
  - v6: eh_anel valida fechamento do polígono (>=4 pontos, primeiro == último); ramos aberto/fechado separados (+eh_multilinha)
  - v7: saída vira envelope GeoFeature genérico (geometry + attributes + crs); atributos do segmento extraídos para modelo próprio
  - v8: módulo realocado para services/domain/logradouro_geocod (irmão de lote_geocod e address_geocod), não mais sob address_match
  - v9: snippet do LogradouroGeocoder refatorado — `__call__` só delega a `pipeline`, que orquestra; passos extraídos em métodos próprios (montar request, mapear feature → segmento, montar atributos), seguindo §10.4. Filtro CQL usa `utils.cql_eq` direto (já devolve `CqlFilter`), eliminando o remonte de predicados
  - v10: CRS de saída deixa de ser constante de módulo e passa a ser injetado via DTO (`output_crs`, código EPSG inteiro), resolvido pela orquestração a partir do settings do Django; `srs_name` derivado dele e `crs` da feature ecoa o valor recebido
  - v11: campos de numeração (`numero_inicial_par`/`numero_final_par`/`numero_inicial_impar`/`numero_final_impar`) passam de `str | None` para `int | None`; opcionais separados em texto (`_as_str`) e numéricos (`_as_int`, tolerando ""/None)
---

# SPEC geocodificacao/001 — Geocodificação de logradouro por codlog (codlog → linha)

- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como desenvolvedor do domínio, quero um serviço que receba um `codlog` e busque na camada de
logradouros do WFS todos os segmentos viários (faces de quadra) cujo `codlog` bate exatamente com o
informado, devolvendo cada um com sua geometria de linha e seus metadados traduzidos, para que a UI
possa renderizar a linha do logradouro no Leaflet e a geocodificação de endereços possa interpolar a
numeração sobre os segmentos.

## Critérios de aceite
- [ ] O serviço reside em `services/domain/logradouro_geocod/`, não importa recursos do
      Django e compõe o `WfsFetcher` pelo callable injetado (não acopla à classe).
- [ ] A entrada é um DTO Pydantic com `codlog`, o nome da camada de logradouros (`layer_name`) **e o
      CRS de saída** (`output_crs`, código EPSG inteiro); tanto a camada quanto o CRS são resolvidos
      pela orquestração a partir do `settings` e injetados no DTO — o domínio **nunca** lê `settings`
      nem fixa o CRS como constante de módulo.
- [ ] A consulta WFS filtra por **match exato** `codlog = <input>` usando `CqlFilter`/`utils.cql_eq`
      (nunca concatenando strings), pois `codlog` é identificador exato (§7.3).
- [ ] A consulta retorna **a geometria** dos segmentos (não restringir `property_names` a ponto de
      derrubar a geometria) e solicita as feições já no CRS recebido — via `srs_name` derivado do
      `output_crs` (ex.: `EPSG:4326`, pronto para o Leaflet) — sem reprojeção manual no código (§7.3).
- [ ] **Todos** os segmentos do `codlog` são retornados (um codlog tem N faces de quadra); nenhuma
      deduplicação é aplicada.
- [ ] A saída é uma lista de **features**, uma por segmento, no formato de envelope (estilo GeoJSON
      Feature) com **três camadas**: `geometry` (a representação de linha centralizada), `attributes`
      (um DTO Pydantic com os atributos do segmento, traduzidos — ver tabela) e `crs` (o SRID/EPSG
      inteiro da geometria; é exatamente o `output_crs` recebido, já que pedimos esse CRS ao WFS).
- [ ] O envelope `geometry`/`attributes`/`crs` é um modelo **genérico** centralizado em
      `services/domain/geometry/`, parametrizado pelo tipo de geometria e pelo modelo de atributos —
      reusável depois por endereço→ponto e lote→polígono. O **modelo de atributos é específico** do
      segmento de logradouro (mora no módulo `logradouro_geocod`). Os campos de `attributes`:

      | Atributo WFS (origem)       | Campo em `attributes`   | Nulável |
      |-----------------------------|-------------------------|---------|
      | `cd_identificador`          | `id_segmento`           | não     |
      | `codlog`                    | `codlog`                | não     |
      | `tipo_logradouro`           | `cd_tipo_logradouro`    | não     |
      | `nm_logradouro`             | `nome_logradouro`       | não     |
      | `cd_titulo_logradouro`      | `titulo`                | sim     |
      | `tx_preposicao_logradouro`  | `preposicao`            | sim     |
      | `cd_numero_inicial_par`     | `numero_inicial_par`    | sim     |
      | `cd_numero_final_par`       | `numero_final_par`      | sim     |
      | `cd_numero_inicial_impar`   | `numero_inicial_impar`  | sim     |
      | `cd_numero_final_impar`     | `numero_final_impar`    | sim     |

- [ ] A geometria **não é convertida em objeto geométrico nem reprojetada no código**: passa apenas
      pela validação estrutural rasa do `LineGeometry` (tipo + forma) e é repassada como está, para
      ser enviada ao Leaflet no front posteriormente.
- [ ] A validação de **forma** do GeoJSON vive em **primitivas estruturais compostas** no pacote
      `services/domain/geometry/`, espelhando o aninhamento da RFC 7946. Como um anel de polígono é
      uma linha **fechada**, há dois ramos a partir da linha — aberto (`ponto → linha → multilinha`) e
      fechado (`linha → anel → polígono → multipolígono`): `eh_ponto` (posição 2D `[lon, lat]` —
      **exatamente 2** números), `eh_linha` (lista de ≥ 2 pontos, **compõe** `eh_ponto`),
      `eh_multilinha` (lista de ≥ 1 linha, **compõe** `eh_linha`), `eh_anel` (linha **fechada**: ≥ 4
      pontos e primeiro == último, **compõe** `eh_linha`), `eh_poligono` (lista de ≥ 1 anel, **compõe**
      `eh_anel`) e `eh_multipoligono` (lista de ≥ 1 polígono, **compõe** `eh_poligono`). A checagem é
      **rasa** (amostra inicial; no anel inclui o fechamento, mas não varre todos os vértices nem os
      anéis internos/buracos) e **não** converte `coordinates` em objeto geométrico (GEOS/GDAL) nem
      reprojeta.
- [ ] As primitivas são entregues nesta SPEC para deixar o pacote de geometria **completo e
      coerente**, ainda que apenas as de linha sejam consumidas agora. `LineGeometry` (exposto pelo
      `__init__.py` do pacote) usa `eh_linha` para `LineString` e `eh_multilinha` para
      `MultiLineString` (linhas **abertas** — não reusa `eh_poligono`, cujos anéis são fechados).
      `eh_ponto`/`eh_anel`/`eh_poligono`/`eh_multipoligono` ficam prontas para reuso, sem reescrita,
      pelos futuros `PointGeometry`, `PolygonGeometry` e `MultiPolygonGeometry`.
- [ ] Feições sem geometria de linha válida ou sem algum dos campos obrigatórios (`id_segmento`,
      `codlog`, `cd_tipo_logradouro`, `nome_logradouro`) são descartadas.
- [ ] Tipagem estrita compatível com `mypy`; sem `from __future__`.

## Contexto e decisões de arquitetura
Mexe **apenas no domínio** (`services/`). É o primeiro tijolo do épico de geocodificação: a
resolução de um `codlog` na sua geometria de linha.

**Lugar na arquitetura de geocodificação.** O épico tem três módulos de domínio irmãos em
`services/domain/`, cada um com responsabilidade única (§10.1): `logradouro_geocod` (codlog →
linha — **este**), `lote_geocod` (nº de contribuinte → polígono) e `address_geocod` (endereço →
ponto, a geocodificação propriamente dita). `logradouro_geocod` e `lote_geocod` são usados **direto**
(busca de logradouro e busca de lote) **e** compostos pelo `address_geocod`: ele usa o
`logradouro_geocod` para obter os segmentos de reta e **interpolar** o número, e o `lote_geocod`
quando o endereço digitado bate exatamente com o endereço de um lote. Por isso `logradouro_geocod`
nasce como módulo de topo, independente — não dentro de um "address_*".

O serviço **compõe** o `WfsFetcher` (§3.3, §10.4): recebe o callable de batches no construtor e
itera as páginas, montando os DTOs de saída. Como `codlog` é identificador exato, o casamento é por
filtro CQL `=` (match direto, §7.3) — sem variações nem fuzzy.

**Saída em envelope de três camadas (`GeoFeature`).** Cada segmento é devolvido como uma *feature*
estilo GeoJSON: `geometry` (a `LineGeometry`), `attributes` (DTO com os atributos do segmento) e
`crs` (SRID inteiro = o `output_crs` injetado, tipicamente 4326). O envelope é um modelo **genérico**
(`GeoFeature[GeomT, AttrT]`) no
pacote `services/domain/geometry/`, para que endereço→ponto e lote→polígono reusem a mesma estrutura,
trocando só o tipo de geometria e o modelo de `attributes`. Separar `attributes` num modelo próprio
(em vez de campos achatados na feature) mantém a geometria, os metadados e o CRS em camadas distintas
e deixa o `attributes` específico do domínio onde ele pertence (no módulo `logradouro_geocod`).

**Geometria leve (sem parsing).** Diferente do script de segmentos (`ingestao_dados/004`), que omite
geometria, aqui a geometria é o produto principal — mas o domínio **não a interpreta**: pede ao WFS
as feições já no **CRS recebido** (`srs_name` derivado do `output_crs` injetado, tipicamente
EPSG:4326), valida só o **tipo** (linha) e repassa o `coordinates`
cru. Isso honra §7.3 (nada de reprojeção manual; a transformação fica a cargo do GeoServer) e mantém
o payload pronto para o Leaflet sem trafegar geometria pesada por parsing desnecessário.

**Representação de geometria centralizada e composta (`services/domain/geometry/`).** Para não
espalhar formatos de geometria pelo código, criamos um pacote "core" de geometria no domínio. A
validação de forma segue o **aninhamento da RFC 7946**, com uma sutileza: um **anel** de polígono é
uma linha **fechada** (≥ 4 pontos, primeiro == último), o que separa um ramo "aberto" de um
"fechado" a partir da linha. Daí seis primitivas que **compõem** umas às outras — aberto:
`eh_ponto → eh_linha → eh_multilinha`; fechado: `eh_linha → eh_anel → eh_poligono → eh_multipoligono`
— em vez de reescrever a checagem por tipo. As de linha já são exigidas pelo próprio `LineGeometry`
(`LineString` usa `eh_linha`; `MultiLineString` usa `eh_multilinha`); as demais são entregues junto
para deixar o pacote **completo e coerente** desde já. A representação **linha** (`LineGeometry`) é a
única instanciada nesta SPEC; `PointGeometry`, `PolygonGeometry` e `MultiPolygonGeometry` virão em
SPECs próprias (fluxos endereço → ponto e lote → polígono), reaproveitando exatamente as mesmas
primitivas — inclusive a validação de fechamento do anel.

**Autorização / orquestração fora do domínio.** Quem lê `settings` (conexão WFS + nome da camada de
logradouros + CRS de saída) e constrói o `WfsFetcher` é a orquestração (view), que injeta tudo no
serviço. Esta SPEC
cobre o serviço de domínio e a representação de geometria; a view/partial HTMX que o consome fica
para outra iteração.

## Peças de referência a compor
- `@services/integrations/wfs` → `WfsFetcher`, `WfsFeatureRequest`, `WfsFeatureCollection`,
  `CqlFilter`/`utils.cql_eq`: comunicação paginada e filtro CQL com escape. Importar pelo nível
  superior `services.integrations.wfs`.
- `@services/scripts/segmentos_logradouros` → `SegmentosLogradourosExtractor`: padrão de composição
  do fetcher callable e de leitura/normalização de `properties` a reaproveitar como referência de
  estilo (esta SPEC adiciona a geometria, que aquele script omite de propósito).
- `@services/domain/codlog_match` → `CodlogMatchOutput`: referência de como já nomeamos
  `codlog`/`tipo_logradouro`/`nome_logradouro` no domínio (consistência de vocabulário).
- Configuração `settings.WFS_*` e `settings.WFS_LAYER_LOGRADOUROS`: já usadas pela orquestração do
  épico de ingestão; reaproveitar na view que vier a consumir este serviço.

## Snippets sugeridos
```python
# services/domain/geometry/coordinates.py
# Primitivas estruturais do GeoJSON 2D (RFC 7946), compostas por aninhamento — cada uma reusa a
# anterior. Dois "mundos" a partir da linha, porque um anel de polígono é uma linha FECHADA:
#   aberto:   ponto → linha → multilinha          (MultiLineString = lista de linhas abertas)
#   fechado:  linha → anel  → polígono → multipolígono
# Checagem RASA (só a amostra inicial e, no anel, o fechamento), sem converter em objeto geométrico
# nem varrer todos os vértices. Internas ao pacote (o __init__ não as reexporta).
from typing import Any


def eh_ponto(coords: Any) -> bool:
    """Um PONTO é uma posição GeoJSON 2D: sequência com exatamente 2 números [lon, lat].
    Trabalhamos só com dados 2D — posições 3D (com z) são rejeitadas de propósito."""
    # `bool` é subclasse de `int` em Python (isinstance(True, int) é True); o `not isinstance`
    # impede que True/False passem como coordenada.
    return (
        isinstance(coords, (list, tuple))
        and len(coords) == 2
        and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in coords)
    )


def eh_linha(coords: Any) -> bool:
    """Uma LINHA (aberta) é uma lista de >= 2 pontos. Compõe `eh_ponto`."""
    return isinstance(coords, list) and len(coords) >= 2 and eh_ponto(coords[0])


def eh_multilinha(coords: Any) -> bool:
    """Uma MULTILINHA é uma lista de >= 1 linha (aberta). Compõe `eh_linha`."""
    return isinstance(coords, list) and len(coords) >= 1 and eh_linha(coords[0])


def eh_anel(coords: Any) -> bool:
    """Um ANEL é uma linha FECHADA: >= 4 pontos e primeiro == último. Compõe `eh_linha`.
    A igualdade é exata (a RFC manda repetir a posição idêntica, não 'aproximadamente igual');
    comparar duas listas [lon, lat] com == já compara coordenada a coordenada."""
    return eh_linha(coords) and len(coords) >= 4 and coords[0] == coords[-1]


def eh_poligono(coords: Any) -> bool:
    """Um POLÍGONO é uma lista de >= 1 anel. Compõe `eh_anel` (valida o fechamento do 1º anel).
    Checagem rasa: só o anel-amostra (exterior) é verificado; anéis internos (buracos) não."""
    return isinstance(coords, list) and len(coords) >= 1 and eh_anel(coords[0])


def eh_multipoligono(coords: Any) -> bool:
    """Um MULTIPOLÍGONO é uma lista de >= 1 polígono. Compõe `eh_poligono`."""
    return isinstance(coords, list) and len(coords) >= 1 and eh_poligono(coords[0])
```

```python
# services/domain/geometry/models.py  — representações centralizadas de geometria
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, model_validator

from .coordinates import eh_linha, eh_multilinha


class LineGeometry(BaseModel):
    """GeoJSON de linha vindo do WFS. Validação estrutural rasa da forma de `coordinates`
    (sem converter em objeto geométrico nem varrer todos os vértices)."""
    type: Literal["LineString", "MultiLineString"]
    coordinates: list[Any]

    @model_validator(mode="after")
    def _validar_forma(self) -> "LineGeometry":
        # LineString = lista de pontos; MultiLineString = lista de linhas (abertas, sem fechamento)
        valida = eh_linha if self.type == "LineString" else eh_multilinha
        if not valida(self.coordinates):
            raise ValueError(f"coordinates não tem a forma de {self.type}")
        return self


GeomT = TypeVar("GeomT", bound=BaseModel)   # LineGeometry hoje; PointGeometry/PolygonGeometry depois
AttrT = TypeVar("AttrT", bound=BaseModel)   # modelo de atributos específico do domínio


class GeoFeature(BaseModel, Generic[GeomT, AttrT]):
    """Envelope estilo GeoJSON Feature: geometria + atributos do domínio + CRS (SRID inteiro).
    Genérico para ser reusado por qualquer resultado de geocodificação (linha/ponto/polígono),
    com `attributes` tipado pelo modelo específico de cada 'bicho'."""
    geometry: GeomT
    attributes: AttrT
    crs: int
```

```python
# services/domain/geometry/__init__.py  — só reexporta (§11)
from .models import GeoFeature, LineGeometry

__all__ = ["GeoFeature", "LineGeometry"]
```

```python
# services/domain/logradouro_geocod/models.py
from pydantic import BaseModel

from services.domain.geometry import GeoFeature, LineGeometry


class LogradouroGeocodInput(BaseModel):
    codlog: str
    layer_name: str  # camada de logradouros, resolvida pela orquestração a partir do settings
    output_crs: int  # código EPSG de saída (ex.: 4326), injetado pela orquestração via settings


class SegmentoLogradouroAttributes(BaseModel):
    """Atributos do segmento de logradouro (camada `attributes` da feature)."""
    id_segmento: str
    codlog: str
    cd_tipo_logradouro: str
    nome_logradouro: str
    titulo: str | None = None
    preposicao: str | None = None
    numero_inicial_par: int | None = None
    numero_final_par: int | None = None
    numero_inicial_impar: int | None = None
    numero_final_impar: int | None = None


# envelope concreto: linha + atributos do segmento + CRS. Instanciável e usável como anotação.
SegmentoLogradouroFeature = GeoFeature[LineGeometry, SegmentoLogradouroAttributes]
```

```python
# services/domain/logradouro_geocod/geocoder.py
from collections.abc import Callable, Iterable

from services.integrations.wfs import (
    WfsFeatureCollection,
    WfsFeatureRequest,
    utils,
)
from services.domain.geometry import LineGeometry

from .models import (
    LogradouroGeocodInput,
    SegmentoLogradouroAttributes,
    SegmentoLogradouroFeature,
)

WfsBatches = Callable[[WfsFeatureRequest], Iterable[WfsFeatureCollection]]

PAGE_SIZE: int = 10_000
# O CRS de saída NÃO é constante de módulo: vem injetado no DTO (entrada.output_crs),
# resolvido pela orquestração a partir do settings do Django (§3.3, §7.3).

# tradução atributo WFS -> campo do DTO (campos opcionais), separados por tipo de saída
_OPCIONAIS_TEXTO: dict[str, str] = {
    "cd_titulo_logradouro": "titulo",
    "tx_preposicao_logradouro": "preposicao",
}
_OPCIONAIS_NUMERO: dict[str, str] = {
    "cd_numero_inicial_par": "numero_inicial_par",
    "cd_numero_final_par": "numero_final_par",
    "cd_numero_inicial_impar": "numero_inicial_impar",
    "cd_numero_final_impar": "numero_final_impar",
}


def _as_str(value: object) -> str | None:
    return None if value is None else str(value)


def _as_int(value: object) -> int | None:
    # numeração do imóvel; WFS pode trazer "", None ou já um número
    if value is None or value == "":
        return None
    return int(value)  # type: ignore[arg-type]


class LogradouroGeocoder:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, entrada: LogradouroGeocodInput) -> list[SegmentoLogradouroFeature]:
        # ponto de entrada fino (§10.4): só delega ao pipeline, que orquestra os passos
        return self.pipeline(entrada)

    def pipeline(self, entrada: LogradouroGeocodInput) -> list[SegmentoLogradouroFeature]:
        # orquestra a sequência: monta o request, pagina o WFS e mapeia cada feição
        request = self._montar_request(entrada)
        segmentos: list[SegmentoLogradouroFeature] = []
        for page in self.fetcher(request):
            for feature in page.features:
                segmento = self._feature_para_segmento(feature, entrada.output_crs)
                if segmento is not None:
                    segmentos.append(segmento)
        return segmentos

    def _montar_request(self, entrada: LogradouroGeocodInput) -> WfsFeatureRequest:
        return WfsFeatureRequest(
            nome_camada=entrada.layer_name,
            cql_filter=utils.cql_eq("codlog", entrada.codlog),  # já devolve um CqlFilter pronto
            srs_name=f"EPSG:{entrada.output_crs}",  # CRS injetado; reprojeção a cargo do WFS
            count=PAGE_SIZE,
            # sem property_names: restringir derrubaria a geometria no GeoServer
        )

    def _feature_para_segmento(
        self, feature: object, output_crs: int
    ) -> SegmentoLogradouroFeature | None:
        # uma feição WFS -> um segmento; devolve None quando a feição é descartada
        props = feature.properties
        id_segmento = _as_str(props.get("cd_identificador"))
        codlog = _as_str(props.get("codlog"))
        cd_tipo = _as_str(props.get("tipo_logradouro"))
        nome = _as_str(props.get("nm_logradouro"))
        if not (feature.geometry and id_segmento and codlog and cd_tipo and nome):
            return None
        return SegmentoLogradouroFeature(
            geometry=LineGeometry.model_validate(feature.geometry.model_dump()),
            attributes=self._montar_attributes(props, id_segmento, codlog, cd_tipo, nome),
            crs=output_crs,
        )

    def _montar_attributes(
        self,
        props: dict[str, object],
        id_segmento: str,
        codlog: str,
        cd_tipo: str,
        nome: str,
    ) -> SegmentoLogradouroAttributes:
        return SegmentoLogradouroAttributes(
            id_segmento=id_segmento,
            codlog=codlog,
            cd_tipo_logradouro=cd_tipo,
            nome_logradouro=nome,
            **{campo: _as_str(props.get(origem)) for origem, campo in _OPCIONAIS_TEXTO.items()},
            **{campo: _as_int(props.get(origem)) for origem, campo in _OPCIONAIS_NUMERO.items()},
        )
```

```python
# services/domain/logradouro_geocod/__init__.py  — só reexporta (§11)
from .geocoder import LogradouroGeocoder
from .models import (
    LogradouroGeocodInput,
    SegmentoLogradouroAttributes,
    SegmentoLogradouroFeature,
)

__all__ = [
    "LogradouroGeocoder",
    "LogradouroGeocodInput",
    "SegmentoLogradouroAttributes",
    "SegmentoLogradouroFeature",
]
```

## Fora de escopo
- A **view/partial HTMX** que consome o serviço, a leitura de `settings` e a construção do
  `WfsFetcher` (orquestração) — virão na SPEC da interface de busca de logradouro.
- Os **models** de geometria `PointGeometry`/`PolygonGeometry`/`MultiPolygonGeometry`: esta SPEC
  instancia apenas `LineGeometry`. (As **primitivas** de validação de todas as formas, essas sim, são
  entregues no pacote — ver §"Representação de geometria centralizada e composta".)
- **Interpolação de numeração** (endereço → ponto) sobre os segmentos retornados.
- Persistência (GeoDjango / `GeometryField`), CRS canônico de armazenamento e export — não há
  gravação aqui; a geometria é só repassada para renderização.
- **Conversão de `coordinates` em objetos geométricos** (GEOS/GDAL) ou reprojeção manual. A
  validação do `LineGeometry` é só estrutural/rasa, não interpreta a geometria.

## Notas de teste
- Injetar um **fake callable** que devolve `WfsFeatureCollection` prontas (sem rede), no padrão de
  `segmentos_logradouros`.
- Casos: múltiplos segmentos para um mesmo `codlog` (todos retornados); tradução correta de cada
  atributo; preservação de nulos nos campos opcionais (incl. numeração vazia `""`/ausente → `None`)
  e conversão para `int` dos campos de numeração presentes; descarte de feição sem geometria; descarte de
  feição faltando campo obrigatório; geometria com `type` inválido (não-linha) rejeitada pela
  validação de `LineGeometry`.
- Verificar que o `WfsFeatureRequest` montado carrega o filtro `codlog = <input>` e o `srs_name`
  derivado do `output_crs` injetado (ex.: `output_crs=4326` → `srs_name == "EPSG:4326"`).
- Envelope: cada item da saída é um `GeoFeature` com `geometry` (`LineGeometry`), `attributes`
  (`SegmentoLogradouroAttributes` com os campos traduzidos) e `crs` igual ao `output_crs` injetado.
  Confirmar que
  `GeoFeature[LineGeometry, SegmentoLogradouroAttributes]` é instanciável e rejeita geometria de
  forma inválida (via validação do `LineGeometry`).
- Primitivas de geometria: `eh_ponto` rejeita posição com 1 ou 3 números e rejeita `bool`; `eh_anel`
  rejeita anel aberto (primeiro != último) e com < 4 pontos, e aceita anel fechado válido; `eh_poligono`
  /`eh_multipoligono` aceitam a forma aninhada correta e rejeitam profundidade errada. Confirmar que
  `eh_multilinha` (MultiLineString) **não** exige fechamento, ao contrário de `eh_anel`.

## Patches

_Nenhum patch registrado até o momento._
