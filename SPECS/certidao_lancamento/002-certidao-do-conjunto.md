---
spec: certidao_lancamento/002
versao: v6
atualizado_em: 2026-09-30
testes_tdd: true
implementado: false
markers_obrigatorios: [banco, artefato]
changelog:
  - v1: versão inicial
  - v2: submódulo `lote_espacial` renomeado para `lotes_mais_proximos`
  - v3: o conjunto vem da sessão e é relido no GeoSampa só na emissão, e a ação passa à gaveta inferior dos lotes intersectados
  - v4: padronização da molécula oficial de poço de ações reduzido no frontend (.card-well com respiro px-4 pt-2.5 pb-3, leading-none no título, gap-2.5 entre ações e máscara de dissolução/blur na rolagem), unificada entre a gaveta inferior e a gaveta lateral
  - v5: o poço do conjunto entra por contrato próprio no router `acoes_lote` com a molécula `.poco-acoes`, o pedido é o da SPEC 001 e o tipo de despacho vem pré-selecionado pela geometria do desenho
  - v6: o limiar da sugestão de tipo de despacho é declarado aqui, e o percentual por lote sai do fora de escopo
---

# SPEC certidao_lancamento/002 — Certidão de Existência de Lançamento de um conjunto de lotes

## 1 · User story
O auditor fiscal com a concessão emite, a partir do conjunto de lotes revisado sobre um terreno
desenhado, uma única Certidão de Existência de Lançamento para todos esses lotes, no contexto de um
imóvel que ocupa vários lotes, para obter um PDF selado que atesta o lançamento de cada um e mostra
o terreno sobre eles.

## 2 · Condições de pronto
- [ ] A gaveta inferior dos lotes intersectados traz o poço **"Ações"** ao lado da tabela só para quem
      tem a concessão; sem ação liberada, o poço não aparece e a tabela ocupa a largura toda.
- [ ] O modal do conjunto lista os lotes que restaram na tabela e pede o mesmo pedido da SPEC
      [001](001-certidao-de-um-lote.md), com as mesmas recusas, **sem consultar o GeoServer**.
- [ ] O modal abre com **deferido** e, pré-selecionado, **"em maior área"** quando o desenho contém os
      lotes que restaram — cada um com a fração mínima configurada dentro dele — ou **"parcial"**
      quando só os intersecta; o auditor pode trocar para qualquer texto, inclusive "possui lançamento".
- [ ] Na recusa 422, o modal do conjunto volta com o que o auditor marcou: o tipo que ele escolheu
      prevalece sobre a sugestão da geometria, que não é refeita.
- [ ] Conjunto **vazio**, ou com algum lote **sem lançamento ativo** ou **condominial**, abre o modal
      com o aviso — listando os lotes impeditivos, quando houver —, sem formulário, para que sejam
      tirados na tabela antes; o lote que perdeu o lançamento entre o modal e a emissão devolve esse
      mesmo aviso, e nada é emitido.
- [ ] Na emissão, os lotes do conjunto guardado são **relidos no GeoSampa**, e a certidão atesta os
      dados dessa leitura; lote que apareceu no desenho depois da consulta não entra.
- [ ] Se o conjunto relido na emissão **difere** do que o modal mostrou — lote tirado na tabela depois,
      lote que saiu da camada, id forjado no POST ou resultado substituído por outra consulta —, a
      emissão é recusada com a explicação, e nada é emitido.
- [ ] A declaração traz os dados relacionados, a área do desenho, a **tabela** com SQL, endereço e
      complemento de cada lote, o despacho do tipo escolhido no plural — "em maior área" e "parcial"
      citando o rol de contribuintes na enumeração do português ("A, B e C").
- [ ] Com **"acrescentar mapa"** marcado — padrão como na SPEC 001 —, a declaração traz a planta com a
      ortofoto, os lotes e o **desenho em destaque por cima**; sem ele, a ortofoto nem é consultada.
- [ ] A certidão de **um** lote continua saindo com o texto da SPEC 001.
- [ ] A emissão entra no acervo e fica **registrada** com operação própria, distinguível da emissão de
      um lote, e a ficha pública mostra os contribuintes, o processo e o despacho.
- [ ] O design da coluna de ações na gaveta inferior, do modal do conjunto e dos avisos foi aprovado
      no mock e as peças novas portadas para o tema e o styleguide antes de qualquer template da
      aplicação usá-las.

