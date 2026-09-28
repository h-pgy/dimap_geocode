---
spec: geocodificacao_externa/003
versao: v1
atualizado_em: 2026-09-27
testes_tdd: false
implementado: false
markers_obrigatorios: [integration]
changelog:
  - v1: versão inicial
---

# SPEC geocodificacao_externa/003 — Endereço externo no mapa, na gaveta e no lote mais próximo

## 1 · User story
O servidor logado na plataforma geocodifica um endereço pelo provedor externo, no contexto de um
logradouro que a base oficial não resolve, para ver o ponto no mapa com o provedor e a precisão
declarados e chegar ao lote mais próximo dele.

## 2 · Condições de pronto
- [ ] Geocodificar um endereço pelo provedor externo desenha o **ponto** e abre a **gaveta do endereço
      externo**: o endereço como o provedor o escreve, o **provedor**, a **precisão** e, quando houver,
      o aviso de **correspondência parcial**.
- [ ] A geocodificação externa **exige login**: sem ele, a rota leva ao login e o provedor não é
      chamado.
- [ ] A gaveta traz **"Buscar lote mais próximo"**.
- [ ] Acioná-lo desenha, junto do ponto, o lote de **menor distância** a até o raio configurado,
      **de qualquer logradouro**, e abre a gaveta do lote com a **distância** e o **endereço de origem**.
- [ ] Sem lote no raio, a resposta diz isso em português com o raio usado, sem falar em logradouro, e o
      ponto continua no mapa.
- [ ] Sem resultado aceito pela política, ou com o provedor indisponível, a resposta é um aviso em
      português que diz **qual dos dois** aconteceu, e nada é desenhado.
- [ ] Sem geocodificador externo configurado, a rota responde o aviso de indisponível sem tentar
      chamada.
- [ ] O design da gaveta do endereço externo foi aprovado no mock e as peças novas portadas para o tema
      e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
