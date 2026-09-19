---
spec: localizacao_lote/003
versao: v6
atualizado_em: 2026-09-18
testes_tdd: true
implementado: true
markers_obrigatorios: [integration]
changelog:
  - v1: versão inicial
  - v2: submódulo `lote_espacial` renomeado para `lotes_mais_proximos`
  - v3: gatilho passa a ser a ação do poço de polígonos, oferecida por um registro de ações sobre desenho
  - v4: a ação aparece só com um polígono selecionado, opera sobre ele e leva ao contexto do resultado — tabela embaixo, gaveta do lote ao lado
  - v5: o desenho que originou o resultado não responde ao clique enquanto o contexto de ação dura, e o resultado nasce fora da bancada
  - v6: a alça recolhe a gaveta inferior, que volta pela paleta, e só o ✕ a fecha; com ela presente, a bancada não encaixa no rodapé
---

# SPEC localizacao_lote/003 — Lotes que cruzam um desenho

## 1 · User story
Quem usa o mapa marca um polígono desenhado sobre um terreno e pede os lotes cadastrados que ele
cruza, no contexto de um imóvel que ocupa mais de um lote, para ver de uma vez quais lotes compõem
aquele terreno.

## 2 · Condições de pronto
- [ ] Com um **polígono selecionado** na gaveta dos desenhos, o poço de polígonos traz, abaixo da
      lista, a ação **"Lotes intersectados"**, inclusive para quem não fez login; sem seleção, ou com um
      ponto ou uma linha selecionados, ela não aparece em poço algum. Uma ação administrativa inscrita
      para um tipo de desenho só aparece no poço desse tipo, quando o selecionado é dele, e só para
      quem tem competência para executá-la.
- [ ] Acionar "Lotes intersectados" desenha no mapa **todos os lotes que intersectam o polígono selecionado
      na gaveta**, como ele está no mapa naquele momento — inclusive depois de editado —, abre a
      **gaveta inferior** só com a quantidade e a tabela deles (SQL, endereço, situação do lançamento)
      e **recolhe a gaveta dos desenhos**; os lotes vêm em **cinza**, por cima dos polígonos
      desenhados, que ficam na cor deles e mais transparentes. Polígono que não cruza lote algum
      mostra o estado de falta escrito na gaveta inferior.
- [ ] Passar o ponteiro numa linha da tabela **realça** o lote dela no mapa, na mesma cor; o lote
      escolhido — pela linha ou pelo mapa — fica com um realce **mais forte**, até outro ser escolhido.
- [ ] Com a gaveta inferior aberta, a gaveta lateral termina **acima** dela, e a **barra de busca fica
      recolhida**. A **alça** recolhe a gaveta inferior para fora da tela, deixando só uma **paleta** na
      borda de baixo, como a da gaveta lateral, que a puxa de volta, subindo devagar; recolhida, a
      lateral volta à altura inteira e o contexto continua. Só o **✕**, gravado, a fecha, encerra o
      contexto da ação e devolve a busca.
- [ ] Enquanto há gaveta inferior, aberta ou recolhida, a bancada de desenho **não encaixa no rodapé**:
      a que estava encaixada embaixo vai para a direita, a solta atrás da gaveta sobe acima dela, e
      largá-la perto do rodapé não a encaixa ali; ela segue arrastável para qualquer outro lugar.
- [ ] Clicar numa linha da tabela, **ou num lote no mapa**, abre a gaveta lateral com a gaveta do lote
      da SPEC [localizacao_lote/001](001-dados-do-lote-na-gaveta.md) — um lote por vez —, e a tabela
      continua aberta; com a gaveta lateral já aberta, o conteúdo **troca por fade**, sem ela recolher.
- [ ] Clicar em **outro** desenho no mapa, fora dos lotes, devolve a gaveta dos desenhos, com ele
      selecionado; e acionar a ação de novo com outro polígono troca os lotes do mapa e da tabela pelos
      dele. Até o ✕ encerrar o contexto, o polígono que originou o resultado **não responde ao
      clique** — nem nos vãos sem lote — e os lotes seguem por cima dele.
- [ ] Polígono que se auto-intersecta, ou acima da área máxima configurada, é recusado sem consultar o
      WFS, com mensagem em português no aviso do mapa — a da área cita a área máxima —, e a gaveta dos
      desenhos recolhe para o aviso ficar à vista.
- [ ] O design da ação no poço, da gaveta inferior com a tabela e da gaveta lateral acima dela foi
      aprovado no mock e as peças novas portadas para o tema e o styleguide antes de qualquer template
      da aplicação usá-las.

