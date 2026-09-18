---
spec: localizacao_lote/003
versao: v3
atualizado_em: 2026-09-18
testes_tdd: false
implementado: false
markers_obrigatorios: [integration]
changelog:
  - v1: versão inicial
  - v2: submódulo `lote_espacial` renomeado para `lotes_mais_proximos`
  - v3: gatilho passa a ser a ação do poço de polígonos, oferecida por um registro de ações sobre desenho
---

# SPEC localizacao_lote/003 — Lotes que cruzam um desenho

## 1 · User story
Quem usa o mapa marca um polígono desenhado sobre um terreno e pede os lotes cadastrados que ele
cruza, no contexto de um imóvel que ocupa mais de um lote, para ver de uma vez quais lotes compõem
aquele terreno.

## 2 · Condições de pronto
- [ ] Todo poço de polígonos da gaveta dos desenhos traz, abaixo da lista, a ação **"Lotes
      contidos"**, inclusive para quem não fez login; os poços de ponto e de linha não a trazem.
- [ ] Uma ação administrativa inscrita para um tipo de desenho só aparece no poço desse tipo para
      quem tem competência para executá-la.
- [ ] Acionar "Lotes contidos" desenha no mapa **todos os lotes que intersectam o polígono marcado no
      poço**, como ele está no mapa naquele momento — inclusive depois de editado —, e abre a
      **gaveta inferior** com a quantidade e a tabela deles (SQL, endereço, situação do lançamento).
- [ ] Marcar outro polígono no poço e acionar a ação de novo troca os lotes do mapa e da tabela pelos
      do polígono marcado.
- [ ] Depois da busca, a gaveta lateral segue com a lista dos desenhos e a marca de cada poço intacta,
      e o desenho continua no mapa, por cima dos lotes.
- [ ] Clicar numa linha da tabela abre a **gaveta de detalhe** com os dados daquele lote, iguais aos
      da gaveta do lote da SPEC [localizacao_lote/001](001-dados-do-lote-na-gaveta.md) — um lote por
      vez.
- [ ] Polígono que se auto-intersecta é recusado com mensagem em português no aviso do mapa, sem
      consultar o WFS.
- [ ] Polígono acima da área máxima configurada é recusado do mesmo jeito, com mensagem que cita a
      área máxima.
- [ ] Polígono que não cruza lote algum mostra o estado de falta escrito na gaveta inferior.
- [ ] O design da ação no poço, da tabela na gaveta inferior e da gaveta de detalhe foi aprovado no
      mock e as peças novas portadas para o tema e o styleguide antes de qualquer template da
      aplicação usá-las.

