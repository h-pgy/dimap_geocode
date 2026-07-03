---
spec: geocodificacao/002
versao: v1
atualizado_em: 2026-06-29
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC geocodificacao/002 — Geocodificação de lote por nº de contribuinte (setor/quadra/lote → polígono)

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como desenvolvedor do domínio, quero um serviço que receba a numeração de um lote fiscal
(setor + quadra + lote) já desmembrada e filtrada por tipo de lote, e busque na camada de lotes do
WFS o(s) polígono(s) cujo identificador bate exatamente com o informado, devolvendo cada um com sua
geometria de polígono e seus metadados traduzidos, para que a UI possa renderizar o polígono do lote
no Leaflet e o fluxo de endereço fiscal exato possa partir do polígono do lote.

## Critérios de aceite
- [ ] O serviço reside em `services/domain/lote_geocod/`, não importa recursos do Django e compõe o
      `WfsFetcher` pelo callable injetado (não acopla à classe). É **irmão** de `logradouro_geocod` em
      `services/domain/`, com a mesma forma (§10.1).
- [ ] A entrada é um DTO Pydantic com `setor` (3 dígitos), `quadra` (3 dígitos), `lote` (4 dígitos),
      `tipo_lote` (código do `cd_tipo_lote`), o nome da camada de lotes (`layer_name`) **e o CRS de
      saída** (`output_crs`, código EPSG inteiro). A camada e o CRS são resolvidos pela orquestração a
      partir do `settings` (`WFS_LAYER_LOTE_CIDADAO` e o CRS de exibição) e injetados no DTO — o
      domínio **nunca** lê `settings` nem fixa o CRS como constante de módulo.
- [ ] Os códigos chegam **zero-padded** (mesma normalização da carga): `setor`/`quadra` com pattern
      `^\d{3}$`, `lote` com `^\d{4}$`. São identificadores **exatos** (§7.3) — diferente do
      `contribuinte_match`, que casa por prefixo para sugerir; aqui é o **match final** do lote
      escolhido.
- [ ] A consulta WFS filtra por **match exato** combinando `cd_setor_fiscal = <setor>` **AND**
      `cd_quadra_fiscal = <quadra>` **AND** `cd_lote = <lote>` **AND** `cd_tipo_lote = <tipo_lote>`,
      montando um único `CqlFilter` com vários `CqlPredicate` (`logic="AND"`) — nunca concatenando
      strings —, pois toda a numeração do contribuinte é identificador exato (§7.3).
- [ ] A consulta retorna **a geometria** dos polígonos (não restringir `property_names` a ponto de
      derrubar a geometria) e solicita as feições já no CRS recebido — via `srs_name` derivado do
      `output_crs` (ex.: `EPSG:4326`, pronto para o Leaflet) — sem reprojeção manual no código (§7.3).
- [ ] **Todas** as feições que casam são retornadas (um lote pode vir como uma ou mais feições —
      ex.: condomínio); nenhuma deduplicação é aplicada.
- [ ] A saída é uma lista de **features**, uma por feição, no formato de envelope (estilo GeoJSON
      Feature) reusando o `GeoFeature` genérico de `services/domain/geometry/`, com **três camadas**:
      `geometry` (a representação de polígono centralizada), `attributes` (um DTO Pydantic com os
      atributos do lote, traduzidos — ver tabela) e `crs` (o SRID/EPSG inteiro da geometria; é
      exatamente o `output_crs` recebido). Os campos de `attributes`:

      | Atributo WFS (origem) | Campo em `attributes` | Nulável |
      |-----------------------|-----------------------|---------|
      | `cd_identificador`    | `id_poligono`         | não     |
      | `cd_setor_fiscal`     | `setor`               | não     |
      | `cd_quadra_fiscal`    | `quadra`              | não     |
      | `cd_lote`             | `lote`                | não     |
      | `cd_tipo_lote`        | `tipo_lote`           | não     |
      | `cd_tipo_quadra`      | `tipo_quadra`         | sim     |
      | `cd_condominio`       | `condominio`          | sim     |