## 3 · Domínio
O conjunto é o [ConjuntoDeLotes](../localizacao_lote/004-revisao-do-conjunto.md#3--domínio) guardado
na sessão; a pergunta que esta SPEC faz a ele é "quais lotes restaram, e como o GeoSampa os descreve
agora?". A certidão de um lote e a do conjunto são **o mesmo documento** com objetos diferentes: o
objeto é um tipo, e cada subtipo sabe se identificar e se declarar.

**`services/domain/certidao_lancamento/models.py`** — `CertidaoLancamentoInput` inteiro e o objeto.

```python
class ObjetoCertidao(BaseModel):
    """O que a certidão atesta. Abstrato: a certidão sempre fala de um subtipo."""

    model_config = ConfigDict(frozen=True)

    @property
    def imoveis(self) -> tuple[LoteAttributes, ...]:
        raise NotImplementedError


class LoteUnico(ObjetoCertidao):
    tipo: Literal["lote_unico"] = "lote_unico"
    imovel: LoteAttributes

    @property
    def imoveis(self) -> tuple[LoteAttributes, ...]:
        return (self.imovel,)


class ConjuntoDesenhado(ObjetoCertidao):
    """Os lotes de um terreno desenhado, já revisados. Desenho e área vão para o papel."""

    tipo: Literal["conjunto_desenhado"] = "conjunto_desenhado"
    lotes: tuple[LoteAttributes, ...] = Field(min_length=1)
    area_desenho_m2: float = Field(gt=0)

    @property
    def imoveis(self) -> tuple[LoteAttributes, ...]:
        return self.lotes


class CertidaoLancamentoInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    envelope: EnvelopeAto
    pedido: PedidoCertidao
    # ALTERADO nesta SPEC: o objeto no lugar do `imovel` solto.
    objeto: Annotated[LoteUnico | ConjuntoDesenhado, Field(discriminator="tipo")]
    planta: PlantaLocalizacao | None      # como na SPEC 001: só quando o pedido a inclui
    consultado_em: AwareDatetime
    base_url: str

    @model_validator(mode="after")
    def _imoveis_certificaveis(self) -> Self:
        # ALTERADO nesta SPEC: a regra vale para cada imóvel do objeto.
        impeditivos = [i for i in self.objeto.imoveis if i.is_condominio or not i.possui_lancamento]
        if impeditivos:
            rotulos = ", ".join(_rotulo(i) for i in impeditivos)
            raise ValueError(f"Lotes sem lançamento ativo ou condominiais: {rotulos}.")
        return self
```

O pedido é o [PedidoCertidao](001-certidao-de-um-lote.md#3--domínio) da SPEC 001, com o
[TipoDespacho](001-certidao-de-um-lote.md#3--domínio) dela e o de-para para o sentido. O tipo que o
modal traz marcado é uma **sugestão** apurada da geometria — o que vale é o que o auditor envia.

**`services/domain/certidao_lancamento/sugestao.py`**

```python
class SugestaoDespachoInput(BaseModel):
    """O desenho e os lotes que restaram, já no CRS métrico: a fração é razão de áreas."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    desenho: GEOSGeometry
    lotes: tuple[GEOSGeometry, ...] = Field(min_length=1)
    fracao_minima_contida: float = Field(gt=0, le=1)


class SugerirTipoDespacho:
    def __call__(self, entrada: SugestaoDespachoInput) -> TipoDespacho:
        return self.pipeline(entrada)

    def pipeline(self, entrada: SugestaoDespachoInput) -> TipoDespacho:
        if all(self._eh_contido(lote, entrada) for lote in entrada.lotes):
            return TipoDespacho.LANCAMENTO_EM_MAIOR_AREA
        return TipoDespacho.LANCAMENTO_PARCIAL

    def _eh_contido(self, lote: GEOSGeometry, entrada: SugestaoDespachoInput) -> bool:
        # "Contém" com folga: a divisa desenhada à mão nunca bate no centímetro com a do cadastro,
        # e o `contains` puro jogaria em "parcial" todo desenho feito rente aos lotes.
        return lote.intersection(entrada.desenho).area / lote.area >= entrada.fracao_minima_contida
```

**Mock:** [002-mock-certidao-do-conjunto.html](002-mock-certidao-do-conjunto.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Lote condominial dentro do conjunto — sem dono ainda.
- Limite de quantidade de lotes numa certidão além da área máxima do desenho — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/lotes_mais_proximos/do_desenho.py` → `BuscarLotesDoDesenho` (SPEC localizacao_lote/003): a releitura.
- `@apps/lotes_mais_proximos/sessao.py` → `conjunto_vigente` (SPEC localizacao_lote/004): o conjunto pela chave.
- `@apps/lotes_mais_proximos/contexto.py` → `camada_lotes`: a camada da releitura.
- `@services/domain/certidao_lancamento/certidao` → `MontarCertidaoLancamento`, `CertidaoLancamento` (SPEC 001).
- `@apps/certidao_lancamento/emissao.py` → `emitir_certidao_lancamento` (SPEC 001).
- `@apps/acoes_lote` → `AcaoDeLote`, `ContratoAcoesLote`, `acoes_liberadas` e o partial do poço (SPEC 001).
- `.poco-acoes` (SPEC 001) → o poço "Ações"; `@templates/partials/_tarja_recusa.html` → recusas e avisos do modal.
- `@apps/certidao_lancamento/views.py` → `grupos_de_despacho`, `VALORES_INICIAIS` (SPEC 001); `@services/domain/certidao_lancamento/certidao` → `corpo_do_despacho`, `abertura_do_despacho` (SPEC 001): o formulário do pedido.
- `@services/domain/planta_localizacao` → `CamadaPlanta`, `EstiloGeometria` (SPEC documentos_oficiais/011).
- `@services/domain/geometry/reprojecao.py` → `reprojetar` (SPEC localizacao_lote/002).
- Skills: `acao-administrativa`, `documento-oficial`, `erros-de-formulario`, `mock`, `escrever-testes`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

No submódulo `services/domain/certidao_lancamento/certidao/` da SPEC 001, o montador pergunta ao objeto,
sem `if` por tipo espalhado.

**`certidao/constants.py`** — os corpos no plural, ao lado dos da SPEC 001.

```python
# O plural dos corpos. "Em maior área" e "parcial" citam o rol: o despacho diz por quais contribuintes o
# imóvel é lançado. "Pedido de acesso" não fala do imóvel e serve aos dois.
CORPO_DO_DESPACHO_CONJUNTO: dict[TipoDespacho, str] = {
    TipoDespacho.POSSUI_LANCAMENTO: (
        "os imóveis relacionados acima possuem lançamento do Imposto Predial e Territorial Urbano – IPTU – "
        "pelos respectivos contribuintes."
    ),
    TipoDespacho.LANCAMENTO_EM_MAIOR_AREA: (
        "o imóvel possui lançamento do Imposto Predial e Territorial Urbano – IPTU, em maior área, pelos "
        "contribuintes números {rol}."
    ),
    TipoDespacho.LANCAMENTO_PARCIAL: (
        "o imóvel possui lançamento parcial do Imposto Predial e Territorial Urbano – IPTU pelos "
        "contribuintes números {rol}."
    ),
    TipoDespacho.IMOVEL_NAO_LOCALIZADO: (
        "não foi possível a localização dos imóveis, já que as informações constantes no processo não são "
        "suficientes para a sua identificação inequívoca."
    ),
    TipoDespacho.PEDIDO_DE_ACESSO_A_INFORMACAO: CORPO_DO_DESPACHO[TipoDespacho.PEDIDO_DE_ACESSO_A_INFORMACAO],
}
```

**`certidao/certidao_builder.py`** — o rol, o corpo do conjunto e o montador por subtipo.

```python
def rol_de_contribuintes(sqls: Sequence[str]) -> str:
    # "A", "A e B", "A, B e C": a enumeração do português, não a vírgula solta.
    if len(sqls) == 1:
        return sqls[0]
    return f"{', '.join(sqls[:-1])} e {sqls[-1]}"


def corpo_do_despacho_conjunto(tipo: TipoDespacho, sqls: Sequence[str]) -> str:
    return CORPO_DO_DESPACHO_CONJUNTO[tipo].format(rol=rol_de_contribuintes(sqls))


class MontarCertidaoLancamento:
    def _blocos(self, pedido: MontarCertidaoLancamentoInput) -> tuple[Bloco, ...]:
        certidao = pedido.certidao
        return (
            Titulo(texto=TITULO),
            Subtitulo(texto="Dados relacionados à declaração"),
            *self._dados_relacionados(certidao),          # a identificação do imóvel sai daqui no lote único
            *self._identificacao(certidao.objeto),        # e daqui no conjunto: o parágrafo da área e a tabela
            Subtitulo(texto="Despacho"),
            *self._despacho(certidao.pedido, certidao.objeto),
            *self._localizacao(certidao.planta, certidao.objeto),           # "do Imóvel" / "dos Imóveis"; vazio sem mapa
            Paragrafo(texto=f"São Paulo, {por_extenso(certidao.envelope.emitido_em)}."),
            SeloDeFecho(selo=pedido.selo, quadro=pedido.quadro),
        )

    def _identificacao(self, objeto: LoteUnico | ConjuntoDesenhado) -> tuple[Bloco, ...]:
        match objeto:
            case LoteUnico():
                return ()
            case ConjuntoDesenhado(lotes=lotes, area_desenho_m2=area):
                return (
                    # Sem citar a planta: no indeferimento ela não existe.
                    Paragrafo(texto=f"Os imóveis objeto desta declaração compõem a área desenhada, com "
                                    f"{formatar_area(area)} m², e são os relacionados abaixo."),
                    Tabela(
                        colunas=(ColunaFixa(largura_mm=38.0), ColunaFluida(), ColunaFixa(largura_mm=40.0)),
                        cabecalho=("Contribuinte", "Endereço", "Complemento"),
                        linhas=tuple((l.sql or "", l.endereco, l.complemento or "—") for l in lotes),
                    ),
                )

    def _corpo_do_despacho(self, tipo: TipoDespacho, objeto: LoteUnico | ConjuntoDesenhado) -> str:
        match objeto:
            case LoteUnico(imovel=imovel):
                return corpo_do_despacho(tipo, imovel.sql)
            case ConjuntoDesenhado(lotes=lotes):
                return corpo_do_despacho_conjunto(tipo, tuple(lote.sql or "" for lote in lotes))
```

**`certidao/__init__.py`** — ALTERADO nesta SPEC: entra `corpo_do_despacho_conjunto`, que a prévia do
modal do conjunto usa. O `rol_de_contribuintes` fica interno: o teste o alcança pelo corpo.

`_dados_relacionados` e `_despacho` são os da SPEC 001; o `_despacho` passa a pedir o corpo a
`_corpo_do_despacho`, a abertura segue vindo de `abertura_do_despacho(tipo.sentido)`, e a ordem
despacho → ressalva → observações → validade não muda.

**`services/domain/lotes_mais_proximos/conjunto.py`** — a releitura: a mesma consulta da SPEC
localizacao_lote/003 sobre o desenho guardado, recortada aos lotes escolhidos.

```python
class ReleituraDoConjuntoInput(BaseModel):
    conjunto: ConjuntoDeLotes
    crs_mapa: int
    camada: CamadaLotes
    area_maxima_m2: float = Field(gt=0)


class RelerConjunto:
    def __init__(self, buscar: Callable[[LotesDoDesenhoInput], LotesDoDesenho]) -> None:
        self._buscar = buscar

    def __call__(self, entrada: ReleituraDoConjuntoInput) -> ConjuntoDeLotes:
        return self.pipeline(entrada)

    def pipeline(self, entrada: ReleituraDoConjuntoInput) -> ConjuntoDeLotes:
        apurado = self._buscar(LotesDoDesenhoInput(
            desenho=entrada.conjunto.apurado.desenho,
            crs_mapa=entrada.crs_mapa,
            camada=entrada.camada,
            area_maxima_m2=entrada.area_maxima_m2,
        ))
        escolhidos = {lote.attributes.id_poligono for lote in entrada.conjunto.lotes}
        # O que o desenho cruza hoje e não foi escolhido entra como removido: nem a camada acrescenta lote.
        # O escolhido que saiu da camada simplesmente não volta — é a conferência da emissão que o acusa.
        return ConjuntoDeLotes(
            apurado=apurado,
            removidos=frozenset(lote.attributes.id_poligono for lote in apurado.lotes) - escolhidos,
        )
```

**`apps/certidao_lancamento/emissao.py`** — a releitura com o instante, a conferência e a planta — esta
só com o mapa no pedido, como na SPEC 001. As geometrias métricas servem à planta e à sugestão.

```python
class ConjuntoLido(BaseModel):
    """O conjunto como o GeoSampa respondeu na emissão, e o instante: é ele que o rodapé declara."""

    conjunto: ConjuntoDeLotes
    consultado_em: AwareDatetime


def reler_conjunto(conjunto: ConjuntoDeLotes) -> ConjuntoLido:
    reler = RelerConjunto(BuscarLotesDoDesenho(build_fetcher(settings)))
    relido = reler(ReleituraDoConjuntoInput(
        conjunto=conjunto,
        crs_mapa=MAP_OUTPUT_CRS,
        camada=camada_lotes(),
        area_maxima_m2=LOTES_DESENHO_AREA_MAXIMA_M2,
    ))
    return ConjuntoLido(conjunto=relido, consultado_em=timezone.localtime())


def conferir_confirmados(lido: ConjuntoLido, confirmados: frozenset[str]) -> None:
    # O modal mostrou uma lista; a certidão atesta exatamente essa lista ou não sai.
    relidos = frozenset(lote.attributes.id_poligono for lote in lido.conjunto.lotes)
    if relidos != confirmados:
        raise ConjuntoAlteradoError(entraram=relidos - confirmados, sairam=confirmados - relidos)


class GeometriasMetricas(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    desenho: GEOSGeometry
    lotes: tuple[GEOSGeometry, ...]


def geometrias_metricas(conjunto: ConjuntoDeLotes, crs_mapa: int, crs_metrico: int) -> GeometriasMetricas:
    # O desenho não carrega CRS: está no do mapa, que a orquestração informa.
    return GeometriasMetricas(
        desenho=reprojetar(conjunto.apurado.desenho.geometria, crs_mapa, crs_metrico),
        lotes=tuple(reprojetar(lote.geometry, lote.crs, crs_metrico) for lote in conjunto.lotes),
    )


def camadas_da_planta_do_conjunto(geometrias: GeometriasMetricas) -> tuple[CamadaPlanta, ...]:
    return (
        CamadaPlanta(geometrias=geometrias.lotes, estilo=EstiloGeometria.CONTEXTO),
        CamadaPlanta(geometrias=(geometrias.desenho,), estilo=EstiloGeometria.DESTAQUE),
    )
```

**`apps/certidao_lancamento/views.py`** — o conjunto chega pela chave; o GeoServer só é consultado
depois que o formulário passou.

```python
@acao_protegida(ACAO_EMITIR_CERTIDAO_LANCAMENTO)
@require_GET
def modal_conjunto(request: HttpRequest) -> HttpResponse:
    # Abrir o modal é leitura: sai da sessão, sem GeoServer e sem linha no registro.
    chave = request.GET.get("id", "")
    conjunto = conjunto_vigente(request.session, chave)
    # contexto_modal_conjunto decide entre formulário e aviso (substituído, vazio, lotes impeditivos).
    return render(request, TEMPLATE_MODAL_CONJUNTO, contexto_modal_conjunto(conjunto, chave))


@acao_protegida(ACAO_EMITIR_CERTIDAO_LANCAMENTO)
@require_POST
def emitir_conjunto(request: HttpRequest) -> HttpResponse:
    leitura = ler_pedido_certidao(request.POST)
    chave = request.POST.get("chave", "")
    conjunto = conjunto_vigente(request.session, chave)
    if conjunto is None:
        return render(request, TEMPLATE_CONJUNTO_ALTERADO, contexto_conjunto_substituido(), status=409)
    if leitura.recusa is not None:
        contexto = contexto_modal_conjunto(conjunto, chave, valores=request.POST, recusa=leitura.recusa)
        return render(request, TEMPLATE_MODAL_CONJUNTO, contexto, status=422)
    lido = reler_conjunto(conjunto)
    try:
        conferir_confirmados(lido, frozenset(request.POST.getlist("confirmados")))
    except ConjuntoAlteradoError as erro:
        return render(request, TEMPLATE_CONJUNTO_ALTERADO, {"erro": erro}, status=409)
    if not certificaveis(lido.conjunto):
        # O lançamento pode ter caído depois do modal: o aviso volta com os dados relidos.
        return render(request, TEMPLATE_MODAL_CONJUNTO, contexto_modal_conjunto(lido.conjunto, chave), status=422)
    documento = emitir_certidao_do_conjunto(
        autor=_perfil(request),
        pedido=leitura.dto,
        lido=lido,
        base_url=request.build_absolute_uri("/"),
    )
    registrar_ato(
        request,
        operacao="emitir_conjunto",
        alvo_tipo="documento",
        alvo_identificador=documento.codigo,
    )
    return render(request, TEMPLATE_CERTIDAO_EMITIDA, {"codigo": documento.codigo})
```

**`config/settings.py`** — NOVO nesta SPEC: o limiar da sugestão, ao lado de
`LOTES_DESENHO_AREA_MAXIMA_M2`, com a linha comentada correspondente no `.env.example`.

```python
    lote_fracao_minima_contida: float = Field(
        default=0.99,
        gt=0,
        le=1,
        alias="LOTE_FRACAO_MINIMA_CONTIDA",
    )

LOTE_FRACAO_MINIMA_CONTIDA = _env.lote_fracao_minima_contida
```

**`apps/certidao_lancamento/views.py`** — o contexto do conjunto traz os textos no plural, com o rol, e
abre com o tipo que a geometria sugere; o resto dos campos é o da SPEC 001.

```python
# O limiar entra pela orquestração, como os CRS: o domínio o recebe no DTO.
LOTE_FRACAO_MINIMA_CONTIDA: float = settings.LOTE_FRACAO_MINIMA_CONTIDA
MAP_INTERPOLATION_CRS: int = settings.MAP_INTERPOLATION_CRS   # 31983: o métrico que o projeto já usa
MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS


def valores_iniciais_do_conjunto(conjunto: ConjuntoDeLotes) -> dict[str, Any]:
    geometrias = geometrias_metricas(conjunto, MAP_OUTPUT_CRS, MAP_INTERPOLATION_CRS)
    sugerir_tipo = SugerirTipoDespacho()
    sugerido = sugerir_tipo(SugestaoDespachoInput(
        desenho=geometrias.desenho,
        lotes=geometrias.lotes,
        fracao_minima_contida=LOTE_FRACAO_MINIMA_CONTIDA,
    ))
    return {**VALORES_INICIAIS, "tipo_despacho": sugerido}


def sqls_do_conjunto(conjunto: ConjuntoDeLotes | None) -> tuple[str, ...]:
    if conjunto is None:
        return ()
    return tuple(lote.attributes.sql or "" for lote in conjunto.lotes)



def contexto_modal_conjunto(
    conjunto: ConjuntoDeLotes | None,
    chave: str,
    valores: Mapping[str, Any] | None = None,
    recusa: RecusaDeFormulario | None = None,
) -> dict[str, Any]:
    # A sugestão só existe com lotes: conjunto vazio ou substituído abre o aviso, sem formulário.
    if valores is None and conjunto is not None and conjunto.lotes:
        valores = valores_iniciais_do_conjunto(conjunto)
    return {
        "conjunto": conjunto,
        "chave": chave,
        "valores": valores or {},
        "recusa": recusa,
        "motivos_recusa_conjunto": motivos_recusa_conjunto(conjunto),   # substituído, vazio ou impeditivos
        "grupos_despacho": grupos_de_despacho(TipoDespacho, partial(corpo_do_despacho_conjunto, sqls=sqls_do_conjunto(conjunto))),
    }
```

**`templates/certidao_lancamento/partials/_modal_conjunto.html`** — o formulário leva a chave e a lista
que o modal mostrou.

```html
<input type="hidden" name="chave" value="{{ chave }}">
{% for lote in conjunto.lotes %}
  <input type="hidden" name="confirmados" value="{{ lote.attributes.id_poligono }}">
{% endfor %}
```

**`apps/certidao_lancamento/emissao.py`** — o envelope do conjunto.

```python
        alvo=AlvoDoAto(tipo="conjunto_lotes", identificador=f"{len(lido.conjunto.lotes)} lotes"),
        operacao="emitir_conjunto",
        campos_publicos=("contribuintes", "processo", "despacho"),
        extras={
            "contribuintes": ", ".join(lote.attributes.sql or "" for lote in lido.conjunto.lotes),
            "processo": pedido.processo,
            "despacho": pedido.tipo_despacho.rotulo,   # o mesmo público da SPEC 001
        },
```

**`templates/lotes_mais_proximos/partials/_resultado_desenho.html`** — a gaveta inferior pede o poço
ao router com a chave do conjunto, fora da `#tabela-conjunto`: a lixeira não o repede a cada remoção.

```html
{% block corpo %}
  {% include "lotes_mais_proximos/partials/_tabela_conjunto.html" %}
  <div hx-get="{% url 'acoes_lote:acoes_conjunto' %}?chave={{ chave }}"   {# NOVO #}
       hx-trigger="load" hx-swap="outerHTML"></div>
{% endblock %}
```

**`apps/acoes_lote/declaradas.py` e `resolucao.py`** — o conjunto é outro contrato do mesmo router; o
filtro recebe o contrato como dado, em vez de ganhar um irmão.

```python
ACOES_LOTE = ContratoAcoesLote(
    itens=(AcaoDeLote(acao=ACAO_EMITIR_CERTIDAO_LANCAMENTO, url_name="certidao_lancamento:modal"),),
)
# NOVO nesta SPEC: a mesma ação, outra rota — a competência é uma só.
ACOES_CONJUNTO = ContratoAcoesLote(
    itens=(AcaoDeLote(acao=ACAO_EMITIR_CERTIDAO_LANCAMENTO, url_name="certidao_lancamento:modal_conjunto"),),
)


# ALTERADO nesta SPEC: o contrato desce como parâmetro.
def acoes_liberadas(contrato: ContratoAcoesLote, slugs: frozenset[str]) -> tuple[AcaoDeLote, ...]:
    return tuple(item for item in contrato.itens if item.acao.acao.slug in slugs)
```

**`apps/acoes_lote/views.py`** — a rota do conjunto; a do lote segue exigindo o SQL. Cada uma monta a
query string que o botão leva ao modal.

```python
class ConsultaAcoesConjunto(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    chave: str = Field(min_length=1, max_length=64)


@require_GET
def acoes_conjunto(request: HttpRequest) -> HttpResponse:
    try:
        consulta = ConsultaAcoesConjunto.model_validate(request.GET.dict())
    except ValidationError:
        return HttpResponse("")
    itens = acoes_liberadas(ACOES_CONJUNTO, slugs_liberados(request.user))
    # A resposta é a coluna inteira: sem item, sai vazia e a tabela fica com a largura toda.
    return render(request, TEMPLATE_COLUNA_ACOES, {"itens": itens, "parametros": urlencode({"id": consulta.chave})})
```

**`templates/acoes_lote/partials/_poco_acoes.html`** — ALTERADO nesta SPEC: o botão leva a query string
que a rota montou (`id` + `sql` no lote, `id` no conjunto).

```html
<button type="button" class="btn btn-onsen btn-sm"
        hx-get="{% url item.url_name %}?{{ parametros }}" hx-target="#poco-modal">
```

**`templates/acoes_lote/partials/_coluna_acoes_conjunto.html`** (`TEMPLATE_COLUNA_ACOES`) — o poço entra
numa coluna própria da gaveta inferior, estreita e centrada na altura da tabela.

```html
{% if itens %}
  <section id="poco-acoes-conjunto" class="gaveta-coluna gaveta-coluna-acoes">
    {% include "acoes_lote/partials/_poco_acoes.html" %}
  </section>
{% endif %}
```

## 7 · Caveats
A certidão do conjunto é a **mesma ação** da certidão de um lote, com outra rota e operação própria
(`emitir_conjunto`). É o mesmo ato, e quem pode certificar um lote pode certificar vários. O custo é
que não dá para conceder uma sem a outra.

O modal lê o conjunto da sessão, e só a emissão volta ao GeoSampa, uma vez. A certidão atesta o
lançamento no instante da emissão, como a de um lote, e a sessão guarda o cadastro do momento da
consulta. O custo é uma consulta `INTERSECTS` por emissão, e uma recusa `409` quando um lote escolhido
sai da camada entre a consulta e a emissão.

Na releitura, lote que o desenho passou a cruzar depois da consulta entra como removido. A pessoa
revisou uma lista, e a certidão não pode atestar lote que ela não viu. O custo é a certidão omitir um
lote novo na camada até alguém refazer a consulta.

`apps/certidao_lancamento` passa a conhecer `apps/lotes_mais_proximos`: a chave da sessão, pelo
`conjunto_vigente`, e a camada, pelo `camada_lotes`. É a ação consumindo o resultado da consulta, na
mão única do §3.5 do CLAUDE.md. O custo é a certidão depender do formato em que a consulta guarda o
conjunto na sessão.

`CertidaoLancamentoInput` troca `imovel` por `objeto`, e o montador passa a despachar por subtipo.
Um documento só evita que o timbre, o selo e o rodapé das duas certidões divirjam no primeiro ajuste.
O custo é que mexer no texto de um subtipo exige rodar o teste do outro.

O tipo que o modal traz marcado sai da geometria com folga: o lote conta como contido com a fração
configurada da área dentro do desenho, 0,99 por padrão. O `contains` puro jogaria em "parcial" todo
desenho feito rente à divisa, e a sugestão é só o ponto de partida do auditor. O custo é um lote com até
1% fora do desenho ser sugerido como "em maior área".

O conjunto ganha contrato e rota próprios no router de `apps/acoes_lote`, em vez de a rota do lote
aceitar um tipo. A rota do lote faz o enforcement do SQL, que o conjunto não tem, e misturar os dois
afrouxaria essa borda. O custo são duas rotas de poço, e cada ação nova de conjunto precisa entrar no
`ACOES_CONJUNTO`.

## 8 · Testes (TDD)

**Comportamento**
- `test_sugestao_de_tipo_pela_geometria` — desenho que contém todos os lotes sugere "em maior área";
  lote com mais que a folga fora do desenho sugere "parcial"; lote rente, com uma lasca abaixo da folga
  fora, segue "em maior área".
- `test_montar_certidao_do_conjunto_lista_todos_os_sqls_e_a_area` — a tabela tem uma linha por lote, o
  parágrafo cita a área formatada, o despacho sai no plural, "em maior área" e "parcial" citam o rol
  "A, B e C", e o pedido sem mapa sai sem a planta.
- `test_corpo_do_conjunto_enumera_o_rol_em_portugues` — pelo `corpo_do_despacho_conjunto` de "em maior
  área": um SQL sai sozinho, dois saem "A e B", três saem "A, B e C".
- `test_certidao_de_um_lote_mantem_o_texto` — com `LoteUnico`, os blocos saem como na SPEC 001.
- `test_planta_do_conjunto_poe_desenho_em_destaque_sobre_lotes_de_contexto` — `geometrias_metricas`
  leva o desenho (CRS do mapa) e os lotes (CRS da camada) ao mesmo CRS métrico, e
  `camadas_da_planta_do_conjunto` devolve os lotes em contexto e o desenho em destaque.
- `test_reler_conjunto_mantem_so_os_escolhidos` — com fetcher fake, lote novo que o desenho passou a
  cruzar entra em `removidos`, escolhido que sumiu da camada não volta, e os demais trazem os
  atributos relidos.
- `test_poco_de_acoes_da_gaveta_inferior_so_para_quem_tem_concessao` — com concessão, a coluna traz o
  botão que leva a chave no `id`; sem concessão ou sem chave, a resposta é vazia *(marker `banco`)*.
- `test_modal_do_conjunto_le_a_sessao_sem_consultar_o_wfs` — lista os lotes restantes com a chave e os
  `confirmados` ocultos, e o tipo sugerido pela geometria já marcado; com lote impeditivo ou conjunto
  vazio, traz o aviso sem formulário *(marker `banco`)*.
- `test_recusa_do_conjunto_preserva_o_tipo_escolhido` — desenho que sugere "em maior área", POST com
  "possui lançamento" e processo inválido: o 422 volta com "possui lançamento" marcado, não com a
  sugestão *(marker `banco`)*.
- `test_emissao_certifica_os_lotes_relidos` — o endereço mudado na camada depois da consulta sai na
  certidão com o valor novo; lote que perdeu o lançamento devolve o modal com o aviso, 422, sem
  emitir; o `DocumentoEmitido` traz contribuintes, processo e despacho entre os públicos *(marker `banco`)*.
- `test_mapa_do_conjunto_segue_o_pedido` — sem o mapa, emite sem chamar o WMS fake; indeferimento com
  o mapa forçado traz a planta com o desenho em destaque *(marker `banco`)*.
- `test_conjunto_diferente_do_modal_e_recusado_sem_emitir` — lote tirado depois do modal, lote que saiu
  da camada, id forjado nos `confirmados` e chave substituída dão 409, e nenhum `DocumentoEmitido`
  *(marker `banco`)*.
- `test_amostra_certidao_do_conjunto` — PDF "em maior área" com o rol, a tabela e a planta fictícia
  *(marker `artefato`)*.

**Segurança da ação** (skill `acao-administrativa`, fora do teto; todos com marker `banco`)
- `test_anonimo_no_modal_do_conjunto_vai_ao_login_sem_linha` — #1.
- `test_sem_concessao_no_conjunto_recebe_403_e_linha_de_negativa` — #2.
- `test_emissao_do_conjunto_grava_autor_cargo_unidade_operacao_e_alvo` — #10.
- `test_emitir_e_emitir_conjunto_distinguiveis_no_registro` — #11.
- `test_abrir_modal_do_conjunto_nao_registra` — #12.
- `test_emitir_conjunto_so_por_post` — #15.
