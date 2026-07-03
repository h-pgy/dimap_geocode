---
spec: mapa/003
versao: v1
atualizado_em: 2026-07-02
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC mapa/003 — Plotagem de endereço (codlog + número → ponto no Leaflet)

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como visitante da aplicação, quero que, ao escolher um endereço nas sugestões da busca (logradouro +
número), o **ponto** geocodificado do imóvel apareça desenhado no mapa Leaflet sobre o WMS do
GeoSampa — com popup e rótulo —, para que eu veja onde aquele endereço cai sem precisar de login; e,
quando o endereço **não puder ser geocodificado**, quero um **aviso claro do motivo** em vez de um
mapa em branco.

## Critérios de aceite
- [ ] A view **`address_geocoder:selecionar`** deixa de ser *stub* e passa a **orquestrar** a
      geocodificação do endereço, **espelhando** o `logradouro_geocoder`/`lote_geocoder` das SPECs
      mapa/001–002 (§10.1): recebe a seleção (POST: `codlog`, `numero`), lê `settings` (conexão WFS +
      `WFS_LAYER_LOGRADOUROS` + `MAP_INTERPOLATION_CRS` + `MAP_OUTPUT_CRS` + cor do ponto), **constrói o
      `WfsFetcher`**, compõe o `AddressGeocoder` e chama o domínio `services/domain/address_geocod`.
      **Nenhuma** regra de negócio na view (§3, §6).
- [ ] O `AddressGeocoder` é composto **por injeção do `LogradouroGeocoder`** (que recebe o `WfsFetcher`)
      — `AddressGeocoder(LogradouroGeocoder(build_fetcher(settings)))` —, exatamente como a
      geocodificacao/003 prevê; a view apenas monta essa composição e passa o DTO.
- [ ] A view monta o DTO `AddressGeocodInput` com **os dois CRS resolvidos por `settings`**:
      `interpolation_crs = MAP_INTERPOLATION_CRS` (projetado/métrico, ex.: 31983) e
      `output_crs = MAP_OUTPUT_CRS` (4326). O domínio interpola em métrico e devolve o ponto já em 4326
      (§7.3) — a view **não** reprojeta.
- [ ] Como o `AddressGeocoder` devolve **uma única `EnderecoFeature`** (não uma lista), a view a envolve
      numa sequência de um elemento e usa o **mesmo serializador** `to_geojson_feature_collection` do
      pacote `services/domain/geometry/` (entregue na mapa/001) — sem reescrevê-lo; ele já é agnóstico ao
      tipo e produz `Point` na `FeatureCollection` igual a linha/polígono.
- [ ] O `EnderecoAttributes` ganha um **atributo calculado `nome_completo`** — a junção
      `tipo_logradouro` + `titulo` (se houver) + `nome_logradouro` (ex.: `AV DR PAULISTA`, `R DIREITA`).
      É **representação do logradouro** (deriva de campos já existentes, sem HTML), então mora no DTO de
      domínio como `@property`, reusável por qualquer apresentação — não é remontado no template.
- [ ] A view **renderiza o `popup_html` por *feature*** (template do próprio app): o **cabeçalho** é o
      `nome_completo` + número (o nome do logradouro por extenso), e o **`codlog` fica na linha de baixo**;
      o `rotulo` (tooltip) também usa o `nome_completo`. Escolhe a **cor de ponto** (`MAP_COR_PONTO`, de
      `settings`) e delega ao `mapping` a renderização do partial, **reusando integralmente** o `mapping`
      e o JS centralizado da mapa/001 (que já plota ponto via `pointToLayer`/`circleMarker` e faz
      `fitBounds`).
