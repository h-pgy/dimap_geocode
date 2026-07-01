---
spec: mapa/002
versao: v1
atualizado_em: 2026-06-29
implementado: false
changelog:
  - v1: versão inicial
---

# SPEC mapa/002 — Plotagem de lote (nº de contribuinte → polígono no Leaflet)

- [X] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como visitante da aplicação, quero que, ao escolher um lote nas sugestões da busca por número de
contribuinte, o **polígono** do lote apareça desenhado no mapa Leaflet sobre o WMS do GeoSampa — com
popup e rótulo —, para que eu veja o imóvel no mapa sem precisar de login.

## Critérios de aceite
- [ ] Existe um app **`lote_geocoder`** (novo, **distinto** do `lote_matcher`) cuja view **orquestra** a
      plotagem do lote, **espelhando** o `logradouro_geocoder` da SPEC mapa/001 (§10.1): recebe a
      numeração escolhida (POST: `setor`, `quadra`, `lote`, `tipo_lote`), lê `settings` (conexão WFS +
      `WFS_LAYER_LOTE_CIDADAO` + `MAP_OUTPUT_CRS` + cor do polígono), **constrói o `WfsFetcher`**, monta o
      DTO `LoteGeocodInput` e chama o domínio `services/domain/lote_geocod` por composição. **Nenhuma**
      regra de negócio na view (§3, §6).
- [ ] A view converte a saída do domínio (`list[LoteFeature]`) em GeoJSON usando o **mesmo serializador**
      `to_geojson_feature_collection` do pacote `services/domain/geometry/` (entregue na mapa/001) — sem
      reescrevê-lo. **Renderiza o `popup_html` por *feature*** (template do próprio app, a partir dos
      `attributes` do lote) e o `rotulo`, escolhe a **cor de polígono** (de `settings`) e delega ao
      `mapping` a renderização do partial, **reusando integralmente** o `mapping` e o JS centralizado da
      mapa/001 (que já estiliza polígono via `style`/`fillColor`).
- [ ] A **sugestão de lote** (item da lista do `lote_matcher`) passa a **acionar o geocoder**: o
      `hx-post` do item aponta para a view do `lote_geocoder` (alvo `#resultado-busca`), substituindo o
      *stub* de seleção atual. O resultado renderizado é o mapa com o polígono.
- [ ] A numeração chega **zero-padded** (mesma normalização da busca): `setor`/`quadra` `^\d{3}$`,
      `lote` `^\d{4}$`, e `tipo_lote` presente — validados pelo `LoteGeocodInput` (geocodificacao/002).
- [ ] Visitante **anônimo** vê o mapa normalmente (busca avulsa pública — §1/§9); sem login nesta SPEC.
- [ ] Tipagem estrita compatível com `mypy`; sem `from __future__`. Convenções de §10/§11 respeitadas.

## Contexto e decisões de arquitetura
Gêmea da mapa/001, do lado do **lote → polígono**. Quase tudo já está pronto: o domínio
(`services/domain/lote_geocod`, geocodificacao/002) e **toda a infra de mapa** (app `mapping`, JS
centralizado modular, serializador `to_geojson_feature_collection`) foram entregues na mapa/001
justamente para serem **reusados aqui sem alteração**. Esta SPEC só acrescenta a **ponta de orquestração**
específica do lote: o app `lote_geocoder`.

**Por que um app separado do `lote_matcher`.** Mesma razão do par logradouro: *sugerir por prefixo*
(`lote_matcher` + `contribuinte_match`) e *geocodificar/plotar o lote escolhido* (`lote_geocoder` +
`lote_geocod`) são responsabilidades distintas e domínios separados (§10.1). O `lote_matcher` continua
dono das sugestões; o `lote_geocoder` nasce só para a view que compõe o domínio de geocodificação de lote
e entrega o polígono ao `mapping`.

