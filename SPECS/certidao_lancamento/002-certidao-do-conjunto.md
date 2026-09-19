---
spec: certidao_lancamento/002
versao: v3
atualizado_em: 2026-09-18
testes_tdd: false
implementado: false
markers_obrigatorios: [banco, artefato]
changelog:
  - v1: versão inicial
  - v2: submódulo `lote_espacial` renomeado para `lotes_mais_proximos`
  - v3: o conjunto vem da sessão e é relido no GeoSampa só na emissão, e a ação passa à gaveta inferior dos lotes intersectados
---

# SPEC certidao_lancamento/002 — Certidão de Existência de Lançamento de um conjunto de lotes

## 1 · User story
O auditor fiscal com a concessão emite, a partir do conjunto de lotes revisado sobre um terreno
desenhado, uma única Certidão de Existência de Lançamento para todos esses lotes, no contexto de um
imóvel que ocupa vários lotes, para obter um PDF selado que atesta o lançamento de cada um e mostra
o terreno sobre eles.

## 2 · Condições de pronto
- [ ] A gaveta inferior dos lotes intersectados traz o poço **"Ações"** com **"Emitir certidão de
      lançamento"** só para quem tem a concessão; sem ação liberada, o poço não aparece.
- [ ] O modal do conjunto lista os lotes que restaram na tabela e pede processo SEI e interessado,
      com as mesmas recusas da SPEC [001](001-certidao-de-um-lote.md), **sem consultar o GeoServer**.
- [ ] Conjunto **vazio**, ou com algum lote **sem lançamento ativo** ou **condominial**, abre o modal
      com o aviso — listando os lotes impeditivos, quando houver —, sem formulário, para que sejam
      tirados na tabela antes.
- [ ] Na emissão, os lotes do conjunto guardado são **relidos no GeoSampa**, e a certidão atesta os
      dados dessa leitura; lote que apareceu no desenho depois da consulta não entra.
- [ ] Se o conjunto relido na emissão **difere** do que o modal mostrou — lote tirado na tabela depois,
      lote que saiu da camada, id forjado no POST ou resultado substituído por outra consulta —, a
      emissão é recusada com a explicação, e nada é emitido.
- [ ] Lote que perdeu o lançamento entre o modal e a emissão devolve o modal com o aviso de lotes
      impeditivos, e nada é emitido.
- [ ] A certidão traz o requerimento, a área do desenho, a **tabela** com SQL, endereço e complemento
      de cada lote, o despacho no plural e a planta com a ortofoto, os lotes e o **desenho em destaque
      por cima**.
- [ ] A certidão de **um** lote continua saindo com o texto da SPEC 001.
- [ ] A emissão entra no acervo e fica **registrada** com operação própria, distinguível da emissão de
      um lote.
- [ ] O design do poço de ações na gaveta inferior, do modal do conjunto e do aviso de lotes
      impeditivos foi aprovado no mock e as peças novas portadas para o tema e o styleguide antes de
      qualquer template da aplicação usá-las.

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
    planta: PlantaLocalizacao
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

**`apps/acoes_entidade/estrutura.py`** — `TipoEntidade` inteiro.

```python
class TipoEntidade(StrEnum):
    LOTE = "lote"                      # id: o id_poligono
    CONJUNTO_LOTES = "conjunto_lotes"  # ALTERADO nesta SPEC — id: a chave do conjunto na sessão
```

