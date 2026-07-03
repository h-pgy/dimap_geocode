---
spec: roteamento_busca/012
versao: v1
atualizado_em: 2026-07-03
implementado: true
changelog:
  - v1: versão inicial
---

# SPEC roteamento_busca/012 — Filtro de condomínio no geocodificador de lote

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como usuário que clicou numa sugestão de lote condominial (ex.: `001.002.0000-03`), quero que o
mapa exiba **apenas o polígono do condomínio que escolhi**, para não ver todos os condomínios da
mesma quadra plotados de uma vez (comportamento anterior, que buscava por `cd_lote=0000` sem
filtrar `cd_condominio`).

## Critérios de aceite

- [x] O DTO `LoteGeocodInput` aceita um novo campo **`cod_condominio: str | None`** com default
      `None`, para manter retrocompatibilidade com fluxos que não envolvem condomínio.
- [x] Quando `cod_condominio` é fornecido, o `LoteGeocoder` inclui o predicado
      `CqlPredicate(field="cd_condominio", op="=", value=<cod>)` na request WFS, filtrando o
      resultado ao condomínio específico.
- [x] Quando `cod_condominio` é `None`, o request WFS permanece idêntico ao anterior (4
      predicados: setor, quadra, lote, tipo_lote) — sem regressão.
- [x] A view `geocodificar` extrai `cd_condominio` do POST (propagado pelos templates de
      sugestão via `hx-vals` na SPEC 011) e passa para `LoteGeocodInput`. Valores `"None"` e
      string vazia são convertidos para `None`.
- [x] O model `LoteAttributes` expõe um **`computed_field` `is_condominio: bool`**, derivado de
      `condominio is not None and condominio != "00"` — a booleana vem do retorno direto do WFS,
      diferente da SPEC 011 onde era materializada no catalog.
- [x] O popup do mapa (`_popup_lote.html`) exibe **"condomínio XX"** em destaque visual (azul,
      negrito) quando `is_condominio` é verdadeiro, diferenciando visualmente lotes condominiais
      dos demais.

## Contexto e decisões de arquitetura

Esta SPEC é a continuação direta da SPEC 011, que preparou a propagação de `cd_condominio` e
`is_condominio` nos templates de sugestão via `hx-vals`. A SPEC 011 explicitamente deixou como
**fora de escopo** o consumo desses valores pelo geocodificador — esta SPEC fecha esse ciclo.

As alterações tocam **três camadas**:

1. **Domínio (`services/domain/lote_geocod/`):**
   - `LoteGeocodInput` ganha `cod_condominio: str | None = None`.
   - `LoteGeocoder._montar_request` condiciona o 5º predicado CQL ao campo estar presente.
   - `LoteAttributes` ganha `is_condominio` como `computed_field` (não coluna materializada,
     porque aqui os dados vêm direto do WFS, não de um DataFrame cacheado).

2. **Interface (view + template):**
   - A view `geocodificar` extrai e sanitiza `cd_condominio` do POST.
   - O popup `_popup_lote.html` usa `is_condominio` para badge visual.

3. **Persistência:** nenhuma alteração.

### Por que `computed_field` e não coluna materializada?

Na SPEC 011, `is_condominio` foi materializada como coluna booleana no DataFrame do
`ContribuinteCatalog` — lá faz sentido porque o filtro vetorizado em pandas é vantajoso e o
dado vive num cache. No `LoteAttributes`, o dado vem do retorno WFS (um punhado de features
por request), então um `computed_field` do Pydantic é suficiente e mais simples.

### Fluxo dos dados

```
Template sugestão (hx-vals: cd_condominio, is_condominio)
  → POST para geocodificar
    → view extrai cd_condominio do POST, sanitiza "None"/vazio → None
      → LoteGeocodInput(cod_condominio=...)
        → LoteGeocoder._montar_request: se cod_condominio, 5º CqlPredicate
          → WFS retorna apenas o condomínio filtrado
            → LoteAttributes.is_condominio (computed_field)
              → _popup_lote.html exibe badge "condomínio XX"
```

## Peças de referência a compor

- `services/domain/lote_geocod/models.py` → `LoteGeocodInput` e `LoteAttributes`: estender
  com os novos campos.