**Reuso total da infra (§14 — composição sobre reimplementação).** O `mapping` é agnóstico de domínio
(recebe GeoJSON 4326 + cor) e o JS já trata polígono (`style` com `fillColor`/`fillOpacity`,
`onEachFeature`, `fitBounds`). Logo, nada de mapa precisa mudar: o `lote_geocoder` só muda **a cor**
(polígono) e **o conteúdo do popup** (atributos do lote). O serializador é o mesmo — ele é agnóstico ao
tipo de geometria por construção (mapa/001).

**Fluxo ponta a ponta.**
```
clique na sugestão (lote_matcher) ──hx-post──▶ lote_geocoder.geocodificar (view)
   • lê settings (WFS + WFS_LAYER_LOTE_CIDADAO + MAP_OUTPUT_CRS + cor polígono) e monta WfsFetcher
   • LoteGeocodInput(setor, quadra, lote, tipo_lote, layer_name, output_crs=4326)
   • LoteGeocoder(fetcher)(input) → list[LoteFeature]                       (domínio)
   • serializa → GeoJSON FeatureCollection (mesmo serializador), popup_html/rotulo por feature
   • escolhe cor de polígono; chama o helper do mapping
   ▼
mapping._mapa (partial reusado) ──swap──▶ #resultado-busca
   ▼
htmx.onLoad (JS centralizado reusado): #map → base WMS → camada GeoJSON (polígono) → fitBounds
```

## Peças de referência a compor
- `@services/domain/lote_geocod` → `LoteGeocoder`, `LoteGeocodInput`, `LoteFeature`/`LoteAttributes`: a
  geocodificação (contribuinte → polígono) **já pronta** (geocodificacao/002); compor, não reescrever.
- **SPEC mapa/001 (entregue)** → app `mapping` (`apps/mapping/context.py`, `templates/mapping/_mapa.html`),
  JS centralizado (`static/src/js/mapa/*`) e o serializador `to_geojson_feature_collection` em
  `services/domain/geometry/`: **reusados integralmente**, sem alteração.
- `@services/integrations/wfs` → `WfsFetcher`/`WfsConnectionConfig`/`WfsRetryPolicy`: montar o fetcher
  como o `logradouro_geocoder` já faz (mesmo padrão dos *management commands*).
- `templates/lote_matcher/partials/resultados_contribuinte.html` → o item de sugestão cujo `hx-post` passa
  a apontar para o `lote_geocoder` (alvo `#resultado-busca`), levando `setor`/`quadra`/`lote`/`tipo_lote`.
- `settings.WFS_LAYER_LOTE_CIDADAO` (já existe), `settings.MAP_OUTPUT_CRS` e `settings.MAP_COR_POLIGONO`
  (criados na mapa/001).

## Snippets sugeridos

