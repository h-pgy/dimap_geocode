---
spec: geocodificacao/004
versao: v1
atualizado_em: 2026-07-03
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC geocodificacao/004 — Estilização condicional abstrata no mapa (Leaflet) e destaque para Lotes Condominiais

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como usuário do sistema, ao buscar por um lote que é condominial, quero que o polígono exibido no mapa tenha uma cor de preenchimento e borda ligeiramente diferente (um laranja mais intenso) dos lotes comuns (laranja padrão), para identificar imediatamente a natureza do lote visualmente.
Além disso, como arquiteto do sistema, quero que essa customização visual seja conduzida pelo backend via contrato de propriedades GeoJSON, mantendo o frontend (`camada_resultado.js`) completamente agnóstico a regras de negócio e reusável por outras partes do sistema.

## Critérios de aceite

- [ ] O modelo `GeoJsonProperties` é criado em `services/domain/geometry/models.py` herdando de `pydantic.BaseModel`, expondo os campos opcionais `popup_html`, `rotulo` e `cor`.
- [ ] A função `to_geojson_feature_collection` em `services/domain/geometry/serializers.py` tem sua assinatura de callback atualizada para aceitar um `Callable` que retorne `GeoJsonProperties`, serializando-o e chamando `model_dump(exclude_none=True)` para ignorar os atributos nulos no payload de destino.
- [ ] Os três geocoders (Lote, Endereço e Logradouro) instanciam e retornam `GeoJsonProperties` em suas respectivas funções `_properties` dentro das views.
- [ ] A função `_properties` de `apps/lote_geocoder/views.py` define `cor="#ea580c"` caso o lote seja condominial (`is_condominio` for `True`).
- [ ] O componente frontend em `static/src/js/mapa/camada_resultado.js` tem seus callbacks de estilo (`style` e `pointToLayer`) atualizados para priorizar a cor definida via `f.properties.cor` (se existir e estiver informada na feature) em detrimento da `cor` base da camada (herdada via param, vinda do DOM).

## Contexto e decisões de arquitetura

Em vez de criar lógicas com blocos condicionais (`if (is_condominio)`) diretamente no código JavaScript do Leaflet — o que violaria o isolamento de regras de negócio e criaria vazamento de domínio para o frontend — a decisão arquitetural tomada foi empurrar a definição da cor para o backend, em tempo de orquestração (views). O backend avalia se o lote se qualifica a receber um estilo diferenciado e, de maneira afirmativa, injeta a propriedade `cor` no envelope GeoJSON respectivo.

O componente JavaScript encarregado da renderização dos resultados no mapa (`camada_resultado.js`) lê passivamente a propriedade `cor` (se disponibilizada no escopo de `properties` da feature) e a prioriza para fins de colorização de borda e de preenchimento. Esta modelagem não altera o comportamento default para elementos sem definição customizada e provê uma forma limpa, simples e agnóstica para futuras estilizações visuais pontuais sem exigir quaisquer modificações no client-side.

A fim de formalizar este contrato de dados e documentá-lo ao desenvolvedor, as properties transportadas passaram a se basear no Pydantic via modelo `GeoJsonProperties`.

## Peças de referência a compor

- `services/domain/geometry/models.py`: Criação do modelo Pydantic `GeoJsonProperties`.
- `services/domain/geometry/serializers.py`: Atualização do typehint da factory de JSON (`properties`) e invocações serializadoras.
- `apps/lote_geocoder/views.py`: Atualização do retorno para o modelo `GeoJsonProperties`, avaliando `is_condominio` para atribuição de cor hexadecimal condicional.
- `apps/address_geocoder/views.py`: Atualização do retorno para o modelo `GeoJsonProperties`.
- `apps/logradouro_geocoder/views.py`: Atualização do retorno para o modelo `GeoJsonProperties`.
- `static/src/js/mapa/camada_resultado.js`: Alteração das propriedades injetadas em `color` e `fillColor` durante as factory expressions em `style` e `pointToLayer` da layer instanciada.

## Snippets sugeridos

### GeoJsonProperties (services/domain/geometry/models.py)

```python
class GeoJsonProperties(BaseModel):
    """Contrato de propriedades GeoJSON interpretadas e esperadas pelo frontend (Leaflet)."""
    popup_html: str | None = None
    rotulo: str | None = None
    cor: str | None = None
```

### to_geojson_feature_collection (services/domain/geometry/serializers.py)

```python
from collections.abc import Callable, Sequence
from typing import Any

from .models import GeoFeature, GeoJsonProperties

def to_geojson_feature_collection(
    features: Sequence[GeoFeature[Any, Any]],
    properties: Callable[[GeoFeature[Any, Any]], GeoJsonProperties],
) -> dict[str, Any]:
    """Converte features de domínio numa GeoJSON FeatureCollection 4326 (formato do Leaflet).
    Agnóstico ao tipo de geometria. Envelope é geometria (mora aqui); properties de
    apresentação (popup_html, rotulo, cor) vêm do app via `properties`."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": f.geometry.model_dump(),
                "properties": properties(f).model_dump(exclude_none=True),
            }
            for f in features
        ],
    }
```