**Mock:** [002-mock-certidao-do-conjunto.html](002-mock-certidao-do-conjunto.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Distinção entre certidão "a maior" e "a menor", e o percentual de cada lote — SPEC
  [certidao_lancamento/003](003-certidao-a-maior-e-a-menor.md).
- Lote condominial dentro do conjunto — sem dono ainda.
- Limite de quantidade de lotes numa certidão além da área máxima do desenho — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/lotes_mais_proximos/do_desenho.py` → `BuscarLotesDoDesenho` (SPEC localizacao_lote/003): a releitura.
- `@apps/lotes_mais_proximos/sessao.py` → `conjunto_vigente` (SPEC localizacao_lote/004): o conjunto pela chave.
- `@apps/lotes_mais_proximos/contexto.py` → `camada_lotes`: a camada da releitura.
- `@services/domain/certidao_lancamento/certidao.py` → `MontarCertidaoLancamento`, `CertidaoLancamento` (SPEC 001).
- `@apps/certidao_lancamento/emissao.py` → `emitir_certidao_lancamento` (SPEC 001).
- `@apps/acoes_entidade` → contrato, `acoes_liberadas` e a rota do poço (SPEC 001).
- `@services/domain/planta_localizacao` → `CamadaPlanta`, `EstiloGeometria` (SPEC documentos_oficiais/011).
- `@services/domain/geometry/reprojecao.py` → `reprojetar` (SPEC localizacao_lote/002).
- Skills: `acao-administrativa`, `documento-oficial`, `erros-de-formulario`, `mock`, `escrever-testes`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/certidao_lancamento/certidao.py`** — o montador pergunta ao objeto, sem `if` por tipo
espalhado.

```python
FUNDAMENTO_CONJUNTO = (
    "Com base nas informações consultadas de forma automatizada junto à base de dados oficial do "
    "Município de São Paulo, declara-se que os imóveis acima relacionados possuem lançamento do "
    "Imposto Predial e Territorial Urbano (IPTU) pelos respectivos contribuintes."
)


class MontarCertidaoLancamento:
    def _blocos(self, pedido: MontarCertidaoLancamentoInput) -> tuple[Bloco, ...]:
        certidao = pedido.certidao
        return (
            Titulo(texto=TITULO),
            Subtitulo(texto="Requerimento"),
            Paragrafo(texto=self._requerimento(certidao.pedido)),
            Subtitulo(texto=self._titulo_identificacao(certidao.objeto)),   # "do Imóvel" / "dos Imóveis"
            *self._identificacao(certidao.objeto),
            Subtitulo(texto="Despacho"),
            Paragrafo(texto=DESPACHO),
            Paragrafo(texto=self._fundamento(certidao.objeto)),
            Subtitulo(texto=self._titulo_localizacao(certidao.objeto)),     # "do Imóvel" / "dos Imóveis"
            ImagemRaster(conteudo=certidao.planta.png, largura_mm=LARGURA_PLANTA_MM),
            Paragrafo(texto=f"São Paulo, {por_extenso(certidao.envelope.emitido_em)}."),
            SeloDeFecho(selo=pedido.selo, quadro=pedido.quadro),
        )

    def _identificacao(self, objeto: LoteUnico | ConjuntoDesenhado) -> tuple[Bloco, ...]:
        match objeto:
            case LoteUnico(imovel=imovel):
                return (Paragrafo(texto=self._endereco_por_extenso(imovel)),)
            case ConjuntoDesenhado(lotes=lotes, area_desenho_m2=area):
                return (
                    Paragrafo(texto=f"Os imóveis objeto desta certidão compõem a área delimitada na planta de "
                                    f"localização, com {formatar_area(area)} m², e são os relacionados abaixo."),
                    Tabela(
                        colunas=(ColunaFixa(largura_mm=38.0), ColunaFluida(), ColunaFixa(largura_mm=40.0)),
                        cabecalho=("Contribuinte", "Endereço", "Complemento"),
                        linhas=tuple((l.sql or "", l.endereco, l.complemento or "—") for l in lotes),
                    ),
                )
```

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

**`apps/certidao_lancamento/emissao.py`** — a releitura com o instante, a conferência e a planta.

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


def camadas_da_planta_do_conjunto(
    conjunto: ConjuntoDeLotes,
    crs_mapa: int,
    crs_metrico: int,
) -> tuple[CamadaPlanta, ...]:
    lotes = tuple(reprojetar(lote.geometry, lote.crs, crs_metrico) for lote in conjunto.lotes)
    # O desenho não carrega CRS: está no do mapa, que a orquestração informa.
    desenho = reprojetar(conjunto.apurado.desenho.geometria, crs_mapa, crs_metrico)
    return (
        CamadaPlanta(geometrias=lotes, estilo=EstiloGeometria.CONTEXTO),
        CamadaPlanta(geometrias=(desenho,), estilo=EstiloGeometria.DESTAQUE),
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
        campos_publicos=("contribuintes", "processo"),
        extras={
            "contribuintes": ", ".join(lote.attributes.sql or "" for lote in lido.conjunto.lotes),
            "processo": pedido.processo,
        },
```

**`templates/lotes_mais_proximos/partials/_resultado_desenho.html`** — a gaveta inferior pede o poço
ao router com a chave do conjunto, fora da `#tabela-conjunto`: a lixeira não o repede a cada remoção.

```html
{% block corpo %}
  {% include "lotes_mais_proximos/partials/_tabela_conjunto.html" %}
  <div hx-get="{% url 'acoes_entidade:acoes' %}?tipo=conjunto_lotes&id={{ chave }}"   {# NOVO #}
       hx-trigger="load" hx-swap="outerHTML"></div>
{% endblock %}
```

**`apps/acoes_entidade/declaradas.py`**

```python
ACOES_ENTIDADE = ContratoAcoesEntidade(por_tipo={
    TipoEntidade.LOTE: (AcaoDeEntidade(acao=ACAO_EMITIR_CERTIDAO_LANCAMENTO, url_name="certidao_lancamento:modal"),),
    # ALTERADO nesta SPEC: a mesma ação, outra rota — a competência é uma só.
    TipoEntidade.CONJUNTO_LOTES: (
        AcaoDeEntidade(acao=ACAO_EMITIR_CERTIDAO_LANCAMENTO, url_name="certidao_lancamento:modal_conjunto"),
    ),
})
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

## 8 · Testes (TDD)

**Comportamento**
- `test_certidao_input_recusa_conjunto_com_lote_sem_lancamento` — a mensagem cita o lote impeditivo.
- `test_montar_certidao_do_conjunto_lista_todos_os_sqls_e_a_area` — a tabela tem uma linha por lote e
  o parágrafo cita a área formatada.
- `test_certidao_de_um_lote_mantem_o_texto` — com `LoteUnico`, os blocos saem como na SPEC 001.
- `test_planta_do_conjunto_poe_desenho_em_destaque_sobre_lotes_de_contexto` — `camadas_da_planta_do_conjunto`
  devolve os lotes em contexto e o desenho em destaque, todos no CRS métrico.
- `test_reler_conjunto_mantem_so_os_escolhidos` — com fetcher fake, lote novo que o desenho passou a
  cruzar entra em `removidos`, escolhido que sumiu da camada não volta, e os demais trazem os
  atributos relidos.
- `test_poco_de_acoes_da_gaveta_inferior_so_para_quem_tem_concessao` — com a chave do conjunto no `id`
  *(marker `banco`)*.
- `test_modal_do_conjunto_le_a_sessao_sem_consultar_o_wfs` — lista os lotes restantes com a chave e os
  `confirmados` ocultos; com lote impeditivo ou conjunto vazio, traz o aviso sem formulário *(marker
  `banco`)*.
- `test_emissao_certifica_os_lotes_relidos` — o endereço mudado na camada depois da consulta sai na
  certidão com o valor novo; lote que perdeu o lançamento devolve o modal com o aviso, 422, sem
  emitir *(marker `banco`)*.
- `test_conjunto_diferente_do_modal_e_recusado_sem_emitir` — lote tirado depois do modal, lote que saiu
  da camada, id forjado nos `confirmados` e chave substituída dão 409, e nenhum `DocumentoEmitido`
  *(marker `banco`)*.
- `test_amostra_certidao_do_conjunto` — PDF com tabela e planta fictícia *(marker `artefato`)*.

**Segurança da ação** (skill `acao-administrativa`, fora do teto; todos com marker `banco`)
- `test_anonimo_no_modal_do_conjunto_vai_ao_login_sem_linha` — #1.
- `test_sem_concessao_no_conjunto_recebe_403_e_linha_de_negativa` — #2.
- `test_emissao_do_conjunto_grava_autor_cargo_unidade_operacao_e_alvo` — #10.
- `test_emitir_e_emitir_conjunto_distinguiveis_no_registro` — #11.
- `test_abrir_modal_do_conjunto_nao_registra` — #12.
- `test_emitir_conjunto_so_por_post` — #15.