- [ ] A geometria **não é convertida em objeto geométrico nem reprojetada no código**: passa apenas
      pela validação estrutural rasa do novo `PolygonGeometry` (tipo + forma) e é repassada como está,
      para ser enviada ao Leaflet no front posteriormente.
- [ ] É adicionado ao pacote `services/domain/geometry/` o model **`PolygonGeometry`**, que
      **reaproveita as primitivas já existentes** `eh_poligono`/`eh_multipoligono` (entregues na
      geocodificacao/001) — **sem reescrevê-las**. Ele aceita `type: Literal["Polygon", "MultiPolygon"]`
      e valida `Polygon` com `eh_poligono` e `MultiPolygon` com `eh_multipoligono`, espelhando
      **exatamente** o desenho do `LineGeometry` (um único model cobrindo o tipo simples e o múltiplo).
      `PolygonGeometry` passa a ser **reexportado** pelo `__init__.py` do pacote de geometria (§11).
- [ ] Feições sem geometria de polígono válida ou sem algum dos campos obrigatórios (`id_poligono`,
      `setor`, `quadra`, `lote`, `tipo_lote`) são descartadas.
- [ ] O serviço é **callable**: `__call__` apenas delega a `pipeline`, que orquestra (montar request,
      paginar o WFS, mapear cada feição → feature de lote); cada passo é um método próprio (§10.4),
      espelhando o `LogradouroGeocoder`.
- [ ] Tipagem estrita compatível com `mypy`; sem `from __future__`.

## Contexto e decisões de arquitetura
Mexe **apenas no domínio** (`services/`). É o segundo tijolo do épico de geocodificação, gêmeo da
geocodificacao/001 (codlog → linha): aqui a numeração de contribuinte resolve no **polígono** do lote.

**Lugar na arquitetura de geocodificação.** O épico tem três módulos de domínio irmãos em
`services/domain/`: `logradouro_geocod` (codlog → linha), `lote_geocod` (nº de contribuinte → polígono
— **este**) e `address_geocod` (endereço → ponto). `lote_geocod` é usado **direto** (busca de lote por
contribuinte) **e** será composto pelo `address_geocod` quando o endereço digitado bater exatamente com
o endereço de um lote (caso do pop-up ponto vs. polígono — fora desta SPEC). Por isso nasce como módulo
de topo, independente.

**Exato, não por prefixo (relação com `contribuinte_match`).** O `contribuinte_match`
(roteamento-busca/006) casa por **prefixo** sobre a base local de endereços fiscais para **sugerir**
lotes enquanto o usuário digita. Esta SPEC é o passo seguinte: o usuário **escolheu** uma sugestão (ou
preencheu a busca detalhada) e agora resolvemos a numeração **completa e exata** na sua geometria,
indo ao **WFS** da camada de lotes. São responsabilidades distintas (sugerir × geocodificar) e domínios
separados — por isso um módulo novo, não uma extensão do matcher.

**Filtro CQL composto (AND de exatos).** Diferente do codlog (um único campo), o lote é identificado
por **setor + quadra + lote**, e ainda restringimos por **tipo de lote**. Como os helpers
`utils.cql_eq` produzem filtros de **um** predicado, aqui montamos diretamente um `CqlFilter` com a
lista de `CqlPredicate` e `logic="AND"` — tudo `op="="` (match exato, §7.3). É a montagem natural do
contrato do integrador; o escape dos literais continua a cargo do `CqlPredicate`.

**Saída em envelope de três camadas (`GeoFeature`).** Reaproveita **integralmente** o `GeoFeature`
genérico de `services/domain/geometry/` (criado na 001), trocando só o tipo de geometria
(`PolygonGeometry`) e o modelo de `attributes` (específico do lote, mora em `lote_geocod`). Mantém a
geometria, os metadados e o CRS em camadas distintas, igual ao logradouro.