- [ ] **Erros tipados viram avisos semânticos (um por erro).** A geocodificação pode levantar dois erros
      de domínio, e cada um gera uma **mensagem distinta e específica** no partial de aviso agnóstico do
      `mapping` (`templates/mapping/_aviso.html` + `contexto_aviso`, entregues na mapa/001 patch 004),
      trocado no **mesmo alvo** `#resultado-busca`:
      - `SegmentoNaoEncontradoError` (não há segmentos para o `codlog`) → aviso de que **não foi possível
        localizar o logradouro** para geocodificar o endereço;
      - `NumeracaoNaoEncontradoError`/`NumeracaoNaoEncontradaError` (há segmentos, mas nenhum cuja faixa
        contém o número) → aviso de que o **número está fora da numeração cadastrada** do logradouro.
      A decisão "geocodificou ou não" é **orquestração** (§3): fica na view (try/except das exceções de
      domínio), **não** no domínio nem no serializador, que seguem intactos.
- [ ] O item de sugestão de endereço **já aponta** para `address_geocoder:selecionar` (POST com
      `codlog` + `numero`) — os partials `resultados_endereco_nome.html`/`resultados_endereco_codlog.html`
      **não mudam**; só o corpo da view e o partial de resposta deixam de ser o *stub* de confirmação.
- [ ] Visitante **anônimo** vê o mapa normalmente (busca avulsa pública — §1/§9); sem login nesta SPEC.
- [ ] Tipagem estrita compatível com `mypy`; sem `from __future__`. Convenções de §10/§11 respeitadas.

## Contexto e decisões de arquitetura
Terceira SPEC do épico **`mapa`**, fechando o trio de geometrias no Leaflet: **endereço → ponto**, ao
lado de logradouro→linha (mapa/001) e lote→polígono (mapa/002). É a **ponta de interface/orquestração**
que a geocodificacao/003 **explicitamente deixou fora de escopo**: "a view/partial HTMX que consome o
serviço, a leitura de `settings` (camada + CRS), a construção do `LogradouroGeocoder`/`WfsFetcher` e a
**captura das exceções** para renderizar aviso — orquestração, virá em SPEC de interface". Esta é essa
SPEC. Toda a lógica de geocodificação (interpolação, paridade, orientação, reprojeção) **já existe** em
`services/domain/address_geocod` — aqui é só **composta**, não reescrita.

**Reuso total da infra de mapa (§14 — composição sobre reimplementação).** O `mapping` é agnóstico de
domínio (recebe GeoJSON 4326 + cor) e o JS centralizado **já trata ponto**: o `camada_resultado.js` da
mapa/001 tem `pointToLayer: (f, latlng) => L.circleMarker(...)` e o `fitBounds` já cobre o caso de uma
única geometria (com fallback `setView` no centro). Logo, **nada de mapa/JS muda**: o `address_geocoder`
só escolhe **a cor** (`MAP_COR_PONTO`) e **o conteúdo do popup** (atributos do endereço). O serializador
`to_geojson_feature_collection` é o mesmo — agnóstico ao tipo por construção.

**Por que a orquestração fica no `address_geocoder` (e não num app novo).** Nos pares logradouro e lote,
o *matching* (sugestões) e a *geocodificação/plotagem* moram em apps distintos (`_matcher` × `_geocoder`).
No endereço, a orquestração de seleção **já vive** no app `address_geocoder` (a view `selecionar`, para a
qual as sugestões já fazem `hx-post`). Esta SPEC **compõe o que existe** em vez de inventar um app novo:
apenas troca o corpo do *stub* `selecionar` pela orquestração real (ler settings → compor domínio →
mapa/aviso). O item de sugestão continua apontando para a mesma URL — a fiação HTMX não muda.

**Uma feature, não uma lista.** Diferente de logradouro/lote (que devolvem `list[...]` e sinalizam
ausência com **lista vazia**), o `AddressGeocoder` devolve **uma** `EnderecoFeature` e sinaliza ausência
com **exceções tipadas**. Por isso o tratamento de "não deu para plotar" aqui **não** é o `if not
features` da mapa/001/002 (patch 004/002): é um **try/except** das duas exceções de domínio, cada uma
mapeada para uma mensagem própria. O serializador recebe `[feature]` (sequência de um elemento) e produz
a `FeatureCollection` de um `Point`.