O endereço é o [EnderecoExternoFeature](002-geocodificador-externo-agnostico.md#3--domínio); a pergunta
que esta SPEC faz a ele é "o que você encontrou, por qual provedor e com que precisão?". O lote e a
distância são o [LoteProximo](../localizacao_lote/002-lote-mais-proximo-do-endereco.md#3--domínio) e a
[CamadaLotes](../localizacao_lote/002-lote-mais-proximo-do-endereco.md#3--domínio).

A proximidade a partir do ponto externo é uma consulta **nova** do submódulo `lotes_mais_proximos`,
ao lado do `LoteMaisProximo` e sem compartilhar código com ele: sem codlog oficial, o raio é o único
recorte, e concorre qualquer lote da camada.

**`services/domain/lotes_mais_proximos/models.py`**

```python
class LoteMaisProximoDoPontoInput(BaseModel):
    ponto: PointGeometry   # no CRS de saída (o do mapa)
    raio_m: float = Field(gt=0)
    camada: CamadaLotes
```

**Mock:** [003-mock-endereco-externo-no-mapa-e-na-gaveta.html](003-mock-endereco-externo-no-mapa-e-na-gaveta.html)
— leia a skill `mock`.

## 4 · Fora de escopo
- Entrada da geocodificação externa na busca (sugestão e Enter) — SPEC 004.
- Outras ações sobre o endereço externo além do lote mais próximo — sem dono ainda.
- Mais de um lote próximo para a pessoa escolher — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/geocodificador_externo` → `build_geocodificador_externo`, `GeocodificacaoExternaInput`, os dois erros (SPEC 002).
- `@services/domain/lote_geocod` → `feature_para_lote`: a conversão da feature de lote.
- `@services/domain/geometry` → `reprojetar`, `para_geos`, `to_geojson_feature_collection`.
- `@services/integrations/wfs` → `WfsFeatureRequest`, `CqlFilter`, `CqlDWithin`, `build_fetcher`.
- `@apps/lotes_mais_proximos/views.py` → `_contexto_mais_proximo`: ponto + lote + gaveta do lote com
  distância e origem; `camada_lotes()` em `contexto.py`.
- `@templates/lotes_mais_proximos/partials/_resultado_mais_proximo.html` → o resultado do lote com o card de distância.
- `@templates/address_geocoder/partials/_gaveta_endereco.html` → a gaveta do endereço interpolado, molde da nova.
- `@apps/mapping/context.py` → `contexto_mapa`, `contexto_aviso`.
- Skills: `mock`, `componentes-frontend`, `leaflet-map`, `wfs-fetcher`, `test-django-views`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/lotes_mais_proximos/exceptions.py`**

```python
class NenhumLoteNoRaioError(Exception):
    """Nenhum lote da camada dentro do raio consultado."""
```

**`services/domain/lotes_mais_proximos/mais_proximo_do_ponto.py`**

```python
class LoteMaisProximoDoPonto:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, entrada: LoteMaisProximoDoPontoInput) -> LoteProximo:
        return self.pipeline(entrada)

    def pipeline(self, entrada: LoteMaisProximoDoPontoInput) -> LoteProximo:
        camada = entrada.camada
        ponto = para_geos(reprojetar(entrada.ponto, camada.crs_saida, camada.crs_camada), camada.crs_camada)
        candidatos = self._candidatos(self._montar_request(ponto, entrada), ponto, camada.crs_camada)
        if not candidatos:
            raise NenhumLoteNoRaioError(entrada.raio_m)
        escolhido = min(candidatos, key=lambda c: c.distancia_m)
        return self._para_saida(escolhido, camada)

    def _montar_request(self, ponto: GEOSGeometry, entrada: LoteMaisProximoDoPontoInput) -> WfsFeatureRequest:
        # só o raio: sem codlog oficial, qualquer lote perto do ponto concorre
        return WfsFeatureRequest(
            nome_camada=entrada.camada.nome,
            srs_name=f"EPSG:{entrada.camada.crs_camada}",
            cql_filter=CqlFilter(
                predicates=[
                    CqlDWithin(
                        field=entrada.camada.campo_geometria,
                        wkt=f"POINT({ponto.x} {ponto.y})",
                        distancia_m=entrada.raio_m,
                    ),
                ],
            ),
        )

    def _candidatos(self, request: WfsFeatureRequest, ponto: GEOSGeometry, crs: int) -> list[LoteProximo]:
        # distância medida no GEOS, no CRS métrico: o servidor só garante "dentro do raio"
        ...

    def _para_saida(self, escolhido: LoteProximo, camada: CamadaLotes) -> LoteProximo:
        # reprojeta o polígono vencedor, e só ele, para o CRS do mapa
        ...
```

**`apps/geocodificacao_externa/views.py`** — app novo; `geocodificador_externo` e
`geocodificar_externo` são o ponto único que a busca da SPEC 004 também chama.

```python
MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
MAP_COR_PONTO: str = settings.MAP_COR_PONTO

TEMPLATE_RESULTADO_EXTERNO = "geocodificacao_externa/partials/_resultado_externo.html"

MSG_INDISPONIVEL = "O serviço externo de geocodificação está indisponível no momento."
MSG_SEM_RESULTADO = "O serviço externo não localizou este endereço com precisão suficiente."

ROTULO_PROVEDOR: dict[Provedor, str] = {Provedor.GOOGLE: "Google"}
ROTULO_PRECISAO: dict[Precisao, str] = {
    Precisao.IMOVEL: "No imóvel",
    Precisao.INTERPOLADA: "Interpolada na via",
    Precisao.LOGRADOURO: "Centro da via",
    Precisao.APROXIMADA: "Aproximada",
}


class SelecaoGeocodificacaoExterna(BaseModel):
    texto: str


def geocodificador_externo() -> GeocodificadorExterno | None:
    # None = provedor não configurado (sem token no ambiente)
    return build_geocodificador_externo(settings)


def geocodificar_externo(
    request: HttpRequest,
    geocodificador: GeocodificadorExterno,
    texto: str,
) -> HttpResponse:
    entrada = GeocodificacaoExternaInput(
        consulta=ConsultaGeocodificacao(texto=texto),
        output_crs=MAP_OUTPUT_CRS,
    )
    try:
        endereco = geocodificador(entrada)
    except ProvedorIndisponivelError:
        return render(request, "mapping/_aviso.html", contexto_aviso(MSG_INDISPONIVEL))
    except SemResultadoAceitoError:
        return render(request, "mapping/_aviso.html", contexto_aviso(MSG_SEM_RESULTADO))
    return render(request, TEMPLATE_RESULTADO_EXTERNO, _contexto_externo(endereco))


def _contexto_externo(endereco: EnderecoExternoFeature) -> dict[str, Any]:
    geojson = to_geojson_feature_collection(
        [endereco],
        lambda f: GeoJsonProperties(rotulo=f.attributes.endereco_formatado),
    )
    a = endereco.attributes
    return contexto_mapa(geojson, MAP_COR_PONTO) | {
        "endereco": a,
        "ponto": endereco.geometry,
        "provedor": ROTULO_PROVEDOR[a.provedor],
        "precisao": ROTULO_PRECISAO[a.precisao],
    }


@login_required  # a cota do provedor é paga: basta estar autenticado, sem contrato de ação
@require_POST
def selecionar(request: HttpRequest) -> HttpResponse:
    selecao = SelecaoGeocodificacaoExterna.model_validate(request.POST.dict())
    geocodificador = geocodificador_externo()
    if geocodificador is None:
        return render(request, "mapping/_aviso.html", contexto_aviso(MSG_INDISPONIVEL))
    return geocodificar_externo(request, geocodificador, selecao.texto)
```

**`templates/geocodificacao_externa/partials/_gaveta_endereco_externo.html`** — o botão leva o ponto e
o rótulo de origem; nada de codlog.

```html
<form hx-post="{% url 'lotes_mais_proximos:mais_proximo_do_ponto' %}" hx-target="#resultado-busca" hx-swap="innerHTML">
  <input type="hidden" name="lon" value="{{ ponto.coordinates.0|unlocalize }}">
  <input type="hidden" name="lat" value="{{ ponto.coordinates.1|unlocalize }}">
  <input type="hidden" name="origem" value="{{ endereco.endereco_formatado }}">
  <button type="submit" class="btn btn-onsen w-full">Buscar lote mais próximo</button>
</form>
```

**`apps/lotes_mais_proximos/views.py`** — rota aberta, irmã de `mais_proximo`, sem codlog.

```python
LOTE_MAIS_PROXIMO_DO_PONTO_RAIO_M: float = settings.LOTE_MAIS_PROXIMO_DO_PONTO_RAIO_M

MSG_SEM_LOTE_NO_RAIO = "Nenhum lote foi encontrado a {raio_m:.0f} metros do ponto de busca."


class ConsultaLoteMaisProximoDoPonto(BaseModel):
    lon: float
    lat: float
    origem: str = ""  # rótulo do endereço de origem, só para a gaveta ler


@require_POST
def mais_proximo_do_ponto(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaLoteMaisProximoDoPonto.model_validate(request.POST.dict())
    entrada = LoteMaisProximoDoPontoInput(
        ponto=PointGeometry(type="Point", coordinates=[consulta.lon, consulta.lat]),
        raio_m=LOTE_MAIS_PROXIMO_DO_PONTO_RAIO_M,
        camada=camada_lotes(),
    )
    try:
        proximo = LoteMaisProximoDoPonto(build_fetcher(settings))(entrada)
    except NenhumLoteNoRaioError:
        mensagem = MSG_SEM_LOTE_NO_RAIO.format(raio_m=LOTE_MAIS_PROXIMO_DO_PONTO_RAIO_M)
        return render(request, TEMPLATE_AVISO, contexto_aviso(mensagem))
    return render(
        request,
        TEMPLATE_RESULTADO_MAIS_PROXIMO,
        _contexto_mais_proximo(entrada.ponto, proximo, consulta.origem),
    )
```

**`config/settings.py`**

```python
    lote_mais_proximo_do_ponto_raio_m: float = Field(
        default=50.0, alias="LOTE_MAIS_PROXIMO_DO_PONTO_RAIO_M"
    )
```

## 7 · Caveats
A geocodificação externa exige só login (`@login_required`), sem contrato de ação, perfil nem
registro de execução. O que se protege é a cota paga do provedor, não uma competência administrativa
(§3.5). O custo é não saber quem consumiu a cota, nem limitar quanto cada um consome.

O lote mais próximo do ponto continua rota aberta, embora só seja alcançável pela gaveta de quem está
logado. Ele só lê a camada pública de lotes do GeoSampa e não gasta cota. O custo é uma rota aberta que
a interface só oferece a quem está logado.

`LoteMaisProximoDoPonto` é uma classe nova ao lado de `LoteMaisProximo`, sem parametrizar a existente.
A busca oficial filtra pelo logradouro e esta não: são consultas de natureza diferente e devem poder
evoluir separadas. O custo é que a consulta DWITHIN, a medição de distância e a reprojeção existem
em duas classes e podem divergir.

O raio tem variável própria (`LOTE_MAIS_PROXIMO_DO_PONTO_RAIO_M`, 50 m por padrão). Sem logradouro, o
raio é o único recorte e se calibra à parte do da busca oficial. O custo é que, numa esquina, o lote
de outra rua pode ser o mais próximo e vencer.

O ponto e a origem chegam do formulário da gaveta, sem recálculo no servidor, como na busca oficial.
Recalcular exigiria uma segunda chamada paga ao provedor. O custo é que um POST forjado consulta
lotes em qualquer ponto, o que a camada de lotes já permite de todo modo.

## 8 · Testes (TDD)
Salvo quando o teste diz o contrário, o cliente dos testes de view está logado.

- `test_mais_proximo_do_ponto_consulta_so_pelo_raio` — o request capturado pelo fetcher dublê pede
  `EPSG:31983`, o ponto em UTM e só o `DWITHIN`, sem `cd_logradouro`.
- `test_mais_proximo_do_ponto_escolhe_menor_distancia` — de dois lotes devolvidos, vence o mais perto.
- `test_mais_proximo_do_ponto_sem_lote_levanta_erro_proprio` — página vazia levanta
  `NenhumLoteNoRaioError`.
- `test_geocodificar_externo_desenha_ponto_e_abre_gaveta` — com geocodificador dublê: o partial traz o
  payload do ponto e o OOB da gaveta com endereço formatado, "Google", o rótulo da precisão e o
  formulário para `mais_proximo_do_ponto` com lon, lat e origem.
- `test_geocodificar_externo_com_falha_responde_aviso_que_diz_qual` — parametrizado:
  `SemResultadoAceitoError` vira `MSG_SEM_RESULTADO` e `ProvedorIndisponivelError` vira
  `MSG_INDISPONIVEL`, os dois sem payload de mapa.
- `test_selecionar_anonimo_vai_para_o_login_sem_chamar_o_provedor` — POST sem login é redirecionado ao
  login, e o geocodificador dublê não é chamado.
- `test_selecionar_sem_configuracao_responde_indisponivel` — factory devolvendo `None` faz o POST de
  `selecionar` responder `MSG_INDISPONIVEL`.
- `test_mais_proximo_do_ponto_anonimo_devolve_ponto_lote_e_gaveta_do_lote` — POST sem login devolve as
  duas features e o OOB da gaveta do lote com a distância e o endereço de origem.
- `test_mais_proximo_do_ponto_sem_lote_responde_aviso_com_raio` — o aviso traz "a 50 metros do ponto de
  busca" e não menciona logradouro.
- `test_lote_mais_proximo_do_ponto_no_geosampa` — ponto real conhecido devolve um lote
  *(marker `integration`)*.