**Geometria leve (sem parsing).** Igual à 001: a geometria é o produto principal, mas o domínio **não
a interpreta**. Pede ao WFS as feições já no **CRS recebido** (`srs_name` derivado do `output_crs`),
valida só o **tipo/forma** (polígono) via `PolygonGeometry` e repassa o `coordinates` cru. Honra §7.3
(reprojeção a cargo do GeoServer) e mantém o payload pronto para o Leaflet.

**`PolygonGeometry` fecha o pacote de geometria.** As primitivas `eh_poligono`/`eh_multipoligono` já
foram entregues na 001 (pacote "completo e coerente"), justamente para que esta SPEC só **instancie** o
model que as consome — sem reescrever validação. O desenho espelha o `LineGeometry`: um único model com
`type: Literal["Polygon", "MultiPolygon"]` que escolhe a primitiva conforme o tipo. A validação é
**rasa** (amostra do anel exterior + fechamento), não converte em objeto geométrico (GEOS/GDAL) nem
reprojeta.

**Autorização / orquestração fora do domínio.** Quem lê `settings` (conexão WFS + camada de lotes +
CRS de saída) e constrói o `WfsFetcher` é a orquestração (view), que injeta tudo no serviço. Esta SPEC
cobre o serviço de domínio e o `PolygonGeometry`; a view/partial HTMX que o consome (clique na sugestão
de contribuinte → polígono no mapa) fica para outra iteração.

## Peças de referência a compor
- `@services/domain/geometry` → `GeoFeature` (envelope genérico) e as primitivas `eh_poligono`/
  `eh_multipoligono` (já existentes): **reusadas** pelo novo `PolygonGeometry`. Importar pelo nível
  superior `services.domain.geometry`.
- `@services/domain/logradouro_geocod` → `LogradouroGeocoder` / `SegmentoLogradouroFeature`: **padrão
  estrutural a espelhar** (callable + `pipeline` + passos; envelope `geometry`/`attributes`/`crs`;
  descarte de feição incompleta). Esta SPEC é o gêmeo de polígono.
- `@services/integrations/wfs` → `WfsFetcher`, `WfsFeatureRequest`, `WfsFeatureCollection`,
  `CqlFilter`/`CqlPredicate`: comunicação paginada e filtro CQL composto com escape. Importar pelo
  nível superior `services.integrations.wfs`.
- `@services/domain/contribuinte_match` → `ContribuinteMatchOutput`: referência de vocabulário já
  usado para o lote (`setor`/`quadra`/`lote`/`tipo_lote`/`id_poligono`) — manter consistência.
- Configuração `settings.WFS_LAYER_LOTE_CIDADAO` (já existe) e o CRS de saída: lidas pela orquestração
  que vier a consumir este serviço.

## Snippets sugeridos
```python
# services/domain/geometry/models.py  — adicionar ao pacote (reusa primitivas da 001)
from .coordinates import eh_linha, eh_multilinha, eh_poligono, eh_multipoligono


class PolygonGeometry(BaseModel):
    """GeoJSON de polígono vindo do WFS. Validação estrutural rasa da forma de `coordinates`
    (sem converter em objeto geométrico nem varrer todos os anéis/vértices). Espelha o
    `LineGeometry`: um único model cobre o tipo simples e o múltiplo."""
    type: Literal["Polygon", "MultiPolygon"]
    coordinates: list[Any]

    @model_validator(mode="after")
    def _validar_forma(self) -> "PolygonGeometry":
        valida = eh_poligono if self.type == "Polygon" else eh_multipoligono
        if not valida(self.coordinates):
            raise ValueError(f"coordinates não tem a forma de {self.type}")
        return self
```

```python
# services/domain/geometry/__init__.py  — só reexporta (§11)
from .models import GeoFeature, LineGeometry, PolygonGeometry

__all__ = ["GeoFeature", "LineGeometry", "PolygonGeometry"]
```

