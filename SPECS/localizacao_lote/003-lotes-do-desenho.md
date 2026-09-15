---
spec: localizacao_lote/003
versao: v1
atualizado_em: 2026-09-15
testes_tdd: false
implementado: false
markers_obrigatorios: [integration]
changelog:
  - v1: versão inicial
---

# SPEC localizacao_lote/003 — Lotes que cruzam um desenho

## 1 · User story
Quem usa o mapa desenha um polígono sobre um terreno e pede os lotes cadastrados que ele cruza, no
contexto de um imóvel que ocupa mais de um lote, para ver de uma vez quais lotes compõem aquele
terreno.

## 2 · Condições de pronto
- [ ] Concluir um **polígono** na bancada de desenho (polígono, retângulo ou círculo) abre a gaveta
      lateral com a **área do desenho** e o botão **"Buscar lotes contidos no polígono"**, sem login.
- [ ] Acionar o botão desenha no mapa **todos os lotes que intersectam** o desenho e abre a
      **gaveta inferior** com a tabela deles (SQL, endereço, situação do lançamento); a gaveta lateral
      passa a mostrar a área e a **quantidade** de lotes.
- [ ] Clicar numa linha da tabela abre a **gaveta de detalhe** com os dados daquele lote, iguais aos
      da gaveta do lote da SPEC [localizacao_lote/001](001-dados-do-lote-na-gaveta.md) — um lote por
      vez.
- [ ] O desenho continua no mapa, por cima dos lotes, depois da busca.
- [ ] Desenho que se auto-intersecta é recusado **já na oferta**, com mensagem em português, e o botão
      não aparece; a busca recusa pelo mesmo critério, sem consultar o WFS.
- [ ] Desenho acima da área máxima configurada é recusado do mesmo jeito, com mensagem que cita a área
      máxima.
- [ ] Desenho que não cruza lote algum mostra o estado de falta escrito na gaveta inferior.
- [ ] Concluir um novo polígono troca a oferta da gaveta pela do desenho novo.
- [ ] O design da gaveta do desenho, da tabela na gaveta inferior e da gaveta de detalhe foi
      aprovado no mock e as peças novas portadas para o tema e o styleguide antes de qualquer
      template da aplicação usá-las.