**Dois CRS, resolvidos pela orquestração (§7.3).** O `AddressGeocodInput` pede **dois** CRS: o de
**interpolação** (projetado/métrico, para a proporção do número ser em metros) e o de **saída** (4326,
pronto pro Leaflet). Ambos são constantes de `settings` lidas **pela view** e injetadas via DTO — o
domínio nunca lê `settings` nem fixa CRS. O `MAP_OUTPUT_CRS` (4326) já existe; falta acrescentar o
`MAP_INTERPOLATION_CRS` (ex.: 31983, SIRGAS 2000 / UTM 23S — nativo do GeoSampa), ajuste de configuração
que a geocodificacao/003 deixou para esta iteração de interface.

**Avisos reusam o `mapping`, sem UI nova.** O partial de aviso agnóstico (`templates/mapping/_aviso.html`)
e o helper `contexto_aviso(mensagem)` já foram entregues na mapa/001 (patch 004) e reusados na mapa/002
(patch 002). Aqui eles são reusados **de novo**: nenhum partial de aviso é criado. A única diferença é
que agora há **dois** motivos possíveis (uma mensagem por exceção), montados como *presentation* na view;
o `mapping` só exibe a string. Ambos os desfechos (mapa ou aviso) trocam o mesmo `#resultado-busca`, então
o *swap* do HTMX não muda.

**Fluxo ponta a ponta.**
```
clique na sugestão de endereço (address_geocoder) ──hx-post──▶ address_geocoder.selecionar (view)
   • lê settings (WFS + WFS_LAYER_LOGRADOUROS + MAP_INTERPOLATION_CRS + MAP_OUTPUT_CRS + cor ponto)
   • compõe AddressGeocoder(LogradouroGeocoder(build_fetcher(settings)))
   • AddressGeocodInput(codlog, numero, layer_name, interpolation_crs=31983, output_crs=4326)
   • AddressGeocoder(...)(input) → EnderecoFeature                                  (domínio)
        ├─ SegmentoNaoEncontradoError  → mapping/_aviso.html (msg: logradouro não localizado)
        └─ NumeracaoNaoEncontradaError → mapping/_aviso.html (msg: número fora da numeração)
   • serializa [feature] → GeoJSON FeatureCollection (mesmo serializador), popup_html/rotulo
   • escolhe cor de ponto; chama o helper do mapping
   ▼
mapping/_mapa.html (partial reusado) ──swap──▶ #resultado-busca
   ▼
htmx.onLoad (JS centralizado reusado): #map → base WMS → camada GeoJSON (ponto/circleMarker) → fitBounds
```

## Peças de referência a compor
- `@services/domain/address_geocod` → `AddressGeocoder`, `AddressGeocodInput`, `EnderecoFeature`,
  `SegmentoNaoEncontradoError`, `NumeracaoNaoEncontradaError` (todos já reexportados no `__init__.py`): a
  geocodificação (codlog + número → ponto) **já pronta** (geocodificacao/003); compor, não reescrever.
- `@services/domain/logradouro_geocod` → `LogradouroGeocoder`: injetado no `AddressGeocoder` (é ele quem
  busca os segmentos no WFS). Mesma composição da geocodificacao/003.
- **SPEC mapa/001 (entregue)** → app `mapping` (`apps/mapping/context.py` com `contexto_mapa` e
  `contexto_aviso`; `templates/mapping/_mapa.html` e `_aviso.html`), JS centralizado
  (`static/src/js/mapa/*`, que já plota ponto via `pointToLayer`/`circleMarker`) e o serializador
  `to_geojson_feature_collection` em `services/domain/geometry/`: **reusados integralmente**, sem alteração.
- `@services/integrations/wfs` → `build_fetcher`: montar o fetcher com o `settings` do Django injetado
  (Protocol `WfsSettingsLike`), como `logradouro_geocoder`/`lote_geocoder` já fazem.