```python
# services/domain/lote_geocod/models.py
from pydantic import BaseModel, Field

from services.domain.geometry import GeoFeature, PolygonGeometry


class LoteGeocodInput(BaseModel):
    setor: str = Field(pattern=r"^\d{3}$")
    quadra: str = Field(pattern=r"^\d{3}$")
    lote: str = Field(pattern=r"^\d{4}$")
    tipo_lote: str
    layer_name: str  # camada de lotes, resolvida pela orquestração a partir do settings
    output_crs: int  # código EPSG de saída (ex.: 4326), injetado pela orquestração via settings


class LoteAttributes(BaseModel):
    """Atributos do lote (camada `attributes` da feature)."""
    id_poligono: str
    setor: str
    quadra: str
    lote: str
    tipo_lote: str
    tipo_quadra: str | None = None
    condominio: str | None = None


# envelope concreto: polígono + atributos do lote + CRS. Instanciável e usável como anotação.
LoteFeature = GeoFeature[PolygonGeometry, LoteAttributes]
```

```python
# services/domain/lote_geocod/geocoder.py
from collections.abc import Callable, Iterable

from services.integrations.wfs import (
    CqlFilter,
    CqlPredicate,
    WfsFeatureCollection,
    WfsFeatureRequest,
)
from services.domain.geometry import PolygonGeometry

from .models import LoteAttributes, LoteFeature, LoteGeocodInput

WfsBatches = Callable[[WfsFeatureRequest], Iterable[WfsFeatureCollection]]

PAGE_SIZE: int = 10_000
# O CRS de saída NÃO é constante de módulo: vem injetado no DTO (entrada.output_crs).

_OPCIONAIS: dict[str, str] = {
    "cd_tipo_quadra": "tipo_quadra",
    "cd_condominio": "condominio",
}


def _as_str(value: object) -> str | None:
    return None if value is None else str(value)


class LoteGeocoder:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, entrada: LoteGeocodInput) -> list[LoteFeature]:
        return self.pipeline(entrada)

    def pipeline(self, entrada: LoteGeocodInput) -> list[LoteFeature]:
        request = self._montar_request(entrada)
        lotes: list[LoteFeature] = []
        for page in self.fetcher(request):
            for feature in page.features:
                lote = self._feature_para_lote(feature, entrada.output_crs)
                if lote is not None:
                    lotes.append(lote)
        return lotes

    def _montar_request(self, entrada: LoteGeocodInput) -> WfsFeatureRequest:
        return WfsFeatureRequest(
            nome_camada=entrada.layer_name,
            cql_filter=CqlFilter(
                logic="AND",
                predicates=[
                    CqlPredicate(field="cd_setor_fiscal", op="=", value=entrada.setor),
                    CqlPredicate(field="cd_quadra_fiscal", op="=", value=entrada.quadra),
                    CqlPredicate(field="cd_lote", op="=", value=entrada.lote),
                    CqlPredicate(field="cd_tipo_lote", op="=", value=entrada.tipo_lote),
                ],
            ),
            srs_name=f"EPSG:{entrada.output_crs}",  # CRS injetado; reprojeção a cargo do WFS
            count=PAGE_SIZE,
            # sem property_names: restringir derrubaria a geometria no GeoServer
        )

    def _feature_para_lote(self, feature: object, output_crs: int) -> LoteFeature | None:
        props = feature.properties
        id_poligono = _as_str(props.get("cd_identificador"))
        setor = _as_str(props.get("cd_setor_fiscal"))
        quadra = _as_str(props.get("cd_quadra_fiscal"))
        lote = _as_str(props.get("cd_lote"))
        tipo_lote = _as_str(props.get("cd_tipo_lote"))
        if not (feature.geometry and id_poligono and setor and quadra and lote and tipo_lote):
            return None
        return LoteFeature(
            geometry=PolygonGeometry.model_validate(feature.geometry.model_dump()),
            attributes=self._montar_attributes(props, id_poligono, setor, quadra, lote, tipo_lote),
            crs=output_crs,
        )

    def _montar_attributes(
        self,
        props: dict[str, object],
        id_poligono: str,
        setor: str,
        quadra: str,
        lote: str,
        tipo_lote: str,
    ) -> LoteAttributes:
        return LoteAttributes(
            id_poligono=id_poligono,
            setor=setor,
            quadra=quadra,
            lote=lote,
            tipo_lote=tipo_lote,
            **{campo: _as_str(props.get(origem)) for origem, campo in _OPCIONAIS.items()},
        )
```

