---
spec: localizacao_lote/002
versao: v6
atualizado_em: 2026-09-17
testes_tdd: true
implementado: true
markers_obrigatorios: [integration]
changelog:
  - v1: versão inicial
  - v2: submódulo `lote_espacial` renomeado para `lotes_mais_proximos`
  - v3: `NenhumLoteProximoError` e a mensagem de ausência de lote no raio ganham snippet próprio
  - v4: a gaveta do lote exibe a distância até o ponto de origem, em card condicional
  - v5: texto final da mensagem de ausência de lote, e o raio declarado como variável de ambiente
  - v6: "[admin] implementado — testes TDD escritos e verdes; `WFS_LOTE_CIDADAO_CAMPO_GEOMETRIA`
    nova (default `ge_poligono`); `reprojetar` corrigido para srid via atributo (§7 Caveats);
    supersede o teste de gaveta da SPEC 001 no resultado de endereço"
---

# SPEC localizacao_lote/002 — Lote mais próximo do endereço interpolado

## 1 · User story
Quem usa a busca pede, na gaveta do endereço interpolado, o lote cadastrado mais próximo daquele
ponto no mesmo logradouro, no contexto de um endereço que não bate com nenhum endereço fiscal, para
chegar ao lote sem procurá-lo no mapa.

## 2 · Condições de pronto
- [ ] Resolver um endereço por interpolação desenha o ponto **e abre a gaveta lateral do endereço**:
      logradouro, número, codlog-DV, **grau de certeza** do logradouro (quando veio de fuzzy) e a
      **faixa de numeração** do segmento que originou o ponto.
- [ ] A gaveta do endereço traz o botão **"Buscar lote mais próximo"**, que funciona **sem login**.
- [ ] Acionar o botão faz **uma** consulta ao WFS e desenha o lote encontrado **junto do ponto**, e a
      gaveta passa a ser a gaveta do lote da SPEC [localizacao_lote/001](001-dados-do-lote-na-gaveta.md).
- [ ] A gaveta do lote, **e só quando ele veio desta busca**, abre com a **distância em metros** até o
      ponto que originou a consulta e o **endereço de origem**. Lote resolvido por SQL, contribuinte
      ou endereço cadastrado segue com a gaveta de hoje, sem o card.
- [ ] O lote devolvido é, entre os lotes **do mesmo codlog** a até o raio configurado do ponto, o de
      **menor distância** — lote mais perto de outro logradouro nunca é escolhido.
- [ ] Sem lote do mesmo codlog dentro do raio, a resposta diz isso em português, com o raio usado, e
      o ponto continua no mapa.
- [ ] O design da gaveta do endereço **e do card de distância** foi aprovado no mock e as peças novas
      portadas para o tema e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