## 3 · Domínio
O desenho é a geometria que a [bancada](../design/018-bancada-desenho.md) produz; a pergunta que esta
SPEC faz a ela é só "qual polígono foi concluído?". A consulta espacial é do submódulo
`lote_espacial`, com a [CamadaLotes](002-lote-mais-proximo-do-endereco.md#3--domínio) e a
reprojeção da SPEC 002.

**`services/domain/lote_espacial/models.py`**

```python
class Desenho(BaseModel):
    """O polígono que o usuário traçou, no CRS do mapa. Só polígono simples: a bancada não produz outro."""

    model_config = ConfigDict(frozen=True)

    geometria: PolygonGeometry
    crs: int

    @model_validator(mode="after")
    def _so_poligono_simples(self) -> Self:
        if self.geometria.type != "Polygon":
            raise ValueError("O desenho precisa ser um polígono simples.")
        return self


class LotesDoDesenho(BaseModel):
    """O que a consulta apurou: o desenho, a área dele e os lotes que ele cruza."""

    desenho: Desenho
    # Guardada: depende do CRS métrico da camada, que não mora no desenho.
    area_m2: float = Field(gt=0)
    lotes: tuple[LoteFeature, ...] = ()
```

**`services/domain/lote_geocod/models.py`** — o lote por identificador do polígono, que a gaveta de
detalhe (e a SPEC [certidao_lancamento/001](../certidao_lancamento/001-certidao-de-um-lote.md))
consulta.

```python
class LotePorIdentificadorInput(BaseModel):
    id_poligono: str = Field(pattern=r"^\d+$")
    layer_name: str
    output_crs: int
```

## 4 · Fora de escopo
- Tirar lotes do conjunto e destacar o lote selecionado no mapa — SPEC [localizacao_lote/004](004-revisao-do-conjunto.md).
- Recalcular a busca quando o desenho é **editado, arrastado ou apagado** depois dela — sem dono ainda.
- Percentual de cada lote contido no desenho e a modalidade "a maior" × "a menor" — SPEC
  [certidao_lancamento/003](../certidao_lancamento/003-certidao-a-maior-e-a-menor.md).
- Linha e ponto desenhados como entrada de busca — sem dono ainda.

## 5 · Peças de referência a compor
- `@static/src/js/mapa/desenho/bancada.js` → handler de `pm:create`: onde o círculo já vira polígono.
- `@services/domain/geometry/reprojecao.py` → `reprojetar` (SPEC 002).
- `@services/integrations/wfs` → `CqlFilter`, `CqlPredicate`, `build_fetcher`.
- `@services/domain/lote_geocod` → `feature_para_lote`, `LoteFeature`.
- `@templates/lote_geocoder/partials/_gaveta_lote.html` → conteúdo da gaveta de detalhe.
- `@static/src/tema-dimap.dev.css` → `.gaveta-inferior`, `.gaveta-coluna`, `.table-onsen`, `.gaveta-lateral-detalhe`.
- Skills: `leaflet-geoman`, `wfs-fetcher`, `mock`, `componentes-frontend`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/integrations/wfs/models.py`**

```python
class CqlIntersects(BaseModel):
    field: str
    wkt: str = Field(pattern=PADRAO_WKT)

    def to_cql(self) -> str:
        return f"INTERSECTS({self.field}, {self.wkt})"


class CqlFilter(BaseModel):
    predicates: list[CqlPredicate | CqlDWithin | CqlIntersects] = Field(default_factory=list)  # ALTERADO
    logic: Literal["AND", "OR"] = "AND"
    raw_cql: str | None = None
```

**`services/domain/lote_espacial/do_desenho.py`**

```python
class LotesDoDesenhoInput(BaseModel):
    desenho: Desenho
    camada: CamadaLotes
    area_maxima_m2: float = Field(gt=0)


class ConferenciaDesenhoInput(BaseModel):
    desenho: Desenho
    crs_metrico: int
    area_maxima_m2: float = Field(gt=0)


class DesenhoConferido(BaseModel):
    projetado: PolygonGeometry   # no CRS métrico
    area_m2: float = Field(gt=0)


class ConferirDesenho:
    """A oferta e a busca recusam pelo mesmo critério: é uma peça só, composta pelas duas."""

    def __call__(self, entrada: ConferenciaDesenhoInput) -> DesenhoConferido:
        return self.pipeline(entrada)

    def pipeline(self, entrada: ConferenciaDesenhoInput) -> DesenhoConferido:
        projetado = reprojetar(entrada.desenho.geometria, entrada.desenho.crs, entrada.crs_metrico)
        geos = GEOSGeometry(json.dumps(projetado.model_dump()))
        if not geos.valid:
            raise DesenhoInvalidoError(geos.valid_reason)
        if geos.area > entrada.area_maxima_m2:
            raise DesenhoGrandeDemaisError(geos.area, entrada.area_maxima_m2)
        return DesenhoConferido(projetado=projetado, area_m2=geos.area)


class BuscarLotesDoDesenho:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher
        self._conferir = ConferirDesenho()

    def __call__(self, entrada: LotesDoDesenhoInput) -> LotesDoDesenho:
        return self.pipeline(entrada)

    def pipeline(self, entrada: LotesDoDesenhoInput) -> LotesDoDesenho:
        # A conferência vem ANTES da rede: o GeoServer não paga por desenho que vai ser recusado.
        conferido = self._conferir(ConferenciaDesenhoInput(
            desenho=entrada.desenho,
            crs_metrico=entrada.camada.crs_camada,
            area_maxima_m2=entrada.area_maxima_m2,
        ))
        lotes = self._consultar(conferido.projetado, entrada.camada)
        return LotesDoDesenho(
            desenho=entrada.desenho,
            area_m2=conferido.area_m2,
            lotes=lotes,
        )

    def _consultar(self, projetado: PolygonGeometry, camada: CamadaLotes) -> tuple[LoteFeature, ...]:
        request = WfsFeatureRequest(
            nome_camada=camada.nome,
            srs_name=f"EPSG:{camada.crs_saida}",   # a intersecção é do servidor; a saída já vem no CRS do mapa
            cql_filter=CqlFilter(predicates=[CqlIntersects(field=camada.campo_geometria, wkt=_wkt(projetado))]),
            count=PAGE_SIZE,
        )
        return tuple(
            lote
            for page in self.fetcher(request)
            for feature in page.features
            if (lote := feature_para_lote(feature, camada.crs_saida)) is not None
        )
```

**`apps/lote_espacial/views.py`** — três rotas abertas.

```python
def _desenho(dados: QueryDict) -> Desenho:
    geometria = PolygonGeometry.model_validate_json(dados.get("desenho", ""))
    return Desenho(geometria=geometria, crs=MAP_OUTPUT_CRS)


@require_POST
def ofertar_desenho(request: HttpRequest) -> HttpResponse:
    # Confere e mede, sem consultar lote: o desenho ruim é recusado já aqui, antes do botão existir.
    desenho = _desenho(request.POST)
    try:
        conferido = ConferirDesenho()(ConferenciaDesenhoInput(
            desenho=desenho,
            crs_metrico=MAP_INTERPOLATION_CRS,
            area_maxima_m2=LOTES_DESENHO_AREA_MAXIMA_M2,
        ))
    except (DesenhoInvalidoError, DesenhoGrandeDemaisError) as erro:
        return render(request, TEMPLATE_AVISO_DESENHO, {"mensagem": str(erro)})
    return render(request, TEMPLATE_OFERTA_DESENHO, contexto_oferta(desenho, conferido))


@require_POST
def lotes_do_desenho(request: HttpRequest) -> HttpResponse:
    entrada = LotesDoDesenhoInput(
        desenho=_desenho(request.POST),
        camada=camada_lotes(),
        area_maxima_m2=LOTES_DESENHO_AREA_MAXIMA_M2,
    )
    try:
        resultado = BuscarLotesDoDesenho(build_fetcher(settings))(entrada)
    except (DesenhoInvalidoError, DesenhoGrandeDemaisError) as erro:
        return render(request, TEMPLATE_AVISO_DESENHO, {"mensagem": str(erro)})
    return render(request, TEMPLATE_RESULTADO_DESENHO, contexto_lotes_do_desenho(resultado))


@require_GET
def detalhe_do_lote(request: HttpRequest) -> HttpResponse:
    entrada = LotePorIdentificadorInput(
        id_poligono=request.GET.get("id", ""),
        layer_name=WFS_LAYER_LOTE_CIDADAO,
        output_crs=MAP_OUTPUT_CRS,
    )
    # LotePorIdentificador devolve LoteFeature | None: o polígono pode ter saído da camada.
    lote = LotePorIdentificador(build_fetcher(settings))(entrada)
    if lote is None:
        return render(request, TEMPLATE_AVISO_DESENHO, {"mensagem": MSG_LOTE_NAO_ENCONTRADO})
    return render(request, TEMPLATE_DETALHE_LOTE, {"lote": lote.attributes})
```

**`static/src/js/mapa/desenho/oferta.js`** — cola de Leaflet → HTMX; nenhum estado.

```javascript
// A URL vem do markup (data-url-ofertar-desenho no container do mapa): o JS não conhece rota.
export function ofertarDesenho(mapa, container) {
  mapa.on("pm:create", (evento) => {
    if (!["Polygon", "Rectangle", "Circle"].includes(evento.shape)) return;
    htmx.ajax("POST", container.dataset.urlOfertarDesenho, {
      target: "#gaveta-entidade",
      swap: "innerHTML",
      values: { desenho: JSON.stringify(evento.layer.toGeoJSON().geometry) },
    });
  });
}
```

**`static/src/js/mapa/init.js`** — o resultado entra por último no `overlayPane`; o desenho volta
para cima dele.

```javascript
camadaResultado = adicionarResultado(mapa, data.geometria, data.cor, data.enquadrar);
mapa.pm.getGeomanLayers().forEach((camada) => camada.bringToFront());
```

**`templates/lote_espacial/partials/_resultado_desenho.html`** — mapa + três placas fora de banda.

```html
{% include "mapping/_mapa.html" %}
<div id="gaveta-entidade" hx-swap-oob="innerHTML">{% include "lote_espacial/partials/_gaveta_desenho.html" %}</div>
<div id="gaveta-inferior-conteudo" hx-swap-oob="innerHTML">{% include "lote_espacial/partials/_tabela_lotes.html" %}</div>
{# Linha da tabela: hx-get em lote_espacial:detalhe_do_lote?id=… com alvo em #gaveta-detalhe. #}
```

## 7 · Caveats
Um lote entra na lista quando **intersecta** o desenho, basta encostar. É o predicado que o
GeoServer resolve numa ida só. O custo é que um traço impreciso traz o vizinho por uma lasca; quem
tira esse vizinho é a SPEC 004.

O desenho viaja no formulário da gaveta como GeoJSON, e o servidor não guarda nada entre a oferta e
a busca. A home não tem sessão de trabalho, e guardar o desenho criaria estado que ninguém limpa. O
custo é que o GeoJSON vai e volta a cada passo, e que editar o desenho no mapa depois da oferta não
muda o que o botão manda.

`LOTES_DESENHO_AREA_MAXIMA_M2` (250.000 m² por padrão) limita o tamanho da consulta. Sem ele, um
desenho sobre um bairro devolveria dezenas de milhares de lotes numa página do navegador. O custo é
recusar desenho legítimo acima do corte até alguém calibrá-lo no ambiente.

`htmx.ajax` é chamado de dentro de um callback do Leaflet-Geoman. É cola entre as duas bibliotecas
e não carrega estado de domínio, que é o que o §7.2 do CLAUDE.md permite. O custo é um ponto em que
a requisição não nasce de atributo HTMX no markup.

## 8 · Testes (TDD)
- `test_intersects_monta_cql` — `CqlIntersects` gera `INTERSECTS(campo, POLYGON((…)))`.
- `test_desenho_reprojetado_para_crs_da_camada_antes_da_consulta` — o WKT do request capturado tem
  coordenadas UTM e o `srsName` pedido é o do mapa.
- `test_desenho_invalido_ou_grande_demais_recusado_sem_consultar` — laço em "8" levanta
  `DesenhoInvalidoError`, área acima do corte levanta `DesenhoGrandeDemaisError`, e o fetcher fake
  não é chamado em nenhum dos dois.
- `test_ofertar_desenho_invalido_responde_aviso_sem_botao` — a oferta de um laço em "8" traz a
  mensagem e não traz o formulário de busca.
- `test_lotes_do_desenho_traz_area_e_lotes` — duas features viram dois `LoteFeature` e a área em m².
- `test_lote_por_identificador_filtra_cd_identificador` — o request usa `cd_identificador = id`.
- `test_ofertar_desenho_anonimo_abre_gaveta_com_area_e_botao` — POST sem login devolve a gaveta com a
  área e o formulário para `lote_espacial:lotes_do_desenho` carregando o desenho.
- `test_lotes_do_desenho_devolve_mapa_resumo_e_tabela` — payload do mapa, OOB da gaveta lateral com a
  quantidade e OOB da gaveta inferior com uma linha por lote.
- `test_detalhe_do_lote_abre_gaveta_de_detalhe` — GET devolve o conteúdo da gaveta do lote com o SQL.
- `test_lotes_do_desenho_no_geosampa` — retângulo real conhecido devolve os lotes esperados
  *(marker `integration`)*.