```python
# services/domain/lote_geocod/__init__.py  — só reexporta (§11)
from .geocoder import LoteGeocoder
from .models import LoteAttributes, LoteFeature, LoteGeocodInput

__all__ = ["LoteGeocoder", "LoteAttributes", "LoteFeature", "LoteGeocodInput"]
```

## Fora de escopo
- A **view/partial HTMX** que consome o serviço (clique na sugestão de contribuinte → polígono no
  mapa), a leitura de `settings` e a construção do `WfsFetcher` (orquestração) — virão na SPEC da
  interface de busca de lote.
- O **caso do endereço fiscal exato** (pop-up ponto vs. polígono) que compõe `lote_geocod` com
  `address_geocod` — roadmap fase 1, item 4, SPEC própria.
- Os models de geometria `PointGeometry` (endereço → ponto): esta SPEC só acrescenta `PolygonGeometry`.
  As primitivas de validação já estão todas no pacote (entregues na 001).
- Persistência (GeoDjango / `GeometryField`), CRS canônico de armazenamento e export — não há gravação
  aqui; a geometria é só repassada para renderização.
- **Conversão de `coordinates` em objetos geométricos** (GEOS/GDAL) ou reprojeção manual. A validação
  do `PolygonGeometry` é só estrutural/rasa.
- **Cálculo/validação do dígito verificador** do contribuinte (segue placeholder no domínio, não
  participa do match).

## Notas de teste
- Injetar um **fake callable** que devolve `WfsFeatureCollection` prontas (sem rede), no padrão da
  geocodificacao/001.
- Casos: uma feição casando (polígono retornado e atributos traduzidos); múltiplas feições para a
  mesma numeração (todas retornadas, sem dedup); preservação de nulos nos opcionais
  (`tipo_quadra`/`condominio`); descarte de feição sem geometria; descarte de feição faltando campo
  obrigatório (`id_poligono`/`setor`/`quadra`/`lote`/`tipo_lote`).
- Verificar que o `WfsFeatureRequest` montado carrega o `CqlFilter` com os **quatro** predicados
  `=` em `AND` (setor, quadra, lote, tipo_lote) e o `srs_name` derivado do `output_crs` injetado
  (ex.: `output_crs=4326` → `srs_name == "EPSG:4326"`).
- Envelope: cada item da saída é um `GeoFeature` com `geometry` (`PolygonGeometry`), `attributes`
  (`LoteAttributes`) e `crs` igual ao `output_crs`. Confirmar que
  `GeoFeature[PolygonGeometry, LoteAttributes]` é instanciável e rejeita geometria de forma inválida.
- `PolygonGeometry`: aceita `Polygon` (lista de anéis fechados) e `MultiPolygon` (lista de polígonos);
  rejeita anel aberto / profundidade de aninhamento errada (via `eh_poligono`/`eh_multipoligono`);
  rejeita `type` inválido (não-polígono). Confirmar que reusa as primitivas da 001 sem reescrevê-las.
- Validação de input: `setor`/`quadra` exigem 3 dígitos, `lote` 4 dígitos (entrada incompleta é
  rejeitada — é match exato, não prefixo).

## Patches

_Nenhum patch registrado até o momento._
