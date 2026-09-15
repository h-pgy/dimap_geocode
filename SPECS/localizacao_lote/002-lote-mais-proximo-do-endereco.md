---
spec: localizacao_lote/002
versao: v1
atualizado_em: 2026-09-15
testes_tdd: false
implementado: false
markers_obrigatorios: [integration]
changelog:
  - v1: versão inicial
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
- [ ] O lote devolvido é, entre os lotes **do mesmo codlog** a até o raio configurado do ponto, o de
      **menor distância** — lote mais perto de outro logradouro nunca é escolhido.
- [ ] Sem lote do mesmo codlog dentro do raio, a resposta diz isso em português, com o raio usado, e
      o ponto continua no mapa.
- [ ] O design da gaveta do endereço foi aprovado no mock e as peças novas portadas para o tema e o
      styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
O ponto interpolado é o do [AddressGeocoder](../geocodificacao/003-address-geocod-ponto.md); a
pergunta que esta SPEC faz a ele é "de qual segmento e faixa você saiu?". O lote é o
[LoteAttributes](001-dados-do-lote-na-gaveta.md#3--domínio). A proximidade é consulta **espacial**
sobre a camada de lotes: nasce aqui o submódulo `lote_espacial`, que responde "que lotes estão
perto de / dentro de uma geometria".

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

**`services/domain/lote_espacial/models.py`**

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
    distancia_m: float = Field(ge=0)
```

## 4 · Fora de escopo
- Proximidade que respeita o **lado** da rua (paridade) — sem dono ainda.
- Oferecer mais de um lote próximo para escolha — sem dono ainda.
- Lote mais próximo de um ponto **desenhado** pelo usuário — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/address_geocod` → `AddressGeocoder`, `limite_inicial`/`limite_final`: o segmento e a faixa.
- `@services/domain/lote_geocod/geocoder.py` → `_feature_para_lote`: a conversão da feature, promovida a função do módulo.
- `@services/integrations/wfs` → `WfsFeatureRequest`, `CqlFilter`, `CqlPredicate`, `build_fetcher`.
- `@apps/address_geocoder/views.py` → `geocodificar_endereco`: ponto único da sugestão e do Enter.
- `@templates/lote_geocoder/partials/_gaveta_lote.html` → a gaveta do lote (SPEC 001).
- `@apps/mapping/context.py` → `contexto_mapa`, `contexto_aviso`.
- Skills: `wfs-fetcher`, `mock`, `componentes-frontend`, `test-django-views`.

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

**`services/domain/lote_espacial/mais_proximo.py`**

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

**`apps/lote_espacial/views.py`** — rota aberta; o ponto e o codlog viajam no formulário da gaveta.

```python
LOTE_MAIS_PROXIMO_RAIO_M: float = settings.LOTE_MAIS_PROXIMO_RAIO_M


class ConsultaLoteMaisProximo(BaseModel):
    """O formulário da gaveta. lon/lat malformados morrem no PydanticValidationMiddleware."""

    lon: float
    lat: float
    codlog: str


@require_POST
def mais_proximo(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaLoteMaisProximo.model_validate(request.POST.dict())
    entrada = LoteMaisProximoInput(
        ponto=PointGeometry(type="Point", coordinates=[consulta.lon, consulta.lat]),
        codlog=consulta.codlog,
        raio_m=LOTE_MAIS_PROXIMO_RAIO_M,
        camada=camada_lotes(),   # apps/lote_espacial/contexto.py: único ponto que lê settings
    )
    try:
        proximo = LoteMaisProximo(build_fetcher(settings))(entrada)
    except NenhumLoteProximoError as erro:
        return render(request, "mapping/_aviso.html", contexto_aviso(mensagem_sem_lote(erro)))
    return render(request, TEMPLATE_RESULTADO_MAIS_PROXIMO, contexto_mais_proximo(entrada.ponto, proximo))
```

**`templates/address_geocoder/partials/_gaveta_endereco.html`** — o botão carrega o que a consulta precisa.

```html
<form hx-post="{% url 'lote_espacial:mais_proximo' %}" hx-target="#resultado-busca" hx-swap="innerHTML">
  <input type="hidden" name="lon" value="{{ ponto.coordinates.0 }}">
  <input type="hidden" name="lat" value="{{ ponto.coordinates.1 }}">
  <input type="hidden" name="codlog" value="{{ endereco.codlog }}">
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

O raio (`LOTE_MAIS_PROXIMO_RAIO_M`, 50 m por padrão) é um corte fixo. O ponto interpolado cai no eixo
da via, e o lote certo pode estar mais longe que isso em quadras grandes. O custo é responder "sem
lote" em casos em que o lote existe, até alguém calibrar o raio no ambiente.

`lote_espacial` passa a conhecer `lote_geocod`, porque converte a feature pela mesma função. Duas
conversões divergiriam no primeiro atributo novo. O custo é um submódulo depender do outro.

## 8 · Testes (TDD)
- `test_dwithin_monta_cql` — `CqlDWithin` gera `DWITHIN(campo, POINT(x y), r, meters)` dentro do `AND`.
- `test_dwithin_recusa_texto_que_nao_e_wkt` — WKT com aspas ou `;` é recusado na construção.
- `test_mais_proximo_consulta_no_crs_da_camada_e_filtra_codlog` — o request capturado pelo fetcher
  fake pede `EPSG:31983`, o ponto em coordenadas UTM e `cd_logradouro` igual ao codlog.
- `test_mais_proximo_escolhe_menor_distancia` — de dois lotes devolvidos, vence o mais perto do ponto.
- `test_sem_lote_no_raio_levanta_erro_proprio` — página vazia levanta `NenhumLoteProximoError`.
- `test_lote_devolvido_no_crs_do_mapa` — o polígono escolhido sai em 4326.
- `test_endereco_interpolado_abre_gaveta_com_faixa_e_botao` — o partial do ponto traz a gaveta com
  a faixa de numeração, o grau de certeza e o formulário para `lote_espacial:mais_proximo`.
- `test_mais_proximo_anonimo_devolve_ponto_lote_e_gaveta_do_lote` — POST sem login devolve payload
  com as duas features e o OOB da gaveta do lote.
- `test_mais_proximo_sem_lote_responde_aviso_com_raio` — a mensagem cita o raio.
- `test_lote_mais_proximo_no_geosampa` — ponto real de endereço conhecido devolve lote do mesmo
  codlog *(marker `integration`)*.