- `apps/address_geocoder/views.py` → a view `selecionar` (hoje *stub* que só imprime no stdout) e o schema
  `EnderecoSelection`: é o ponto exato que esta SPEC transforma em orquestração real.
- `templates/address_geocoder/partials/resultados_endereco_nome.html` e `resultados_endereco_codlog.html`
  → os itens de sugestão que **já** fazem `hx-post` para `address_geocoder:selecionar` levando `codlog` e
  `numero` (alvo `#resultado-busca`): **não mudam**.
- `settings.WFS_LAYER_LOGRADOUROS` e `settings.MAP_OUTPUT_CRS` (já existem); **novas** constantes de
  `settings`: `MAP_INTERPOLATION_CRS` (projetado, ex.: 31983) e `MAP_COR_PONTO` (cor default do ponto).

## Snippets sugeridos

```python
# services/domain/address_geocod/models.py — atributo calculado do nome completo do logradouro.
# Deriva de campos já existentes (sem HTML) → é representação de domínio, mora no DTO como @property.
class EnderecoAttributes(BaseModel):
    codlog: str
    nome_logradouro: str
    tipo_logradouro: str            # sigla do tipo (R, AV, PC, …), vinda do GeoSampa
    numero: int
    id_segmento: str
    titulo: str | None = None

    @property
    def nome_completo(self) -> str:
        """tipo + título (se houver) + nome — ex.: 'AV DR PAULISTA', 'R DIREITA'."""
        partes = [self.tipo_logradouro, self.titulo, self.nome_logradouro]
        return " ".join(p for p in partes if p)
```

```python
# config/settings.py — novas constantes (lidas pela orquestração; nada disso vai pro JS hardcoded)

# no bloco _Settings, junto de map_cor_linha/map_cor_poligono (mesmo padrão de Field/alias):
class _Settings(BaseSettings):
    ...
    map_cor_ponto: str = Field(default="#ef4444", alias="MAP_COR_PONTO")

# depois, reextraído para constante UPPER_CASE local (§10.3), junto das demais MAP_*:
MAP_INTERPOLATION_CRS = 31983            # CRS projetado/métrico p/ interpolar o número (§7.3)
MAP_COR_PONTO = _env.map_cor_ponto       # cor default do ponto de endereço geocodificado
```

```python
# apps/address_geocoder/views.py — a view `selecionar` deixa de ser stub e passa a orquestrar.
# (mantém as views de sugestão secao_endereco/secao_endereco_codlog como estão)
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.mapping.context import contexto_aviso, contexto_mapa
from services.domain.address_geocod import (
    AddressGeocodInput,
    AddressGeocoder,
    EnderecoFeature,
    NumeracaoNaoEncontradaError,
    SegmentoNaoEncontradoError,
)
from services.domain.geometry import to_geojson_feature_collection
from services.domain.logradouro_geocod import LogradouroGeocoder
from services.integrations.wfs import build_fetcher

MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
MAP_INTERPOLATION_CRS: int = settings.MAP_INTERPOLATION_CRS
WFS_LAYER_LOGRADOUROS: str = settings.WFS_LAYER_LOGRADOUROS
MAP_COR_PONTO: str = settings.MAP_COR_PONTO

MSG_SEM_SEGMENTO = "Não foi possível localizar o logradouro para geocodificar este endereço."
MSG_SEM_NUMERACAO = "O número informado está fora da faixa de numeração cadastrada para este logradouro."


def _properties(f: EnderecoFeature) -> dict[str, Any]:
    a = f.attributes
    return {
        "popup_html": render_to_string(
            "address_geocoder/partials/_popup_endereco.html", {"a": a}
        ),
        "rotulo": f"{a.nome_completo}, {a.numero}",
    }


@require_POST
def selecionar(request: HttpRequest) -> HttpResponse:
    entrada = AddressGeocodInput(
        codlog=request.POST.get("codlog", ""),
        numero=request.POST.get("numero", ""),   # Pydantic coage "123" → 123 (Field(gt=0))
        layer_name=WFS_LAYER_LOGRADOUROS,
        interpolation_crs=MAP_INTERPOLATION_CRS,
        output_crs=MAP_OUTPUT_CRS,
    )
    geocoder = AddressGeocoder(LogradouroGeocoder(build_fetcher(settings)))
    try:
        feature = geocoder(entrada)
    except SegmentoNaoEncontradoError:
        return render(request, "mapping/_aviso.html", contexto_aviso(MSG_SEM_SEGMENTO))
    except NumeracaoNaoEncontradaError:
        return render(request, "mapping/_aviso.html", contexto_aviso(MSG_SEM_NUMERACAO))
    geojson = to_geojson_feature_collection([feature], _properties)
    return render(request, "mapping/_mapa.html", contexto_mapa(geojson, MAP_COR_PONTO))
```