- `services/domain/lote_geocod/geocoder.py` → `LoteGeocoder._montar_request`: compor o
  predicado condicional usando `CqlPredicate` já existente.
- `apps/lote_geocoder/views.py` → `geocodificar`: extrair e sanitizar `cd_condominio` do POST.
- `templates/lote_geocoder/partials/_popup_lote.html`: atualizar com badge condicional.
- SPEC 011 (`011-info-condominio-sugestoes.md`): os templates `resultados_contribuinte.html` e
  `resultados_endereco_lote.html` já propagam `cd_condominio` no `hx-vals` — usar sem alterar.

## Snippets sugeridos

### LoteGeocodInput — novo campo opcional

```python
class LoteGeocodInput(BaseModel):
    # ... campos existentes ...
    cod_condominio: str | None = None
```

### LoteGeocoder._montar_request — predicado condicional

```python
def _montar_request(self, entrada: LoteGeocodInput) -> WfsFeatureRequest:
    predicates = [
        CqlPredicate(field="cd_setor_fiscal", op="=", value=entrada.setor),
        CqlPredicate(field="cd_quadra_fiscal", op="=", value=entrada.quadra),
        CqlPredicate(field="cd_lote", op="=", value=entrada.lote),
        CqlPredicate(field="cd_tipo_lote", op="=", value=entrada.tipo_lote),
    ]
    if entrada.cod_condominio is not None:
        predicates.append(
            CqlPredicate(field="cd_condominio", op="=", value=entrada.cod_condominio),
        )
    return WfsFeatureRequest(
        nome_camada=entrada.layer_name,
        cql_filter=CqlFilter(logic="AND", predicates=predicates),
        srs_name=f"EPSG:{entrada.output_crs}",
        count=PAGE_SIZE,
    )
```

### LoteAttributes — computed_field is_condominio

```python
class LoteAttributes(BaseModel):
    # ... campos existentes ...
    condominio: str | None = None

    @computed_field
    @property
    def is_condominio(self) -> bool:
        return self.condominio is not None and self.condominio != "00"
```

### View — extração e sanitização

```python
cd_cond_raw = request.POST.get("cd_condominio", "")
cod_condominio = cd_cond_raw if cd_cond_raw and cd_cond_raw != "None" else None
entrada = LoteGeocodInput(
    # ... campos existentes ...
    cod_condominio=cod_condominio,
)
```

### Popup — badge condicional

```html
tipo {{ a.tipo_lote }}{% if a.is_condominio %} · <span style="color:#3b82f6;font-weight:600">condomínio {{ a.condominio }}</span>{% elif a.condominio %} · cond. {{ a.condominio }}{% endif %}
```

## Fora de escopo

- **Cor diferenciada do polígono para condomínios** — o popup sinaliza, mas o polígono em si
  ainda usa a cor padrão. Uma SPEC futura pode mudar a cor de preenchimento/borda quando
  `is_condominio` é verdadeiro.
- **Parse de `cd_condominio` a partir da entrada digitada** — quando o usuário digita
  diretamente `001.002.0000-03`, o `ContribuinteIdentifier` poderia popular `cd_condominio`
  no `ContribuinteParse` a partir do padrão `0000-XX`. Isso fica para uma SPEC futura.
- **Testes unitários novos** — ver Notas de teste.

## Notas de teste

- **`LoteGeocodInput`**: verificar que `cod_condominio=None` (default) mantém 4 predicados no
  CQL, e que `cod_condominio="03"` gera 5 predicados com `cd_condominio='03'`.
- **`LoteAttributes.is_condominio`**: testar os três cenários — `condominio=None` (False),
  `condominio="00"` (False), `condominio="03"` (True).
- **View `geocodificar`**: smoke test com POST contendo `cd_condominio=03` e verificar que o
  `LoteGeocodInput` recebe `cod_condominio="03"`; POST com `cd_condominio=None` (string)
  deve resultar em `cod_condominio=None` (Python None).
- **Regressão**: os 32 testes existentes do geocoder devem continuar passando sem alteração
  (o campo é opcional com default `None`).

## Patches

_Nenhum patch registrado até o momento._