### Callback no Lote Geocoder (apps/lote_geocoder/views.py)

```python
from services.domain.geometry.models import GeoJsonProperties

def _properties(f: GeoFeature[Any, Any]) -> GeoJsonProperties:
    # #ea580c = laranja intenso (Tailwind orange-600)
    cor_condominio = "#ea580c" if getattr(f.attributes, "is_condominio", False) else None
    
    return GeoJsonProperties(
        popup_html=render_to_string(
            "lote_geocoder/partials/_popup_lote.html", {"a": f.attributes}
        ),
        rotulo=f"{f.attributes.setor}.{f.attributes.quadra}.{f.attributes.lote}",
        cor=cor_condominio,
    )
```

### Callback no Address Geocoder (apps/address_geocoder/views.py)

```python
from services.domain.geometry.models import GeoJsonProperties

def _properties(f: EnderecoFeature) -> GeoJsonProperties:
    a = f.attributes
    return GeoJsonProperties(
        popup_html=render_to_string(
            "address_geocoder/partials/_popup_endereco.html", {"a": a}
        ),
        rotulo=f"{a.nome_completo}, {a.numero}",
        cor=None,
    )
```

### Callback no Logradouro Geocoder (apps/logradouro_geocoder/views.py)

```python
from services.domain.geometry.models import GeoJsonProperties

def _properties(f: GeoFeature[Any, Any]) -> GeoJsonProperties:
    return GeoJsonProperties(
        popup_html=render_to_string(
            "logradouro_geocoder/partials/_popup_segmento.html", {"a": f.attributes}
        ),
        rotulo=f.attributes.nome_logradouro,
        cor=None,
    )
```

### Frontend Leaflet agnóstico (static/src/js/mapa/camada_resultado.js)

```javascript
// popup_html, rotulo e cor (opcional) já vêm prontos nas properties (servidor)
export function adicionarResultado(map, geometria, corPadrao) {
  const camada = L.geoJSON(geometria, {
    style: (f) => {
      const c = (f.properties && f.properties.cor) ? f.properties.cor : corPadrao;
      return { color: c, weight: 3, opacity: 1, fillColor: c, fillOpacity: 0.3 };
    },
    pointToLayer: (f, latlng) => {
      const c = (f.properties && f.properties.cor) ? f.properties.cor : corPadrao;
      return L.circleMarker(latlng, { radius: 7, color: c, weight: 2, fillColor: c, fillOpacity: 0.85 });
    },
    onEachFeature: (f, layer) => {
      const p = f.properties || {};
      if (p.popup_html) layer.bindPopup(p.popup_html);
      if (p.rotulo) layer.bindTooltip(p.rotulo, { direction: "top", sticky: true });
    },
  }).addTo(map);
  
  const b = camada.getBounds();
  b.isValid()
    ? map.fitBounds(b, { maxZoom: 18, padding: [20, 20] })
    : map.setView(b.getCenter(), 17);
  return camada;
}
```

## Fora de escopo

- **Outras cores dinâmicas para endereços ou logradouros** — O mecanismo é flexibilizado no Leaflet e no contrato Pydantic para suportar customizações visuais de qualquer geometria, mas nesta etapa unicamente o condomínio receberá a condicional com injeção de `#ea580c`. O comportamento dos demais resultados prosseguirá baseando-se em `corPadrao`.
- **Implementação do filtro de requisições WFS** — As validações estruturais referentes ao isolamento de feature/filtragem de queries que geraram `is_condominio` já foram aplicadas na SPEC roteamento_busca/012.

## Notas de teste

- **Integração das instâncias Lote**: Confirmar, através de uso local, que a visualização de um Lote puramente originário de condomínio de fato rende o polígono de cor intensa, preservando as popups.
- **Não Regressão Lote Comum/Logradouro/Endereço**: Garantir que as lógicas das demais visualizações visuais permaneçam íntegras (laranja clássico para lote isolado, azul para ruas e ponto vermelho para endereços), verificando as invocações HTMX pós-refactor do TypeHint e do `BaseModel` retornado.
- **Testes unitários de serialização**: Criar/atualizar teste unitário para `to_geojson_feature_collection` em `tests/services/domain/geometry/test_serializers.py` garantindo que ao retornar um `GeoJsonProperties` com `cor=None`, a chave `cor` seja omitida (via `exclude_none=True`) do dicionário resultante da property.

## Patches

_Nenhum patch registrado até o momento._