O ponto interpolado é o do [AddressGeocoder](../geocodificacao/003-address-geocod-ponto.md); a
pergunta que esta SPEC faz a ele é "de qual segmento e faixa você saiu?". O lote é o
[LoteAttributes](001-dados-do-lote-na-gaveta.md#3--domínio). A proximidade é consulta **espacial**
sobre a camada de lotes: nasce aqui o submódulo `lotes_mais_proximos`, que responde "que lotes
estão perto de / dentro de uma geometria".

A distância é a **menor distância entre o ponto e a borda do lote**, medida pelo GEOS no CRS métrico
da camada — é ela que ordena os candidatos e é ela que a gaveta exibe. Lote que contém o ponto dista
zero.

**`services/domain/address_geocod/models.py`** — `EnderecoAttributes` inteiro.

```python
class EnderecoAttributes(BaseModel):
    codlog: str
    nome_logradouro: str
    tipo_logradouro: str
    numero: int
    id_segmento: str
    # ALTERADO nesta SPEC: a faixa do lado (par/ímpar) do segmento escolhido, no dia da geocodificação.
    numeracao_inicial: int
    numeracao_final: int
    titulo: str | None = None
```

**`services/domain/lotes_mais_proximos/models.py`**

```python
class CamadaLotes(BaseModel):
    """Onde os lotes moram no GeoServer — processo, não domínio; chega pronto da orquestração."""

    model_config = ConfigDict(frozen=True)

    nome: str
    campo_geometria: str
    crs_camada: int      # CRS métrico em que distância e área fazem sentido
    crs_saida: int       # CRS do mapa


class LoteProximo(BaseModel):
    """Um lote e a distância dele ao ponto, apurada no CRS da camada."""

    lote: LoteFeature
    # Menor distância do ponto à borda do lote; zero quando o ponto cai dentro dele.
    distancia_m: float = Field(ge=0)
```

**Mock:** [002-mock-lote-mais-proximo-do-endereco.html](002-mock-lote-mais-proximo-do-endereco.html)
— leia a skill `mock`.

## 4 · Fora de escopo
- Proximidade que respeita o **lado** da rua (paridade) — sem dono ainda.
- Oferecer mais de um lote próximo para escolha — sem dono ainda.
- Lote mais próximo de um ponto **desenhado** pelo usuário — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/address_geocod` → `AddressGeocoder`, `limite_inicial`/`limite_final`: o segmento e a faixa.
- `@services/domain/lote_geocod/geocoder.py` → `_feature_para_lote`: a conversão da feature, promovida a função do módulo.
- `@services/integrations/wfs` → `WfsFeatureRequest`, `CqlFilter`, `CqlPredicate`, `build_fetcher`.
- `@apps/address_geocoder/views.py` → `geocodificar_endereco`: ponto único da sugestão e do Enter.
- `@templates/lote_geocoder/partials/_gaveta_lote.html` → a gaveta do lote (SPEC 001); ganha o card
  condicional de distância, com aval do usuário (§3.4).
- `@apps/mapping/context.py` → `contexto_mapa`, `contexto_aviso`.
- Skills: `wfs-fetcher`, `mock`, `componentes-frontend`, `test-django-views`.
- `WFS_LOTE_CIDADAO_CAMPO_GEOMETRIA` (nova, default `ge_poligono` — confirmado via
  `DescribeFeatureType` da camada real) e `LOTE_MAIS_PROXIMO_RAIO_M` (default `50.0`): lidas só por
  `apps/lotes_mais_proximos/contexto.py:camada_lotes()`, no mesmo padrão de `WFS_LAYER_LOTE_CIDADAO`.
  `crs_camada` reusa `MAP_INTERPOLATION_CRS` (31983) — nenhum CRS métrico novo.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/integrations/wfs/models.py`** — o predicado espacial tipado; `raw_cql` segue sendo
exceção.

```python
# WKT gerado pelo GEOS no domínio: o padrão é só uma cerca contra texto que não é geometria.
PADRAO_WKT = r"^(POINT|POLYGON|MULTIPOLYGON)\s*\([-0-9.,\s()]+\)$"


class CqlDWithin(BaseModel):
    field: str
    wkt: str = Field(pattern=PADRAO_WKT)
    distancia_m: float = Field(gt=0)

    def to_cql(self) -> str:
        return f"DWITHIN({self.field}, {self.wkt}, {self.distancia_m}, meters)"


class CqlFilter(BaseModel):
    predicates: list[CqlPredicate | CqlDWithin] = Field(default_factory=list)  # ALTERADO
    logic: Literal["AND", "OR"] = "AND"
    raw_cql: str | None = None
```

**`services/domain/geometry/reprojecao.py`** — a reprojeção centralizada, que as SPECs seguintes reusam.

```python
def reprojetar[G: (PointGeometry, PolygonGeometry)](geometria: G, origem: int, destino: int) -> G:
    geos = GEOSGeometry(json.dumps(geometria.model_dump()), srid=origem)
    geos.transform(destino)
    return type(geometria).model_validate_json(geos.geojson)
```

**`services/domain/lotes_mais_proximos/exceptions.py`**

```python
class NenhumLoteProximoError(Exception):
    """Nenhum lote do codlog informado dentro do raio consultado."""
```

**`services/domain/lotes_mais_proximos/mais_proximo.py`**

```python
class LoteMaisProximoInput(BaseModel):
    ponto: PointGeometry            # no CRS de saída (o do mapa)
    codlog: str = Field(pattern=r"^\d{6}$")   # codlog + DV, como a camada grava cd_logradouro
    raio_m: float = Field(gt=0)
    camada: CamadaLotes


class LoteMaisProximo:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, entrada: LoteMaisProximoInput) -> LoteProximo:
        return self.pipeline(entrada)

    def pipeline(self, entrada: LoteMaisProximoInput) -> LoteProximo:
        ponto = reprojetar(entrada.ponto, entrada.camada.crs_saida, entrada.camada.crs_camada)
        candidatos = self._candidatos(self._montar_request(ponto, entrada), ponto)
        if not candidatos:
            raise NenhumLoteProximoError(entrada.codlog, entrada.raio_m)
        # Menor distância; o codlog já filtrou no servidor, então nenhum vizinho de outra rua chega aqui.
        escolhido = min(candidatos, key=lambda c: c.distancia_m)
        return self._para_saida(escolhido, entrada.camada)

    def _montar_request(self, ponto: PointGeometry, entrada: LoteMaisProximoInput) -> WfsFeatureRequest:
        return WfsFeatureRequest(
            nome_camada=entrada.camada.nome,
            srs_name=f"EPSG:{entrada.camada.crs_camada}",
            cql_filter=CqlFilter(
                logic="AND",
                predicates=[
                    CqlDWithin(
                        field=entrada.camada.campo_geometria,
                        wkt=_wkt(ponto),
                        distancia_m=entrada.raio_m,
                    ),
                    CqlPredicate(field="cd_logradouro", op="=", value=entrada.codlog),
                ],
            ),
        )

    def _candidatos(self, request: WfsFeatureRequest, ponto: PointGeometry) -> list[LoteProximo]:
        # Distância medida no GEOS, no CRS métrico: o servidor só garante "dentro do raio".
        ...

    def _para_saida(self, escolhido: LoteProximo, camada: CamadaLotes) -> LoteProximo:
        # Reprojeta o polígono vencedor, e só ele, para o CRS do mapa.
        ...
```

**`config/settings.py`** — o raio é operacional: calibra-se no ambiente, não no código.

```python
    lote_mais_proximo_raio_m: float = Field(default=50.0, alias="LOTE_MAIS_PROXIMO_RAIO_M")
```

```python
LOTE_MAIS_PROXIMO_RAIO_M = _env.lote_mais_proximo_raio_m
```

**`apps/lotes_mais_proximos/views.py`** — rota aberta; o ponto e o codlog viajam no formulário da gaveta.

```python
LOTE_MAIS_PROXIMO_RAIO_M: float = settings.LOTE_MAIS_PROXIMO_RAIO_M

# O raio sai da mesma constante que alimentou a consulta; a exceção não precisa carregá-lo de volta.
MSG_SEM_LOTE_PROXIMO = (
    "Nenhum lote situado neste logradouro foi encontrado "
    "a {raio_m:.0f} metros do ponto de busca."
)


class ConsultaLoteMaisProximo(BaseModel):
    """O formulário da gaveta. lon/lat malformados morrem no PydanticValidationMiddleware."""

    lon: float
    lat: float
    codlog: str
    # Rótulo do endereço de origem, só para a gaveta ler — como `score`, é apresentação.
    origem: str = ""


@require_POST
def mais_proximo(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaLoteMaisProximo.model_validate(request.POST.dict())
    entrada = LoteMaisProximoInput(
        ponto=PointGeometry(type="Point", coordinates=[consulta.lon, consulta.lat]),
        codlog=consulta.codlog,
        raio_m=LOTE_MAIS_PROXIMO_RAIO_M,
        camada=camada_lotes(),   # apps/lotes_mais_proximos/contexto.py: único ponto que lê settings
    )
    try:
        proximo = LoteMaisProximo(build_fetcher(settings))(entrada)
    except NenhumLoteProximoError:
        return render(
            request,
            "mapping/_aviso.html",
            contexto_aviso(MSG_SEM_LOTE_PROXIMO.format(raio_m=LOTE_MAIS_PROXIMO_RAIO_M)),
        )
    return render(
        request,
        TEMPLATE_RESULTADO_MAIS_PROXIMO,
        contexto_mais_proximo(entrada.ponto, proximo, consulta.origem),
    )
```

**`templates/lote_geocoder/partials/_gaveta_lote.html`** — primeiro filho de
`.gaveta-lateral-conteudo`. Sem `distancia_m` no contexto, a gaveta renderiza como hoje.

```html
{% if distancia_m is not None %}
  <div class="card-well p-4">
    <p class="text-overline mb-1">Distância do endereço</p>
    <p class="text-xl font-bold tabular-nums">
      {{ distancia_m|floatformat:0 }} <span class="text-sm font-normal text-base-content/60">m</span>
    </p>
    {% if origem_busca %}
      <p class="text-sm text-base-content/70 mt-0.5">{{ origem_busca }}</p>
    {% endif %}
  </div>
{% endif %}
```

**`templates/address_geocoder/partials/_gaveta_endereco.html`** — o botão carrega o que a consulta precisa.

```html
<form hx-post="{% url 'lotes_mais_proximos:mais_proximo' %}" hx-target="#resultado-busca" hx-swap="innerHTML">
  <input type="hidden" name="lon" value="{{ ponto.coordinates.0 }}">
  <input type="hidden" name="lat" value="{{ ponto.coordinates.1 }}">
  <input type="hidden" name="codlog" value="{{ endereco.codlog }}">
  <input type="hidden" name="origem" value="{{ endereco.nome_logradouro }}, {{ endereco.numero }}">
  <button type="submit" class="btn btn-onsen btn-sm">Buscar lote mais próximo</button>
</form>
```

**`templates/address_geocoder/partials/resultados_endereco_nome.html`** — a sugestão passa o grau de
certeza adiante; `geocodificar_endereco` ganha `score: float | None = None`, que só a gaveta lê.

```html
hx-vals='{"codlog": "{{ item.logradouro.codlog }}{{ item.logradouro.dv }}", "numero": "{{ numero }}"{% if item.score is not None %}, "score": "{{ item.score }}"{% endif %}}'
```

## 7 · Caveats
O ponto e o codlog que alimentam a consulta chegam do formulário da gaveta, não são recalculados no
servidor. A consulta é pública e só lê a camada de lotes, e recalcular custaria uma segunda ida ao
WFS de segmentos. O custo é que um POST forjado consulta qualquer ponto e codlog, e isso é o mesmo
que a busca já permite.

O grau de certeza exibido chega na requisição da sugestão (`score`), como a lista de sugestões já o
mostra. Ele é apresentação, e nenhuma regra o lê. O custo é que o valor na gaveta não é
revalidado contra o matcher.

O raio (`LOTE_MAIS_PROXIMO_RAIO_M` no `.env`, 50 m por padrão) é um corte fixo. O ponto interpolado cai no eixo
da via, e o lote certo pode estar mais longe que isso em quadras grandes. O custo é responder "sem
lote" em casos em que o lote existe, até alguém calibrar o raio no ambiente.

O card de distância é a única alteração numa peça já implementada (a gaveta da SPEC 001), aprovada
pelo usuário em 17/09/2026. Ele é condicional: as demais rotas que renderizam a gaveta não passam
`distancia_m` e seguem idênticas. O custo é que a gaveta do lote passa a exibir um dado que não é
atributo do lote, e sim da consulta que chegou até ele.

Esta SPEC **substitui** o comportamento da SPEC 001 no resultado de endereço: onde antes o partial
tirava a gaveta de cena (`_sem_gaveta_oob.html`), agora ele abre a gaveta do endereço. O teste
`test_resultado_de_endereco_tira_a_gaveta` (tests/apps/address_geocoder/test_views.py) foi
substituído por `test_endereco_interpolado_abre_gaveta_com_faixa_e_botao`, refletindo a nova regra.

O snippet de `reprojetar` em `services/domain/geometry/reprojecao.py` foi implementado passando
`srid` como **atributo**, não no construtor do `GEOSGeometry` (`geos.srid = origem` após
desserializar, antes do `transform`) — igual ao padrão já usado em
`address_geocod/orientacao.py`. Passar `srid=origem` direto no construtor, como o snippet original
mostrava, levanta `GEOSException` sempre que `origem != 4326` (o `GEOSGeometry` lê GeoJSON como
SRID 4326 por padrão e rejeita um `srid` explícito divergente) — e é exatamente o caso de
`_para_saida` (31983 → 4326). Pinado por `test_reprojetar_de_crs_metrico_para_4326_nao_levanta` em
`tests/services/domain/geometry/test_reprojecao.py`.

`lotes_mais_proximos` passa a conhecer `lote_geocod`, porque converte a feature pela mesma função.
Duas conversões divergiriam no primeiro atributo novo. O custo é um submódulo depender do outro.

## 8 · Testes (TDD)
- `test_dwithin_monta_cql` — `CqlDWithin` gera `DWITHIN(campo, POINT(x y), r, meters)` dentro do `AND`.
- `test_dwithin_recusa_texto_que_nao_e_wkt` — WKT com aspas ou `;` é recusado na construção.
- `test_mais_proximo_consulta_no_crs_da_camada_e_filtra_codlog` — o request capturado pelo fetcher
  fake pede `EPSG:31983`, o ponto em coordenadas UTM e `cd_logradouro` igual ao codlog.
- `test_mais_proximo_escolhe_menor_distancia` — de dois lotes devolvidos, vence o mais perto do ponto.
- `test_sem_lote_no_raio_levanta_erro_proprio` — página vazia levanta `NenhumLoteProximoError`.
- `test_lote_devolvido_no_crs_do_mapa` — o polígono escolhido sai em 4326.
- `test_endereco_interpolado_abre_gaveta_com_faixa_e_botao` — o partial do ponto traz a gaveta com
  a faixa de numeração, o grau de certeza e o formulário para `lotes_mais_proximos:mais_proximo`.
- `test_mais_proximo_anonimo_devolve_ponto_lote_e_gaveta_do_lote` — POST sem login devolve payload
  com as duas features e o OOB da gaveta do lote, e a gaveta traz a distância em metros e o
  endereço de origem.
- `test_gaveta_do_lote_sem_distancia_nao_mostra_o_card` — a rota da SPEC 001 (lote por SQL) segue
  renderizando a gaveta sem o card, para que o condicional não vaze nas outras buscas.
- `test_mais_proximo_sem_lote_responde_aviso_com_raio` — o aviso renderizado traz
  `MSG_SEM_LOTE_PROXIMO` com o raio do ambiente por extenso ("a 50 metros do ponto de busca").
- `test_lote_mais_proximo_no_geosampa` — ponto real de endereço conhecido devolve lote do mesmo
  codlog *(marker `integration`)*.
