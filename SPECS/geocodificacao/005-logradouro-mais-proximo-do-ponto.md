---
spec: geocodificacao/005
versao: v5
atualizado_em: 2026-10-09
testes_tdd: true
implementado: true
markers_obrigatorios: [integration]
changelog:
  - v1: versão inicial
  - v2: a SPEC do endereço mais próximo do ponto passa a ser a geocodificacao/007
  - v3: a resposta passa a abrir a gaveta do logradouro em vez de esvaziar a gaveta lateral (SPEC geocodificacao/006)
  - v4: o endereço mais próximo do ponto é renumerado para geocodificacao/008
  - v5: com a gaveta inferior aberta ou recolhida, a consulta deixa de responder, e o `ConsultaSobrePonto` passa a `apps/mapping/models` (SPEC design/021)
---

# SPEC geocodificacao/005 — Logradouro mais próximo de um ponto desenhado

## 1 · User story
Quem usa o mapa marca um ponto desenhado e pede o logradouro mais próximo dele, no contexto de um
local que conhece só pela posição no mapa, para saber em que logradouro oficial ele está.

## 2 · Condições de pronto
- [ ] Com um **ponto selecionado** na gaveta dos desenhos, o poço de pontos traz a ação **"Logradouro
      mais próximo"**, inclusive para quem não fez login; sem seleção, ou com uma linha ou um polígono
      selecionados, ela não aparece em poço algum.
- [ ] Acionar a ação desenha no mapa a **linha do logradouro inteiro** — todos os segmentos do codlog
      —, como a busca por logradouro desenha, com o nome e o codlog no pop-up de cada segmento, e a
      gaveta dos desenhos sai. Vale o ponto como está no mapa naquele momento, inclusive depois de
      arrastado.
- [ ] O logradouro é o do **segmento cujo eixo está mais perto** do ponto, dentro do raio configurado;
      segmento sem numeração concorre como qualquer outro.
- [ ] Sem segmento no raio, o mapa fica como estava, o aviso do mapa diz isso em português, **citando
      o raio**, e a gaveta dos desenhos recolhe para o aviso ficar à vista.
- [ ] Desenho que não é ponto é recusado sem consultar o WFS.
- [ ] O design da ação no poço de pontos e do resultado no mapa foi aprovado no mock, e o ícone foi
      gravado antes de qualquer template da aplicação usá-lo.