```html
{# templates/address_geocoder/partials/_popup_endereco.html — popup por feature (apresentação) #}
<b>{{ a.nome_completo }}, {{ a.numero }}</b><br>
codlog {{ a.codlog }}
```

## Fora de escopo
- Toda a **infra de mapa** (app `mapping`, JS centralizado, serializador, partial/helper de aviso,
  constantes `MAP_*`/`WMS_*` de mapa): já entregue nas **mapa/001–002**; esta SPEC só a consome. Nenhuma
  alteração no `mapping`, no JS ou no serializador.
- Toda a **lógica de geocodificação** (interpolação, paridade, orientação, reprojeção): já entregue na
  **geocodificacao/003**; aqui é composta, não reescrita.
- O **caso especial do endereço fiscal exato** (pop-up ponto × polígono, item 4 do roadmap) — outra
  iteração; aqui só existe o caminho "endereço solto → interpolação → ponto".
- **Match fuzzy / roteamento / parsing do número**: o `codlog` e o `numero` chegam já resolvidos das
  sugestões (`address_match`/`roteamento_busca`); esta SPEC não toca no matching nem no parsing.
- **Captura de eventos do mapa**, **salvar no projeto/autenticação/layers**, **persistência/export** —
  fora desta iteração (idem mapa/001–002 e geocodificacao/003).

## Notas de teste
- **View `selecionar`** (endereço, caminho feliz): injetar um `AddressGeocoder` fake (sem rede) que
  devolve uma `EnderecoFeature` de ponto e verificar que o DTO carrega `interpolation_crs =
  MAP_INTERPOLATION_CRS`, `output_crs = MAP_OUTPUT_CRS`, `layer_name = WFS_LAYER_LOGRADOUROS`; que
  `mapping/_mapa.html` é renderizado com a **cor de ponto**; e que `properties` traz `popup_html` (com
  logradouro/número/codlog) e `rotulo`.
- **View `selecionar`** (erros): forçar o geocoder a levantar `SegmentoNaoEncontradoError` e depois
  `NumeracaoNaoEncontradaError` e confirmar que cada um renderiza `mapping/_aviso.html` com a **mensagem
  específica** correspondente (uma por erro) — e que o mapa **não** é renderizado nesses casos.
- **Serializador com ponto**: `to_geojson_feature_collection([feature], props)` produz uma
  `FeatureCollection` de um `Feature` cuja `geometry` é o `Point` (`model_dump()`), confirmando que o
  serializador é agnóstico ao tipo (igual a linha/polígono).
- **Reuso**: confirmar que nenhuma alteração foi necessária no `mapping`, no JS centralizado, no
  serializador ou nos partials de sugestão de endereço — só o corpo da view `selecionar` e o popup novo.
- **Smoke manual**: digitar um endereço (logradouro + número), clicar na sugestão, ver o **ponto**
  (circleMarker) sobre o WMS com popup no clique e tooltip no hover; testar um número fora de faixa e um
  codlog sem segmentos e ver **os avisos semânticos** correspondentes; reenviar outra sugestão e confirmar
  o re-monte do mapa no swap (`htmx.onLoad` redetecta o novo `#map`).

## Patches

_Nenhum patch registrado até o momento._