## 3 · Domínio
O desenho é o [Desenho](../design/020-desenhos-na-gaveta.md#3--domínio) da gaveta dos desenhos; a
pergunta que esta SPEC faz a ele é só "qual polígono está marcado, e como ele está agora?". A
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

**`services/domain/lote_geocod/models.py`** — o lote por identificador do polígono, que a gaveta de
detalhe (e a SPEC [certidao_lancamento/001](../certidao_lancamento/001-certidao-de-um-lote.md))
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
- Tirar lotes do conjunto e destacar o lote selecionado no mapa — SPEC [localizacao_lote/004](004-revisao-do-conjunto.md).
- Refazer a busca sozinha quando o polígono é **editado, arrastado ou apagado** depois dela — sem dono ainda.
- Percentual de cada lote contido no desenho e a modalidade "a maior" × "a menor" — SPEC
  [certidao_lancamento/003](../certidao_lancamento/003-certidao-a-maior-e-a-menor.md).
- Primeiro ato administrativo sobre desenho (amostragem de ofertas, por exemplo) e consultas dos poços de ponto e de linha — sem dono ainda.

## 5 · Peças de referência a compor
- `@static/src/js/mapa/desenho/envio.js` → `inicializarEnvio`: enxerta no envio a geometria atual do traço marcado.
- `@services/domain/desenho` → `Desenho`, `TipoDesenho`.
- `@services/domain/geometry` → `reprojetar` (SPEC 002), `para_geos` (design/020).
- `@services/integrations/wfs` → `CqlFilter`, `CqlPredicate`, `build_fetcher`.
- `@services/domain/lote_geocod` → `feature_para_lote`, `LoteFeature`.
- `@apps/competencias` → `AcaoImplementada`, `slugs_liberados`, `{% icone_acao %}` + `_icone_acao.html`; `@services/domain/autorizacao` → `PADRAO_SLUG`.
- `@apps/mapping/context.py` → `contexto_mapa`, `contexto_aviso`; `@templates/lote_geocoder/partials/_gaveta_lote.html` → conteúdo da gaveta de detalhe.
- `@static/src/tema-dimap.dev.css` → `.placa-lista`, `.item-menu-swell`, `.gaveta-inferior`, `.gaveta-coluna`, `.table-onsen`, `.gaveta-lateral-detalhe`.
- Skills: `leaflet-geoman`, `wfs-fetcher`, `htmx`, `painel`, `mock`, `componentes-frontend`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`apps/lotes_mais_proximos/desenho_declarado.py`** — o app declara o que oferece sobre desenho, como
declara ações em `acoes_declaradas.py`.

```python
CONSULTA_LOTES_CONTIDOS = ConsultaSobreDesenho(
    slug="lotes_mais_proximos.lotes_contidos",
    nome="Lotes contidos",
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
            CONSULTA_LOTES_CONTIDOS,
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

**`apps/mapping/views.py`** — a gaveta dos desenhos entrega cada poço já com o que ele oferece.

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

**`templates/mapping/_poco_desenhos.html`** — a âncora do rodapé ganha os itens. O botão está dentro
do `<form>` do poço: o `hx-post` leva o `id_bancada` marcado, e o `envio.js` enxerta o `desenho`.

```html
{% load icones %}
<div class="poco-desenhos__acoes" id="acoes-desenho-{{ poco.tipo }}">
  {% if itens %}
    {# A casca .placa-lista com cabeçalho "Ações" e a contagem, como no mock do design/020. #}
    {% for item in itens %}
      {% icone_acao item.slug "pequeno" as svg %}
      <button type="button" class="card-well item-menu item-menu-swell" title="{{ item.tooltip }}"
              hx-post="{% url item.url_name %}" hx-target="#resultado-busca" hx-swap="innerHTML">
        {% include "competencias/partials/_icone_acao.html" with svg=svg variante="pequeno" %}
        <span class="item-menu-rotulo">{{ item.nome }}</span>
      </button>
    {% endfor %}
  {% endif %}
</div>
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
    """O formulário do poço: o radio marcado e a geometria que o envio.js enxertou."""

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
        return render(request, "mapping/_aviso.html", contexto_aviso(str(erro)))
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
    return render(request, TEMPLATE_DETALHE_LOTE, {"lote": lote.attributes})
```

**`templates/lotes_mais_proximos/partials/_resultado_desenho.html`** — mapa no alvo da busca + gaveta
inferior fora de banda. A gaveta lateral **não** é tocada: é ela que carrega a lista dos desenhos.

```html
{% include "mapping/_mapa.html" %}
<div id="gaveta-inferior-conteudo" hx-swap-oob="innerHTML">{% include "lotes_mais_proximos/partials/_tabela_lotes.html" %}</div>
{# Linha da tabela: hx-get em lotes_mais_proximos:detalhe_do_lote?id=… com alvo em #gaveta-detalhe. #}
```

**`static/src/js/mapa/init.js`** — o resultado entra por último no `overlayPane`; o desenho volta
para cima dele.

```javascript
camadaResultado = adicionarResultado(mapa, data.geometria, data.cor, data.enquadrar);
mapa.pm.getGeomanLayers().forEach((camada) => camada.bringToFront());
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

A ação aparece em todo poço de polígonos, e o polígono inválido ou grande demais só é recusado ao
acioná-la. Conferir cada traço na montagem da gaveta refaria a conferência a cada desenho criado,
apagado ou modificado. O custo é um botão oferecido para um desenho que vai ser recusado.

A busca não se refaz quando o polígono é editado depois dela. O resultado é de um clique, e o servidor
não guarda o desenho entre um envio e outro. O custo é tabela e mapa descrevendo um traço que já não
está na tela até o próximo clique na ação.

`LOTES_DESENHO_AREA_MAXIMA_M2` (250.000 m² por padrão) limita o tamanho da consulta. Sem ele, um
desenho sobre um bairro devolveria dezenas de milhares de lotes numa página do navegador. O custo é
recusar desenho legítimo acima do corte até alguém calibrá-lo no ambiente.

## 8 · Testes (TDD)
- `test_poco_oferece_so_o_que_opera_sobre_o_tipo` — com um registro fake, a consulta de polígono sai
  para o poço de polígonos e não para o de ponto.
- `test_ato_sobre_desenho_so_para_quem_tem_a_caneta` — com um registro fake, o ato sai só quando o
  slug está nos liberados, e a consulta sai com os liberados vazios.
- `test_gaveta_anonima_traz_lotes_contidos_no_poco_de_poligonos` — POST anônimo com um ponto e um
  polígono devolve o botão com `hx-post` para `lotes_mais_proximos:lotes_do_desenho` dentro do
  formulário do poço de polígonos, e nenhum no do ponto.
- `test_intersects_com_desenho_reprojetado` — o CQL do request capturado é
  `INTERSECTS(campo, POLYGON((…)))` com coordenadas UTM, e o `srsName` pedido é o do mapa.
- `test_desenho_invalido_ou_grande_demais_recusado_sem_consultar` — laço em "8" levanta
  `DesenhoInvalidoError`, área acima do corte levanta `DesenhoGrandeDemaisError`, e o fetcher fake
  não é chamado em nenhum dos dois.
- `test_lotes_do_desenho_traz_area_e_lotes` — duas features viram dois `LoteFeature` e a área em m².
- `test_lotes_do_desenho_devolve_mapa_e_tabela_sem_tocar_a_gaveta_lateral` — POST anônimo com
  `id_bancada` e `desenho` devolve o payload do mapa e o OOB da gaveta inferior com a quantidade e uma
  linha por lote, e nenhum OOB em `#gaveta-entidade`.
- `test_lotes_do_desenho_invalido_responde_aviso` — POST com laço em "8" devolve o aviso do mapa com
  a mensagem, sem payload de mapa.
- `test_detalhe_do_lote_abre_gaveta_de_detalhe` — GET devolve o conteúdo da gaveta do lote com o SQL,
  e o `LotePorIdentificador` filtra `cd_identificador = id`.
- `test_lotes_do_desenho_no_geosampa` — retângulo real conhecido devolve os lotes esperados
  *(marker `integration`)*.