```python
# apps/lote_geocoder/views.py — espelha o logradouro_geocoder (só muda domínio, cor e popup)
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.mapping.context import contexto_mapa
from services.domain.geometry import GeoFeature, to_geojson_feature_collection
from services.domain.lote_geocod import LoteGeocoder, LoteGeocodInput
from services.integrations.wfs import WfsConnectionConfig, WfsFetcher, WfsRetryPolicy

MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
WFS_LAYER_LOTE_CIDADAO: str = settings.WFS_LAYER_LOTE_CIDADAO
MAP_COR_POLIGONO: str = settings.MAP_COR_POLIGONO


def _fetcher() -> WfsFetcher:
    config = WfsConnectionConfig(
        domain=settings.WFS_DOMAIN, endpoint=settings.WFS_ENDPOINT,
        namespace=settings.WFS_NAMESPACE, service=settings.WFS_SERVICE, version=settings.WFS_VERSION,
    )
    retry = WfsRetryPolicy(
        request_timeout_seconds=settings.WFS_REQUEST_TIMEOUT_SECONDS,
        max_retries=settings.WFS_MAX_RETRIES,
        retry_wait_min_seconds=settings.WFS_RETRY_WAIT_MIN_SECONDS,
        retry_wait_max_seconds=settings.WFS_RETRY_WAIT_MAX_SECONDS,
    )
    return WfsFetcher(config, retry_policy=retry)


def _properties(f: GeoFeature[Any, Any]) -> dict[str, Any]:
    return {
        "popup_html": render_to_string(
            "lote_geocoder/partials/_popup_lote.html", {"a": f.attributes}
        ),
        "rotulo": f"{f.attributes.setor}.{f.attributes.quadra}.{f.attributes.lote}",
    }


@require_POST
def geocodificar(request: HttpRequest) -> HttpResponse:
    entrada = LoteGeocodInput(
        setor=request.POST.get("setor", ""),
        quadra=request.POST.get("quadra", ""),
        lote=request.POST.get("lote", ""),
        tipo_lote=request.POST.get("tipo_lote", ""),
        layer_name=WFS_LAYER_LOTE_CIDADAO,
        output_crs=MAP_OUTPUT_CRS,
    )
    features = LoteGeocoder(_fetcher())(entrada)
    geojson = to_geojson_feature_collection(features, _properties)
    return render(request, "mapping/_mapa.html", contexto_mapa(geojson, MAP_COR_POLIGONO))
```

```html
{# templates/lote_geocoder/partials/_popup_lote.html — popup por feature (apresentação) #}
<b>{{ a.setor }}.{{ a.quadra }}.{{ a.lote }}</b><br>
tipo {{ a.tipo_lote }}{% if a.condominio %} · cond. {{ a.condominio }}{% endif %}
```

```html
{# alteração no item de sugestão do lote_matcher: hx-post passa a acionar o geocoder #}
<li hx-post="{% url 'lote_geocoder:geocodificar' %}"
    hx-vals='{"setor": "{{ r.setor }}", "quadra": "{{ r.quadra }}", "lote": "{{ r.lote }}", "tipo_lote": "{{ r.tipo_lote }}"}'
    hx-target="#resultado-busca" hx-swap="innerHTML">…</li>
```

## Fora de escopo
- Toda a **infra de mapa** (app `mapping`, JS centralizado, serializador, constantes `MAP_*`/`WMS_*`): já
  entregue na **mapa/001**; esta SPEC só a consome.
- **Endereço → ponto** e o **pop-up endereço fiscal exato** (ponto vs. polígono, que compõe `lote_geocod`
  com `address_geocod`): SPECs futuras.
- **Captura de eventos do mapa**, **salvar no projeto/autenticação/layers**, **persistência/export** e
  **cálculo do dígito verificador** — fora desta iteração (idem mapa/001 e geocodificacao/002).

## Notas de teste
- **View `geocodificar`** (lote): injetar `WfsFetcher`/geocoder fake (sem rede) e verificar que o DTO
  carrega `output_crs = MAP_OUTPUT_CRS`, `layer_name = WFS_LAYER_LOTE_CIDADAO` e a numeração validada
  (3/3/4 dígitos); que `mapping/_mapa.html` é renderizado com a **cor de polígono**; e que cada
  `properties` traz `popup_html` (atributos do lote) e `rotulo`. Numeração incompleta/sem `tipo_lote` →
  rejeitada pela validação do `LoteGeocodInput`.
- **Reuso**: confirmar que nenhuma alteração foi necessária no `mapping`, no JS ou no serializador — só o
  novo app e o popup do lote. O serializador produz a FeatureCollection com `PolygonGeometry` igual ao
  caso de linha.
- **Smoke manual**: digitar um nº de contribuinte, clicar na sugestão, ver o **polígono** preenchido
  sobre o WMS, com popup no clique e tooltip no hover; reenviar outra sugestão e confirmar o re-monte do
  mapa no swap.

## Patches

_Nenhum patch registrado até o momento._