## 3 · Domínio
O resultado é o logradouro da [geocodificação por codlog](001-logradouro-geocod-linha.md) — os
`SegmentoLogradouroFeature` de um codlog —, a quem esta SPEC faz uma pergunta nova: "quais segmentos
estão perto deste ponto, e a que distância?". O ponto é o
[Desenho](../design/020-desenhos-na-gaveta.md#3--domínio) selecionado na bancada, e a oferta no poço é
uma [ConsultaSobreDesenho](../localizacao_lote/003-lotes-do-desenho.md#3--domínio).

**`services/domain/logradouro_geocod/models.py`**

```python
class SegmentoProximo(BaseModel):
    """Um segmento e a distância dele ao ponto, apurada no CRS métrico."""

    segmento: SegmentoLogradouroFeature   # no CRS métrico da consulta
    distancia_m: float = Field(ge=0)      # do ponto ao eixo; zero quando o ponto está sobre ele
```

**Mock:** [005-mock-logradouro-mais-proximo-do-ponto.html](005-mock-logradouro-mais-proximo-do-ponto.html)
— leia a skill `mock`.

## 4 · Fora de escopo
- O número do endereço naquele segmento — SPEC [geocodificacao/007](007-endereco-mais-proximo-do-ponto.md).
- Mostrar a distância entre o ponto desenhado e o logradouro — sem dono ainda.
- Gaveta lateral do logradouro, com os dados dele — sem dono ainda.
- Logradouro mais próximo a partir de linha ou de polígono — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/geometry` → `reprojetar`, `para_geos`: o ponto e o segmento como GEOS, no CRS métrico.
- `@services/integrations/wfs` → `CqlDWithin`, `CqlFilter`, `WfsFeatureRequest`, `build_fetcher`: a consulta por raio.
- `@services/domain/lotes_mais_proximos/mais_proximo_do_ponto.py` → `LoteMaisProximoDoPonto`: molde da consulta por raio com a distância medida no GEOS.
- `@apps/logradouro_geocoder/views.py` → `geocodificar_codlog`: a resposta do logradouro — a linha no mapa e o pop-up.
- `@apps/mapping` → `ConsultaSobreDesenho`, `REGISTRO_DESENHO`, `contexto_aviso`, `_recusa_acao.html`: a oferta no poço e a recusa.
- `@static/src/js/mapa/desenho/envio.js` → `inicializarEnvio`: enxerta no envio a geometria atual do ponto marcado.
- Skills: `acao-sobre-desenho`, `wfs-fetcher`, `painel`, `escrever-testes`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`config/settings.py`**

```python
wfs_logradouros_campo_geometria: str = Field(
    default="ge_linha", alias="WFS_LOGRADOUROS_CAMPO_GEOMETRIA"
)
# ALTERADO: um raio só para toda consulta de "mais próximo". Substitui LOTE_MAIS_PROXIMO_RAIO_M e
# LOTE_MAIS_PROXIMO_DO_PONTO_RAIO_M, que deixam de existir — aqui e no .env.example.
mais_proximo_raio_limite_m: float = Field(default=50.0, alias="MAIS_PROXIMO_RAIO_LIMITE_M")
```

Passam a ler `MAIS_PROXIMO_RAIO_LIMITE_M` os três consumidores dos raios antigos —
`apps/lotes_mais_proximos/views.py`, `apps/address_geocoder/views.py` e
`apps/geocodificacao_externa/views.py` —, sem mudança de regra.

**`services/domain/logradouro_geocod/geocoder.py`** — a conversão da feição sai do método e vira
função de módulo, exposta no `__init__`, como o `feature_para_lote`; o `LogradouroGeocoder` passa a
chamá-la.

```python
def feature_para_segmento(feature: WfsFeature, output_crs: int) -> SegmentoLogradouroFeature | None:
    ...   # ALTERADO: o corpo de LogradouroGeocoder._feature_para_segmento, sem mudança de regra
```

**`services/domain/logradouro_geocod/no_raio.py`** — a peça que a SPEC 007 reaproveita: ela devolve
todos os segmentos do raio, em ordem, e cada consumidor escolhe o seu.

```python
class SegmentosNoRaioInput(BaseModel):
    ponto: PointGeometry
    crs_ponto: int              # o CRS em que o ponto chega (o do mapa)
    raio_m: float = Field(gt=0)
    layer_name: str
    campo_geometria: str
    crs_metrico: int            # o CRS da camada: é nele que raio e distância são metros


class SegmentosNoRaio:
    """Os segmentos de logradouro a até `raio_m` do ponto, do mais perto ao mais longe."""

    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, entrada: SegmentosNoRaioInput) -> tuple[SegmentoProximo, ...]:
        return self.pipeline(entrada)

    def pipeline(self, entrada: SegmentosNoRaioInput) -> tuple[SegmentoProximo, ...]:
        ponto_metrico = reprojetar(entrada.ponto, entrada.crs_ponto, entrada.crs_metrico)
        ponto = para_geos(ponto_metrico, entrada.crs_metrico)
        request = self._montar_request(ponto, entrada)
        proximos = self._medir(request, ponto, entrada.crs_metrico)
        return tuple(sorted(proximos, key=lambda proximo: proximo.distancia_m))

    def _montar_request(self, ponto: GEOSGeometry, entrada: SegmentosNoRaioInput) -> WfsFeatureRequest:
        return WfsFeatureRequest(
            nome_camada=entrada.layer_name,
            # Os segmentos saem no CRS métrico: é nele que a distância é medida, e a SPEC 007 interpola.
            srs_name=f"EPSG:{entrada.crs_metrico}",
            cql_filter=CqlFilter(
                predicates=[
                    CqlDWithin(
                        field=entrada.campo_geometria,
                        wkt=f"POINT({ponto.x} {ponto.y})",
                        distancia_m=entrada.raio_m,
                    ),
                ],
            ),
        )

    def _medir(
        self,
        request: WfsFeatureRequest,
        ponto: GEOSGeometry,
        crs_metrico: int,
    ) -> list[SegmentoProximo]:
        proximos: list[SegmentoProximo] = []
        for page in self.fetcher(request):
            for feature in page.features:
                segmento = feature_para_segmento(feature, crs_metrico)
                if segmento is None:
                    continue
                # Distância medida no GEOS: o servidor só garante "dentro do raio", não diz quanto.
                eixo = para_geos(segmento.geometry, crs_metrico)
                distancia_m = eixo.distance(ponto)
                proximos.append(SegmentoProximo(segmento=segmento, distancia_m=distancia_m))
        return proximos
```

**`apps/mapping/consultas.py`** — o que o `envio.js` entrega quando o desenho marcado é um ponto; toda
consulta sobre ponto valida o envio por aqui.

```python
class ConsultaSobrePonto(BaseModel):
    """A geometria que o envio.js enxertou. Linha e polígono viram ValidationError."""

    desenho: PointGeometry

    @field_validator("desenho", mode="before")
    @classmethod
    def _do_json(cls, valor: object) -> object:
        # Sem o envio.js o campo não chega: vira ValidationError e cai no middleware.
        return json.loads(valor) if isinstance(valor, str) else valor
```

**`apps/logradouro_mais_proximo/desenho_declarado.py`** — app novo, montado em `logradouro-mais-proximo/`.

```python
CONSULTA_LOGRADOURO_MAIS_PROXIMO = ConsultaSobreDesenho(
    slug="logradouro_mais_proximo.do_ponto",
    nome="Logradouro mais próximo",
    tooltip="Logradouro oficial cujo eixo passa mais perto do ponto marcado.",
    url_name="logradouro_mais_proximo:do_ponto",
    tipos=frozenset({TipoDesenho.PONTO}),
)
```

O ícone é `static/src/acoes/logradouro_mais_proximo/do_ponto/icones/pequeno.svg`.

**`apps/mapping/registro_desenho.py`**

```python
itens=(
    CONSULTA_LOTES_INTERSECTADOS,
    CONSULTA_LOGRADOURO_MAIS_PROXIMO,   # NOVO
),
```

**`apps/logradouro_mais_proximo/views.py`** — rota aberta: lê a camada pública de segmentos.

```python
MSG_SEM_LOGRADOURO_NO_RAIO = "Nenhum logradouro foi encontrado a {raio_m:.0f} metros do ponto."


@require_POST
def do_ponto(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaSobrePonto.model_validate(request.POST.dict())
    entrada = SegmentosNoRaioInput(
        ponto=consulta.desenho,
        crs_ponto=MAP_OUTPUT_CRS,
        raio_m=MAIS_PROXIMO_RAIO_LIMITE_M,
        layer_name=WFS_LAYER_LOGRADOUROS,
        campo_geometria=WFS_LOGRADOUROS_CAMPO_GEOMETRIA,
        crs_metrico=MAP_INTERPOLATION_CRS,
    )
    fetcher = build_fetcher(settings)
    buscar_segmentos = SegmentosNoRaio(fetcher)
    proximos = buscar_segmentos(entrada)
    if not proximos:
        mensagem = MSG_SEM_LOGRADOURO_NO_RAIO.format(raio_m=MAIS_PROXIMO_RAIO_LIMITE_M)
        return render(request, TEMPLATE_RECUSA_ACAO, contexto_aviso(mensagem))
    mais_proximo = proximos[0]   # a ordem é do domínio: do mais perto ao mais longe
    # A mesma resposta do logradouro escolhido na busca: a linha do codlog inteiro, já no CRS do mapa.
    return geocodificar_codlog(request, mais_proximo.segmento.attributes.codlog)
```

## 7 · Caveats
A consulta por raio mora em `logradouro_geocod`, e não num submódulo próprio da ação (§6.3 do
CLAUDE.md). Ela é uma segunda pergunta à mesma camada de segmentos, e a SPEC 007 a compõe a partir de
`address_geocod`, que já depende desse submódulo. O custo é o submódulo passar a ter duas portas de
entrada, por codlog e por raio.

A resposta é a do logradouro da busca, e não a base `mapping/_resultado_acao.html`. O resultado é uma
entidade só, que a busca já sabe desenhar. O custo é a linha sair na cor do logradouro e não na cor
única dos resultados de ação, o app da ação importar `geocodificar_codlog` do app de busca, e a volta à
bancada — clicar no ponto desenhado — ser JavaScript já existente, sem teste automatizado.

O logradouro não tem gaveta lateral, e a resposta enquadra o logradouro inteiro. É o que a busca por
logradouro entrega hoje. O custo é o nome só aparecer ao passar o ponteiro ou clicar na linha, e uma
avenida longa levar o mapa para longe do ponto marcado.

Cada acionamento vai duas vezes ao WFS: os segmentos no raio e, pela resposta da busca, os do codlog
escolhido. A resposta reaproveitada recebe o codlog e consulta por conta própria. O custo é o dobro de
rede por clique.

"Mais próximo" é a distância do ponto ao eixo do segmento. É a única geometria que o logradouro tem na
camada. O custo é o ponto marcado num lote de esquina poder devolver a rua transversal, e não a rua
para a qual o imóvel dá frente.

Toda consulta de "mais próximo" — lote do endereço, lote do ponto externo, logradouro e endereço do
ponto desenhado — usa um raio só, `MAIS_PROXIMO_RAIO_LIMITE_M` (50 m por padrão). Todas perguntam o que está
perto de um ponto, na escala de uma quadra. O custo é calibrar uma consulta mover as outras, o
ambiente que define `LOTE_MAIS_PROXIMO_RAIO_M` ou `LOTE_MAIS_PROXIMO_DO_PONTO_RAIO_M` ter de trocá-las
pela nova, e ponto no meio de quadra grande, parque ou represa ser recusado.

Túnel, viaduto e parque são segmentos da camada e concorrem pela distância em planta. A camada não
separa o que passa por baixo, por cima ou não é via. O custo é o ponto na calçada do MASP devolver o
túnel que passa sob ele, a 15 m, e não a Av. Paulista, que está mais longe.

## 8 · Testes (TDD)
- `test_segmentos_no_raio_consulta_pelo_raio_no_crs_metrico` — o CQL do request capturado é
  `DWITHIN(ge_linha, POINT(…), 50.0, meters)` com coordenadas UTM, e o `srsName` pedido é o métrico.
- `test_segmentos_no_raio_saem_do_mais_perto_ao_mais_longe` — três feições devolvidas fora de ordem
  viram três `SegmentoProximo` ordenados pela distância ao eixo, em metros; ponto sobre o eixo dá
  distância zero; sem feições, a tupla sai vazia.
- `test_gaveta_anonima_traz_logradouro_mais_proximo_no_poco_de_pontos` — POST anônimo com um ponto e
  uma linha, o ponto selecionado, devolve o botão com `hx-post` para `logradouro_mais_proximo:do_ponto`
  e `hx-include=".linha-desenho__marca:checked"` no poço de pontos, e o poço de linhas com a âncora
  vazia; o `test_gaveta_anonima_traz_lotes_intersectados_no_poco_de_poligonos` passa a conferir a
  âncora vazia no poço de linhas.
- `test_do_ponto_devolve_a_linha_do_logradouro_mais_proximo` — POST anônimo com `desenho` de ponto e
  dois logradouros no raio devolve o payload do mapa com os segmentos do codlog do mais próximo, na cor
  de linha, e o `#gaveta-entidade` esvaziado; a segunda consulta ao WFS filtra por esse codlog.
- `test_do_ponto_recusa_sem_logradouro_e_nao_ponto` — POST sem segmento no raio devolve o aviso com o
  raio e o toggle da gaveta dos desenhos desmarcado, sem payload de mapa; POST com `desenho` de
  polígono é recusado pela validação, sem consultar o WFS.
- `test_logradouro_mais_proximo_no_geosampa` — ponto na pista da Av. Paulista em frente ao MASP devolve
  como mais próximo um segmento do codlog 156566 (Av. Paulista) *(marker `integration`)*.