## 3 · Domínio
O desenho é o [Desenho](../design/020-desenhos-na-gaveta.md#3--domínio) da gaveta dos desenhos; a
pergunta que esta SPEC faz a ela é só "qual é o desenho selecionado (`GavetaDesenhos.id_selecionado`),
e como ele está agora?". A
consulta espacial é do submódulo `lotes_mais_proximos`, com a
[CamadaLotes](002-lote-mais-proximo-do-endereco.md#3--domínio) e a reprojeção da SPEC 002. O ato
administrativo é o `AcaoImplementada` do registro de competências (SPECs `autorizacao/`), consumido
sem alteração.

**`services/domain/lotes_mais_proximos/models.py`**

```python
class LotesDoDesenho(BaseModel):
    """O que a consulta apurou: o desenho, a área dele e os lotes que ele cruza."""

    desenho: Desenho   # o de services/domain/desenho
    # Guardada: depende do CRS métrico da camada, que não mora no desenho.
    area_m2: float = Field(gt=0)
    lotes: tuple[LoteFeature, ...] = ()
```

**`services/domain/geometry/models.py`** — `GeoJsonProperties` inteiro.

```python
class GeoJsonProperties(BaseModel):
    """Contrato de propriedades GeoJSON interpretadas e esperadas pelo frontend (Leaflet)."""
    popup_html: str | None = None
    rotulo: str | None = None
    cor: str | None = None
    url_ficha: str | None = None   # ALTERADO nesta SPEC: a rota que o clique na feature abre na gaveta lateral
    id: str | None = None          # ALTERADO nesta SPEC: o que liga a linha da tabela à feature no mapa
```

**`services/domain/lote_geocod/models.py`** — o lote por identificador do polígono, que a gaveta do
lote aberta pela tabela ou pelo mapa (e a SPEC [certidao_lancamento/001](../certidao_lancamento/001-certidao-de-um-lote.md))
consulta.

```python
class LotePorIdentificadorInput(BaseModel):
    id_poligono: str = Field(pattern=r"^\d+$")
    layer_name: str
    output_crs: int
```

**`apps/mapping/acoes_desenho.py`** — o que um poço pode oferecer, em duas naturezas, como o
`ItemAcao` × `ItemLivre` do painel.

```python
class AcaoSobreDesenho(BaseModel):
    """Ato administrativo inscrito no REGISTRO que opera sobre desenho: só aparece a quem tem a caneta."""

    model_config = ConfigDict(frozen=True)

    acao: AcaoImplementada
    tipos: frozenset[TipoDesenho] = Field(min_length=1)


class ConsultaSobreDesenho(BaseModel):
    """Rota aberta que opera sobre desenho. Fora do REGISTRO: não é concedível e aparece a todos."""

    model_config = ConfigDict(frozen=True)

    slug: str = Field(pattern=PADRAO_SLUG)   # mesmo formato das ações: é ele que encontra o SVG
    nome: str
    tooltip: str
    url_name: str
    tipos: frozenset[TipoDesenho] = Field(min_length=1)


class RegistroDesenho(BaseModel):
    """Coleção explícita e curada do que opera sobre desenho."""

    model_config = ConfigDict(frozen=True)

    itens: tuple[AcaoSobreDesenho | ConsultaSobreDesenho, ...]


class ItemPoco(BaseModel):
    """O que o poço desenha: as duas naturezas convergem para o mesmo item."""

    model_config = ConfigDict(frozen=True)

    slug: str
    nome: str
    tooltip: str
    url_name: str
```

**Mock:** [003-mock-lotes-do-desenho.html](003-mock-lotes-do-desenho.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Tirar lotes do conjunto — SPEC [localizacao_lote/004](004-revisao-do-conjunto.md).
- Refazer a busca sozinha quando o polígono é **editado, arrastado ou apagado** depois dela — sem dono ainda.
- Percentual de cada lote contido no desenho e a modalidade "a maior" × "a menor" — SPEC
  [certidao_lancamento/003](../certidao_lancamento/003-certidao-a-maior-e-a-menor.md).
- Primeiro ato administrativo sobre desenho (amostragem de ofertas, por exemplo) e consultas dos poços de ponto e de linha — sem dono ainda.

## 5 · Peças de referência a compor
- `@static/src/js/mapa/desenho/envio.js` → `inicializarEnvio`: enxerta no envio a geometria atual do traço marcado.
- `@static/src/js/mapa/desenho/sincronia.js` → o envio da coleção que monta a gaveta dos desenhos.
- `@templates/lote_geocoder/partials/_gaveta_lote.html` → a gaveta que a linha e o lote do mapa abrem.
- `@services/domain/desenho` → `Desenho`, `TipoDesenho`.
- `@services/domain/geometry` → `reprojetar` (SPEC 002), `para_geos` (design/020).
- `@services/integrations/wfs` → `CqlFilter`, `CqlPredicate`, `build_fetcher`.
- `@services/domain/lote_geocod` → `feature_para_lote`, `LoteFeature`, `MontarGavetaLote`: os dados da gaveta do lote.
- `@apps/competencias` → `AcaoImplementada`, `slugs_liberados`, `{% icone_acao %}` + `_icone_acao.html`; `@services/domain/autorizacao` → `PADRAO_SLUG`.
- `@apps/mapping/context.py` → `contexto_mapa`, `contexto_aviso`.
- `@static/src/js/mapa/desenho/arrasto.js` → `esquerdaTomada`, `recuoEsquerdo`, `desocuparEsquerda`: o guarda da gaveta lateral, que o do rodapé repete.
- `@static/src/tema-dimap.dev.css` → `.item-menu-swell`, `.gaveta-inferior`, `.gaveta-cabecalho`, `.gaveta-coluna`, `.gaveta-vazia`, `.table-onsen`, `.tabela-onsen-gaveta`.
- Skills: `leaflet-geoman`, `wfs-fetcher`, `htmx`, `painel`, `mock`, `componentes-frontend`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`apps/lotes_mais_proximos/desenho_declarado.py`** — o app declara o que oferece sobre desenho, como
declara ações em `acoes_declaradas.py`.

```python
CONSULTA_LOTES_INTERSECTADOS = ConsultaSobreDesenho(
    slug="lotes_mais_proximos.lotes_intersectados",
    nome="Lotes intersectados",
    tooltip="Lotes cadastrados que o polígono marcado cruza.",
    url_name="lotes_mais_proximos:lotes_do_desenho",
    tipos=frozenset({TipoDesenho.POLIGONO}),
)
```

**`apps/mapping/registro_desenho.py`** — ponto único de inscrição: oferecer algo sobre desenho é
acrescentar uma linha aqui. Um ato entra envolvendo a constante que já está no `REGISTRO`.

```python
def _construir_registro() -> RegistroDesenho:
    return RegistroDesenho(
        itens=(
            CONSULTA_LOTES_INTERSECTADOS,
            # AcaoSobreDesenho(acao=ACAO_AMOSTRAGEM_OFERTAS, tipos=frozenset({TipoDesenho.POLIGONO})),
        )
    )


REGISTRO_DESENHO = _construir_registro()
```

**`apps/mapping/acoes_desenho.py`** — o router: tipo do poço + canetas do usuário → o que o poço
oferece.

```python
class OfertaPocoInput(BaseModel):
    tipo: TipoDesenho
    slugs_liberados: frozenset[str]   # já resolvidos pela view: o router não vê request


class OfertarNoPoco:
    def __init__(self, registro: RegistroDesenho) -> None:
        self.registro = registro

    def __call__(self, entrada: OfertaPocoInput) -> tuple[ItemPoco, ...]:
        return self.pipeline(entrada)

    def pipeline(self, entrada: OfertaPocoInput) -> tuple[ItemPoco, ...]:
        return tuple(
            self._item(item)
            for item in self.registro.itens
            if entrada.tipo in item.tipos and self._liberado(item, entrada.slugs_liberados)
        )

    def _liberado(self, item: AcaoSobreDesenho | ConsultaSobreDesenho, slugs: frozenset[str]) -> bool:
        # A consulta não é ato: não há caneta que a libere, nem que a esconda.
        # O router só filtra; quem recusa o ato é a proteção da rota, a cada execução.
        if isinstance(item, ConsultaSobreDesenho):
            return True
        return item.acao.acao.slug in slugs

    def _item(self, item: AcaoSobreDesenho | ConsultaSobreDesenho) -> ItemPoco:
        if isinstance(item, ConsultaSobreDesenho):
            return ItemPoco(slug=item.slug, nome=item.nome, tooltip=item.tooltip, url_name=item.url_name)
        acao = item.acao.acao
        return ItemPoco(slug=acao.slug, nome=acao.nome, tooltip=acao.tooltip, url_name=item.acao.url_name)
```

**`apps/mapping/views.py`** — a gaveta dos desenhos entrega cada poço já com o que ele oferece. O
router não olha a seleção: ela muda no navegador sem ida ao servidor, e quem mostra as ações só no
poço do selecionado é o CSS do `.poco-desenhos` (design/020).

```python
    gaveta = MontarGavetaDesenhos()(entrada)
    ofertar = OfertarNoPoco(REGISTRO_DESENHO)                                   # NOVO
    liberados = slugs_liberados(request.user)                                  # NOVO: anônimo → vazio
    pocos = [
        (poco, ofertar(OfertaPocoInput(tipo=poco.tipo, slugs_liberados=liberados)))
        for poco in gaveta.pocos
    ]
    return render(request, TEMPLATE_GAVETA_DESENHOS, {"gaveta": gaveta, "pocos": pocos})
```

**`templates/mapping/_gaveta_desenhos.html`** — o laço dos poços passa a desempacotar os pares; o resto
da gaveta (o `<form>` único, o limpar, a contagem por tipo em `gaveta.pocos`) segue como está.

```html
<form class="gaveta-lateral-conteudo">
  {% for poco, itens in pocos %}                                         {# ALTERADO #}
    {% include "mapping/_poco_desenhos.html" with poco=poco itens=itens %}
  {% endfor %}
  ...
</form>
```

**`templates/mapping/_poco_desenhos.html`** — a âncora do rodapé ganha o recorte e, dentro dele, os
itens. O `hx-include` pesca o **único** radio `id_bancada` marcado na gaveta inteira — que, com o
botão à vista, é sempre um desenho deste poço —, e o `envio.js` enxerta o `desenho` lido do mapa.

```html
{% load icones %}
{# Sem espaço entre a âncora e o {% if %}: com itens vazios ela tem de sair :empty, senão o empty:hidden não a recolhe. #}
<div class="poco-desenhos__acoes" id="acoes-desenho-{{ poco.tipo }}">{% if itens %}
  <div class="poco-desenhos__acoes-recorte">
    {# A casca .placa-lista (molécula nova, no mock) com cabeçalho "Ações" e a contagem. #}
    {% for item in itens %}
      {% icone_acao item.slug "pequeno" as svg %}
      <button type="button" class="card-well item-menu item-menu-swell" title="{{ item.tooltip }}"
              hx-post="{% url item.url_name %}" hx-include=".linha-desenho__marca:checked"
              hx-target="#resultado-busca" hx-swap="innerHTML">
        {% include "competencias/partials/_icone_acao.html" with svg=svg variante="pequeno" %}
        <span class="item-menu-rotulo">{{ item.nome }}</span>
      </button>
    {% endfor %}
  </div>
{% endif %}</div>
```

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

**`services/domain/lotes_mais_proximos/do_desenho.py`**

```python
class LotesDoDesenhoInput(BaseModel):
    desenho: Desenho
    crs_mapa: int          # o desenho não carrega CRS: vem do mapa, pela orquestração
    camada: CamadaLotes
    area_maxima_m2: float = Field(gt=0)

    @model_validator(mode="after")
    def _so_poligono(self) -> Self:
        # O Desenho da bancada aceita ponto e linha; esta consulta, não.
        if self.desenho.tipo is not TipoDesenho.POLIGONO:
            raise ValueError("A busca de lotes precisa de um polígono.")
        return self


class ConferenciaDesenhoInput(BaseModel):
    geometria: PolygonGeometry
    crs_mapa: int
    crs_metrico: int
    area_maxima_m2: float = Field(gt=0)


class DesenhoConferido(BaseModel):
    projetado: PolygonGeometry   # no CRS métrico
    area_m2: float = Field(gt=0)


class ConferirDesenho:
    """Recusa o polígono que o GeoServer não deve receber: laço que se cruza ou área acima do corte."""

    def __call__(self, entrada: ConferenciaDesenhoInput) -> DesenhoConferido:
        return self.pipeline(entrada)

    def pipeline(self, entrada: ConferenciaDesenhoInput) -> DesenhoConferido:
        projetado = reprojetar(entrada.geometria, entrada.crs_mapa, entrada.crs_metrico)
        geos = para_geos(projetado, entrada.crs_metrico)
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
            geometria=entrada.desenho.geometria,   # polígono garantido pelo validator do input
            crs_mapa=entrada.crs_mapa,
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

**`apps/lotes_mais_proximos/views.py`** — duas rotas abertas.

```python
class ConsultaLotesDoDesenho(BaseModel):
    """O formulário da gaveta: o único radio marcado e a geometria que o envio.js enxertou."""

    id_bancada: str
    desenho: PolygonGeometry

    @field_validator("desenho", mode="before")
    @classmethod
    def _do_json(cls, valor: object) -> object:
        # Sem o envio.js o campo não chega: vira ValidationError e cai no middleware.
        return json.loads(valor) if isinstance(valor, str) else valor


@require_POST
def lotes_do_desenho(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaLotesDoDesenho.model_validate(request.POST.dict())
    entrada = LotesDoDesenhoInput(
        desenho=Desenho(id_bancada=consulta.id_bancada, geometria=consulta.desenho),
        crs_mapa=MAP_OUTPUT_CRS,
        camada=camada_lotes(),
        area_maxima_m2=LOTES_DESENHO_AREA_MAXIMA_M2,
    )
    try:
        resultado = BuscarLotesDoDesenho(build_fetcher(settings))(entrada)
    except (DesenhoInvalidoError, DesenhoGrandeDemaisError) as erro:
        return render(request, "mapping/_recusa_acao.html", contexto_aviso(str(erro)))
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
        return render(request, "mapping/_aviso.html", contexto_aviso(MSG_LOTE_NAO_ENCONTRADO))
    # A gaveta do lote da SPEC 001, intacta: é ela que ocupa a gaveta lateral (#gaveta-entidade).
    gaveta = MontarGavetaLote()(GavetaLoteInput(lote=lote, crs_metrico=MAP_INTERPOLATION_CRS))
    return render(request, "lote_geocoder/partials/_gaveta_lote.html", {"gaveta": gaveta})
```

### Peças reaproveitáveis por toda ação

Uma ação que devolve resultado ao mapa responde pela mesma base, e a home reage a ela sem saber qual
ação foi: a gaveta inferior de resultado, o contexto de ação, a troca da gaveta lateral e a interação
com as features do resultado. A ação só preenche o corpo da gaveta e dá a cada feature `id` e
`url_ficha`.

**`templates/mapping/_resultado_acao.html`** — a base que a resposta da ação estende: payload do mapa,
gaveta inferior de resultado fora de banda, gaveta dos desenhos recolhida e a marca do contexto. A
gaveta tem dois controles: o toggle `#gaveta-resultado`, de id fixo, que só o ✕ desmarca e que encerra
o contexto; e o `#gaveta-resultado-recolhida`, **dentro** da placa, que a alça marca e a paleta
desmarca.

```html
{% include "mapping/_mapa.html" %}
<div id="gaveta-inferior-conteudo" hx-swap-oob="innerHTML">
  {# O toggle vem marcado junto da placa: é o swap que abre a gaveta, sem JS. #}
  <input type="checkbox" id="gaveta-resultado" class="gaveta-toggle" checked>
  <aside class="glass-drawer-bottom gaveta-inferior gaveta-inferior-rasa" role="dialog" aria-labelledby="gaveta-resultado-titulo">
    {# NOVO: filho imediato da placa, lido por :has(> ...) — recolher não fecha nem encerra o contexto. #}
    <input type="checkbox" id="gaveta-resultado-recolhida" class="gaveta-inferior-recolher">
    <label for="gaveta-resultado-recolhida" class="gaveta-alca" tabindex="0"               {# ALTERADO: antes, for="gaveta-resultado" #}
           aria-label="Recolher a gaveta"><span class="etched-line"></span></label>
    {# NOVO: a paleta da gaveta lateral virada para o rodapé; só aparece recolhida. #}
    <label for="gaveta-resultado-recolhida" class="paleta-gaveta paleta-gaveta-inferior" tabindex="0" aria-label="Abrir a gaveta">
      <svg class="etched paleta-gaveta-glifo" ...><path d="M6 15l6-6 6 6"/></svg>
    </label>
    <header class="gaveta-cabecalho items-center">
      <div class="min-w-0 flex items-baseline gap-3 flex-wrap">
        <h2 id="gaveta-resultado-titulo" class="text-xl font-bold tracking-tight leading-none text-madeira-700">{% block titulo %}{% endblock %}</h2>
        {% block resumo %}{% endblock %}
      </div>
      {# ALTERADO: o ✕ gravado, que incha e acende em ciano — composição do .btn-etched-swell. #}
      <label for="gaveta-resultado" class="btn-etched btn-etched-swell etched self-center" tabindex="0" aria-label="Fechar">
        <svg class="w-5 h-5" ...><path d="M6 6l12 12M18 6L6 18"/></svg>
      </label>
    </header>
    <div class="gaveta-corpo">{% block corpo %}{% endblock %}</div>
  </aside>
</div>
{% include "mapping/_recolher_gaveta_oob.html" with toggle="gaveta-desenhos-toggle" %}
{% include "mapping/_contexto_acao_oob.html" with encerra_com="#gaveta-resultado" %}
```

**`templates/mapping/_recusa_acao.html`** — a recusa de uma ação: o aviso do mapa e a gaveta dos
desenhos recolhida, para a busca, onde o aviso mora, ficar à vista.

```html
{% include "mapping/_aviso.html" %}
{% include "mapping/_recolher_gaveta_oob.html" with toggle="gaveta-desenhos-toggle" %}
```

**`templates/mapping/_recolher_gaveta_oob.html`** — o toggle de uma gaveta lateral desmarcado. Só ele é
trocado: o conteúdo fica no DOM, e a paleta reabre a gaveta.

```html
<input type="checkbox" id="{{ toggle }}" class="gaveta-lateral-toggle" hx-swap-oob="true">
```

**`templates/mapping/_contexto_acao_oob.html`** — a marca do contexto: o slug de quem o abriu, o
desenho sobre o qual ele opera e o controle que, desmarcado, o encerra. O slot
`<div id="contexto-acao" hidden></div>` mora na `core/home.html`; `acao` e `desenho` vêm do contexto
da view.

```html
<div id="contexto-acao" hidden hx-swap-oob="true"
     data-contexto-acao="{{ acao }}" data-desenho="{{ desenho }}"             {# ALTERADO: data-desenho #}
     data-encerra-com="{{ encerra_com }}"></div>
```

**`apps/mapping/context.py`** — o contexto de toda resposta de ação: o do mapa, o slug, o desenho de
origem e a cor única dos resultados de ação, distinta da dos desenhos.

```python
def contexto_resultado_acao(acao: str, desenho: Desenho, geojson: dict[str, Any]) -> dict[str, Any]:
    return contexto_mapa(geojson, MAP_COR_RESULTADO_ACAO) | {"acao": acao, "desenho": desenho.id_bancada}
    # MAP_COR_RESULTADO_ACAO: setting nova, rocha-600 da paleta, como as MAP_COR_* de hoje
```

**`static/src/js/ui/contexto_acao.js`** — tira a marca quando o controle apontado por ela é
desmarcado. Quem esconde a busca é o CSS, lendo a marca.

```javascript
export function inicializarContextoAcao() {
  document.addEventListener("change", (evento) => {
    const slot = document.getElementById("contexto-acao");
    const encerraCom = slot?.dataset.encerraCom;
    if (!encerraCom || evento.target.checked || !evento.target.matches(encerraCom)) return;
    slot.removeAttribute("data-contexto-acao");
    slot.removeAttribute("data-desenho");                        // NOVO: o desenho volta a ser clicável
    slot.removeAttribute("data-encerra-com");
  });
}
```

**`static/src/js/ui/troca_gaveta.js`** — callback de `htmx:beforeSwap` no `#gaveta-entidade`: diz no
alvo como a gaveta nova chega, comparando o `data-gaveta` da raiz de hoje com o da resposta. A
`_gaveta_desenhos.html` leva `data-gaveta="desenhos"`; a `_gaveta_lote.html`, `data-gaveta="lote-{{ id }}"`.

```javascript
const ALVO = "gaveta-entidade";
const TROCA_COM_FADE = "innerHTML swap:150ms settle:200ms";

function chave(raiz) {
  return raiz.querySelector(".gaveta-lateral")?.dataset.gaveta ?? null;
}

function modo(alvo, html) {
  if (!alvo.querySelector(":scope > .gaveta-lateral > .gaveta-lateral-toggle:checked")) return "entrada";
  const molde = document.createElement("template");
  molde.innerHTML = html;
  // A mesma gaveta redesenhada (a bancada, a cada traço) não anima: só outra entidade troca.
  return chave(molde.content) === chave(alvo) ? "mesma" : "troca";
}

export function inicializarTrocaGaveta() {
  htmx.on("htmx:beforeSwap", (evento) => {
    const alvo = evento.detail.target;
    if (alvo.id !== ALVO) return;
    alvo.dataset.trocaGaveta = modo(alvo, evento.detail.serverResponse);
    if (alvo.dataset.trocaGaveta === "troca") evento.detail.swapOverride = TROCA_COM_FADE;
  });
}
```

**`static/src/js/mapa/interacao_resultado.js`** — utilitário de Leaflet para qualquer resultado no
mapa: os desenhos descem para baixo dele, a feature com `url_ficha` abre a gaveta dela, e a feature
cujo `id` está sob o ponteiro ou escolhido numa `[data-id-feature]` da gaveta inferior acende. Estado
visual do mapa, e só dele; o escolhido zera a cada resultado novo.

```javascript
const DESENHO_SOB_RESULTADO = { fillOpacity: 0.2 };
// Traço em JS porque é estilo de <path> do Leaflet; o halo é classe do tema.
const REALCE = {
  normal: { weight: 1.5, fillOpacity: 0.18, brilho: null },
  ponteiro: { weight: 3, fillOpacity: 0.4, brilho: "realce-resultado" },
  escolhido: { weight: 4, fillOpacity: 0.55, brilho: "realce-resultado-forte" },
};

let resultado = null;
const estado = { idEscolhido: null, idSobPonteiro: null };

function realcar() {
  resultado?.eachLayer((camada) => {
    const id = camada.feature?.properties?.id;
    pintar(camada, id === estado.idEscolhido ? "escolhido" : id === estado.idSobPonteiro ? "ponteiro" : "normal");
  });
}

function escolher(id) {
  estado.idEscolhido = id;
  realcar();
}

// Uma vez, no init.js: os gatilhos vêm da gaveta inferior, que é trocada a cada resultado.
export function inicializarInteracaoResultado() {
  const linha = (evento) => evento.target.closest("#gaveta-inferior-conteudo [data-id-feature]");
  document.addEventListener("mouseover", (evento) => {
    const id = linha(evento)?.dataset.idFeature ?? null;
    if (id === estado.idSobPonteiro) return;
    estado.idSobPonteiro = id;
    realcar();
  });
  // A linha pede a gaveta pelo próprio hx-get; aqui ela só vira a escolhida.
  document.addEventListener("click", (evento) => {
    const id = linha(evento)?.dataset.idFeature;
    if (id) escolher(id);
  });
}

// A cada resultado aplicado, no aplicarResultado do init.js.
export function interagirComResultado(mapa, camadaResultado) {
  resultado = camadaResultado;
  estado.idEscolhido = null;
  estado.idSobPonteiro = null;
  mapa.pm.getGeomanLayers().forEach((camada) => {
    if (camada.setStyle) camada.setStyle(DESENHO_SOB_RESULTADO);   // o marcador de ponto não tem estilo
    camada.bringToBack?.();
  });
  camadaResultado.eachLayer((camada) => {
    const { id, url_ficha: urlFicha } = camada.feature?.properties ?? {};
    if (!urlFicha) return;
    camada.on("click", () => {
      escolher(id);
      htmx.ajax("GET", urlFicha, { target: "#gaveta-entidade", swap: "innerHTML" });
    });
  });
  realcar();
}
```

**`static/src/js/mapa/camada_resultado.js`** — resultado não é desenho. O `getGeomanLayers()` do plugin
devolve toda camada vetorial do mapa; sem `pmIgnore`, o resultado seria repintado, rebaixado, listado
na gaveta e apagado como um traço da bancada. O encaixe nele continua valendo.

```javascript
const FORA_DA_BANCADA = { pmIgnore: true, snapIgnore: false };   // NOVO: nas opções do L.geoJSON e do circleMarker
```

**`static/src/js/mapa/init.js`** — os três inicializadores entram no `montarMapaBase`, e o
`aplicarResultado` passa a entregar a camada nova à interação.

```javascript
camadaResultado = adicionarResultado(mapa, data.geometria, data.cor);
interagirComResultado(mapa, camadaResultado);                    // NOVO
```

**`static/src/tema-dimap.dev.css`** — as peças de tela do padrão. A gaveta rasa tem altura fixa, e é
essa medida que deixa a lateral parar acima dela.

```css
/* VARIANTE · .gaveta-inferior-rasa, e a lateral da home que termina acima dela. */
@media (width >= 48rem) {
  .gaveta-inferior-rasa { height: var(--gaveta-rasa-altura); }   /* TOKEN novo: 16rem */
  .tela-home .gaveta-lateral { transition-property: transform, bottom; }
  .tela-home:has(.gaveta-toggle:checked + .gaveta-inferior-rasa) .gaveta-lateral {
    bottom: calc(var(--gaveta-rasa-altura) + 0.75rem);
  }
}

/* NOVO · a rasa sobe devagar e assenta; chegando pelo swap já aberta, sobe do rodapé. */
.gaveta-inferior-rasa { @apply duration-1000 ease-out; }
@starting-style {
  .gaveta-toggle:checked + .gaveta-inferior-rasa { @apply translate-y-full; }
}

/* NOVO · ÁTOMO .paleta-gaveta-inferior — a .paleta-gaveta virada para o rodapé, só na rasa recolhida. */
.paleta-gaveta-inferior {
  @apply top-auto left-1/2 bottom-full -translate-x-1/2 translate-y-0 opacity-0 pointer-events-none;
  @apply w-[4.5rem] h-9 rounded-none rounded-t-full border-l border-b-0 bg-gradient-to-t;
  @apply shadow-[inset_0_1px_0_rgba(255,255,255,1),0_-8px_24px_rgba(7,58,84,0.28),0_0_20px_rgba(72,202,228,0.25)];
}

/* NOVO · recolhida, a placa sai da tela, a paleta fica na borda e a lateral volta à altura inteira. */
.gaveta-inferior-recolher { @apply sr-only; }
.gaveta-toggle:checked + .gaveta-inferior-rasa:has(> .gaveta-inferior-recolher:checked) { @apply translate-y-full; }
.gaveta-toggle:checked + .gaveta-inferior-rasa:has(> .gaveta-inferior-recolher:checked) > .paleta-gaveta-inferior {
  @apply opacity-100 pointer-events-auto;
}
.tela-home:has(.gaveta-toggle:checked + .gaveta-inferior-rasa > .gaveta-inferior-recolher:checked) .gaveta-lateral {
  @apply bottom-0;
}

/* VARIANTE · .table-onsen-compacta — linha baixa, para a tabela que divide a altura com o mapa. */
.table-onsen-compacta thead th { @apply p-1.5; }
.table-onsen-compacta tbody td { @apply px-3 py-1.5 text-[13px]; }

/* Os três modos do troca_gaveta.js — entrada desliza, troca funde só o conteúdo do painel, mesma não anima. */
@starting-style {
  [data-troca-gaveta="entrada"] > .gaveta-lateral:has(> .gaveta-lateral-toggle:checked) {
    transform: translateX(-100%);
  }
  [data-troca-gaveta="troca"] .gaveta-lateral-painel > * { opacity: 0; }
}
[data-troca-gaveta="troca"] .gaveta-lateral-painel > * { @apply transition-opacity duration-150 ease-in-out; }
[data-troca-gaveta="troca"].htmx-swapping .gaveta-lateral-painel > * { @apply opacity-0; }

/* Com a marca de contexto de ação, a busca recolhe como sob a gaveta lateral aberta. */
.tela-home:has(#contexto-acao[data-contexto-acao]) .search-hero {
  @apply opacity-0 -translate-y-5 scale-95 pointer-events-none invisible;
}

/* ÁTOMO · o halo da feature realçada, na tinta de rocha dos resultados de ação. */
.realce-resultado { filter: drop-shadow(0 0 4px rgba(65, 90, 119, 0.75)); }
.realce-resultado-forte {
  filter: drop-shadow(0 0 3px rgba(255, 255, 255, 0.95)) drop-shadow(0 0 10px rgba(46, 69, 96, 0.9));
}
```

**`static/src/js/mapa/desenho/selecao.js`** — o desenho de origem do contexto de ação não responde: o
clique nele vale como clique no mapa vazio. Qualquer outro desenho cujo radio não está no DOM (a
gaveta lateral é a de uma entidade) pede a gaveta dos desenhos de volta, já com ele selecionado.

```javascript
// NOVO: sem isso, o vão sem lote dentro do polígono o reselecionaria e o traria por cima dos lotes.
if (String(L.Util.stamp(camada)) === document.getElementById("contexto-acao")?.dataset.desenho) return;
const radio = document.querySelector(`.linha-desenho__marca[value="${L.Util.stamp(camada)}"]`);
if (!radio) {                                                    // ALTERADO: antes, só return
  L.DomEvent.stopPropagation(evento.originalEvent);
  pedirGavetaDesenhos(String(L.Util.stamp(camada)));             // exportado de sincronia.js
  return;
}
```

**`static/src/js/mapa/desenho/sincronia.js`** — o `enviar` vira `pedirGavetaDesenhos(selecionado)`,
exportado; os eventos do plugin o chamam com o marcado da gaveta, como hoje.

### O que é só desta ação

**`apps/lotes_mais_proximos/contexto.py`** — cada lote vai ao mapa com o `id` que a linha da tabela
também carrega e a rota da gaveta dele.

```python
def _properties_lote_do_desenho(lote: LoteFeature) -> GeoJsonProperties:
    return GeoJsonProperties(
        id=lote.attributes.id_poligono,
        rotulo=f"SQL {lote.attributes.sql}",
        url_ficha=f"{reverse('lotes_mais_proximos:detalhe_do_lote')}?id={lote.attributes.id_poligono}",
    )


def contexto_lotes_do_desenho(resultado: LotesDoDesenho) -> dict[str, Any]:
    geojson = to_geojson_feature_collection(resultado.lotes, _properties_lote_do_desenho)
    return contexto_resultado_acao(CONSULTA_LOTES_INTERSECTADOS.slug, resultado.desenho, geojson) | {"resultado": resultado}
```

**`templates/lotes_mais_proximos/partials/_resultado_desenho.html`** — o `TEMPLATE_RESULTADO_DESENHO`
só preenche a base: título, resumo e a tabela.

```html
{% extends "mapping/_resultado_acao.html" %}
{% block titulo %}Lotes intersectados{% endblock %}
{% block resumo %}
  ...  {# badge do desenho, quantidade de lotes e área do desenho #}
{% endblock %}
{% block corpo %}
  <section class="gaveta-coluna">
    ...  {# table.table-onsen.table-onsen-compacta #}
    {% for lote in resultado.lotes %}
      <tr data-id-feature="{{ lote.attributes.id_poligono }}"
          hx-get="{% url 'lotes_mais_proximos:detalhe_do_lote' %}?id={{ lote.attributes.id_poligono }}"
          hx-target="#gaveta-entidade" hx-swap="innerHTML">…</tr>
    {% empty %}
      ...  {# .gaveta-vazia: o desenho não cruza lote algum #}
    {% endfor %}
  </section>
{% endblock %}
```

## 7 · Caveats
Um lote entra na lista quando **intersecta** o desenho, basta encostar. É o predicado que o
GeoServer resolve numa ida só. O custo é que um traço impreciso traz o vizinho por uma lasca; quem
tira esse vizinho é a SPEC 004.

O registro e o router do desenho moram em `apps/mapping`, e não em `services/`. Eles operam sobre
`AcaoImplementada` e `url_name`, que são peças da camada Django, como o resolvedor do painel. O custo
é regra de oferta fora do domínio, testável só com o Django carregado.

`apps/mapping` passa a importar a declaração de cada app que oferece algo sobre desenho, como o
`REGISTRO` de competências importa as ações. É o que mantém a inscrição num ponto só, revisável em
code review. O custo é que cada app novo de ação sobre desenho edita o registro do `mapping`.

A gaveta dos desenhos passa a conhecer o usuário da sessão, para resolver as canetas. É o router que
esconde o ato de quem não pode executá-lo. O custo é que a gaveta dos desenhos deixa de ser a mesma
para todos, e cada montagem dela consulta as permissões.

A ação aparece para todo polígono selecionado, e o polígono inválido ou grande demais só é recusado
ao acioná-la. Conferir cada traço na montagem da gaveta refaria a conferência a cada desenho criado,
apagado ou modificado. O custo é um botão oferecido para um desenho que vai ser recusado.

O router oferece a ação a todo poço de polígonos, sem olhar a seleção, e é o CSS da gaveta que a
mostra só no poço do selecionado. A seleção muda no navegador sem ida ao servidor, então o servidor
não sabe qual poço está com ela. O custo é o botão no DOM de um poço sem seleção; a rota recusa
qualquer `desenho` que não seja polígono, venha de onde vier.

A busca não se refaz quando o polígono é editado depois dela. O resultado é de um clique, e o servidor
não guarda o desenho entre um envio e outro. O custo é tabela e mapa descrevendo um traço que já não
está na tela até o próximo clique na ação.

Toda ação que devolve resultado ao mapa responde pela base `mapping/_resultado_acao.html`, e a home
reage à resposta sem saber qual ação foi. É o que faz a próxima ação sobre desenho ser só o corpo da
gaveta e as `properties` das features. O custo é que a base supõe ação disparada da bancada — ela
recolhe a gaveta dos desenhos — e uma gaveta de resultado por vez: ação com outro formato de resultado
pede outra base.

Acionar uma ação recolhe a gaveta dos desenhos, e abrir uma feature a troca pela gaveta dela. A busca
leva do contexto da bancada ao do resultado, e a gaveta lateral mostra uma entidade por vez. O custo é
que trocar de polígono exige voltar à bancada, pela paleta ou pelo clique no desenho, e a base da
resposta conhecer o id do toggle da gaveta dos desenhos.

Com resultado no mapa, os desenhos descem para baixo dele, mais transparentes. É o que dá ao clique
sobre uma feature a gaveta dela, e ao clique em outro desenho fora delas a volta à bancada. O custo é o
desenho só ser clicável onde nenhuma feature o cobre, e desenho feito ou reselecionado depois do
resultado voltar para cima, com o preenchimento cheio, até o próximo resultado.

O desenho de origem não responde ao clique enquanto o contexto de ação dura. Um polígono que cruza a
rua tem vãos sem lote, e o clique ali o reselecionaria e o traria por cima dos lotes, que deixariam de
ser clicáveis. Quem diz qual é a origem é o servidor, na marca do contexto, e a regra acaba com ela. O
custo é o ponteiro de mão sobre um traço que não responde, e voltar a ele na bancada só pela paleta ou
fechando a gaveta inferior pelo ✕.

A gaveta de resultado tem altura fixa, e a home encurta a gaveta lateral enquanto ela está aberta. A
medida conhecida é o que deixa a lateral parar acima da inferior sem JavaScript. O custo é a regra de
layout da home conhecer as duas gavetas, e poucas linhas deixarem a placa com sobra.

Recolher e fechar são gestos distintos: a alça recolhe, a paleta puxa de volta e o ✕ fecha. Tirar a
tabela da frente não pode custar o resultado, que só volta refazendo a ação. O custo é que fechar uma
gaveta recolhida pede reabri-la antes, para chegar ao ✕.

Com gaveta inferior, o rodapé é dela: a bancada não encaixa ali, como já não encaixa à esquerda com a
gaveta lateral, e pelo mesmo mecanismo — o `arrasto.js` recebe do `bancada.js` se o rodapé está
tomado e quanto ele ocupa. O custo é a bancada não voltar sozinha ao rodapé quando a gaveta fecha.

A gaveta lateral que chega por swap no `#gaveta-entidade` ganha coreografia de chegada, pedida pelo
usuário, sem alterar o organismo: o `troca_gaveta.js` marca o alvo e o CSS lê a marca. Sem estado
anterior a transição do toggle não tem de onde partir, e só o JS sabe se a gaveta de antes estava
aberta e era outra. O custo é o JS ler o `data-gaveta` do HTML da resposta, e toda gaveta que entra
no `#gaveta-entidade` passar a depender desse atributo na raiz.

O contexto de ação é uma marca no DOM, e não cookie nem estado em JavaScript. O servidor a manda junto
da resposta da ação, o CSS a lê e o `contexto_acao.js` só a apaga. O custo é que ela só sai pelo
controle que aponta: um contexto encerrado por outro caminho deixa a busca recolhida até a página
recarregar.

A feature escolhida e a sob o ponteiro vivem em JavaScript, no `interacao_resultado.js`. É estado
visual de um controle do mapa, pedido pelo usuário, e o servidor não tem como saber onde está o
ponteiro. O custo é que o realce some quando a camada é redesenhada, sem memória da escolhida.

Todo resultado de ação vai ao mapa na mesma cor, `MAP_COR_RESULTADO_ACAO`, distinta da dos desenhos.
É o que separa, sem legenda, o que a pessoa traçou do que o sistema devolveu. O custo é que duas ações
não se distinguem pela cor, e o halo do realce, escrito em rocha no tema, só casa com essa cor.

Os testes do §8 não cobrem JavaScript, como já registrado em design/020. O custo é que a ordem das
camadas, o realce, o clique no lote, a volta à bancada pelo desenho, a troca da gaveta por fade e o
fim do contexto de ação só têm prova no smoke test manual.

`LOTES_DESENHO_AREA_MAXIMA_M2` (250.000 m² por padrão) limita o tamanho da consulta. Sem ele, um
desenho sobre um bairro devolveria dezenas de milhares de lotes numa página do navegador. O custo é
recusar desenho legítimo acima do corte até alguém calibrá-lo no ambiente.

## 8 · Testes (TDD)
- `test_poco_oferece_so_o_que_opera_sobre_o_tipo` — com um registro fake, a consulta de polígono sai
  para o poço de polígonos e não para o de ponto.
- `test_ato_sobre_desenho_so_para_quem_tem_a_caneta` — com um registro fake, o ato sai só quando o
  slug está nos liberados, e a consulta sai com os liberados vazios.
- `test_gaveta_anonima_traz_lotes_intersectados_no_poco_de_poligonos` — POST anônimo com um ponto e um
  polígono, o polígono selecionado, devolve o botão com `hx-post` para
  `lotes_mais_proximos:lotes_do_desenho` e `hx-include=".linha-desenho__marca:checked"` no
  `.poco-desenhos__acoes-recorte` do poço de polígonos; o poço do ponto
  tem a âncora `.poco-desenhos__acoes` vazia, sem nó algum dentro.
- `test_intersects_com_desenho_reprojetado` — o CQL do request capturado é
  `INTERSECTS(campo, POLYGON((…)))` com coordenadas UTM, e o `srsName` pedido é o do mapa.
- `test_desenho_invalido_ou_grande_demais_recusado_sem_consultar` — laço em "8" levanta
  `DesenhoInvalidoError`, área acima do corte levanta `DesenhoGrandeDemaisError`, e o fetcher fake
  não é chamado em nenhum dos dois.
- `test_lotes_do_desenho_traz_area_e_lotes` — duas features viram dois `LoteFeature` e a área em m².
- `test_lotes_do_desenho_devolve_mapa_tabela_e_recolhe_os_desenhos` — POST anônimo com `id_bancada` e
  `desenho` devolve o payload do mapa, com `id`, `cor` cinza e `url_ficha` em cada lote; o OOB da
  gaveta de resultado, com o toggle `#gaveta-resultado` marcado, o `#gaveta-resultado-recolhida`
  desmarcado dentro da placa, com a alça e a paleta apontando para ele e o ✕ para o
  `#gaveta-resultado`, a quantidade e uma linha por lote com o mesmo `data-id-feature`
  e `hx-get` mirando `#gaveta-entidade`; o OOB do toggle da gaveta dos desenhos desmarcado; e o OOB
  do `#contexto-acao` com o slug da ação, `data-desenho` com o `id_bancada` enviado e
  `data-encerra-com="#gaveta-resultado"`.
- `test_lotes_do_desenho_recusa_invalido_e_nao_poligono` — POST com laço em "8" devolve o aviso do
  mapa com a mensagem e o toggle da gaveta dos desenhos desmarcado, sem payload de mapa; POST com
  `id_bancada` e um `desenho` de ponto é recusado pela validação; nenhum dos dois consulta o WFS.
- `test_detalhe_do_lote_abre_a_gaveta_do_lote` — GET devolve a gaveta do lote da SPEC 001 com o SQL
  e `data-gaveta="lote-<id>"` na raiz, e o `LotePorIdentificador` filtra `cd_identificador = id`.
- `test_lotes_do_desenho_no_geosampa` — retângulo real conhecido devolve os lotes esperados
  *(marker `integration`)*.
