---
spec: certidao_lancamento/002
versao: v2
atualizado_em: 2026-09-17
testes_tdd: false
implementado: false
markers_obrigatorios: [banco, artefato]
changelog:
  - v1: versão inicial
  - v2: submódulo `lote_espacial` renomeado para `lotes_mais_proximos`
---

# SPEC certidao_lancamento/002 — Certidão de Existência de Lançamento de um conjunto de lotes

## 1 · User story
O auditor fiscal com a concessão emite, a partir do conjunto de lotes revisado sobre um terreno
desenhado, uma única Certidão de Existência de Lançamento para todos esses lotes, no contexto de um
imóvel que ocupa vários lotes, para obter um PDF selado que atesta o lançamento de cada um e mostra
o terreno sobre eles.

## 2 · Condições de pronto
- [ ] A gaveta do desenho traz o poço **"Ações"** com **"Emitir certidão de lançamento"** só para quem
      tem a concessão; sem ação liberada, o poço não aparece.
- [ ] O modal do conjunto lista os lotes que a certidão vai cobrir e pede processo SEI e interessado,
      com as mesmas recusas da SPEC [001](001-certidao-de-um-lote.md).
- [ ] Conjunto com algum lote **sem lançamento ativo** ou **condominial** abre o modal listando esses
      lotes, sem formulário, para que sejam tirados na tabela antes.
- [ ] Na emissão, o conjunto é **refeito no servidor** a partir do desenho e dos removidos: lote que
      o desenho não cruza não entra, mesmo mandado no POST.
- [ ] Se o conjunto refeito na emissão **difere** do que o modal mostrou, a emissão é recusada com a
      explicação, e nada é emitido.
- [ ] A certidão traz o requerimento, a área do desenho, a **tabela** com SQL, endereço e complemento
      de cada lote, o despacho no plural e a planta com a ortofoto, os lotes e o **desenho em destaque
      por cima**.
- [ ] A certidão de **um** lote continua saindo com o texto da SPEC 001.
- [ ] A emissão entra no acervo e fica **registrada** com operação própria, distinguível da emissão de
      um lote.
- [ ] O design do poço de ações na gaveta do desenho, do modal do conjunto e do aviso de lotes
      impeditivos foi aprovado no mock e as peças novas portadas para o tema e o styleguide antes de
      qualquer template da aplicação usá-las.

## 3 · Domínio
O conjunto é o [ConjuntoDeLotes](../localizacao_lote/004-revisao-do-conjunto.md#3--domínio), refeito
por `RevisarConjunto` a cada passo. A certidão de um lote e a do conjunto são **o mesmo documento**
com objetos diferentes: o objeto é um tipo, e cada subtipo sabe se identificar e se declarar.

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

**`apps/acoes_entidade/estrutura.py`** — `TipoEntidade` e a consulta inteiros.

```python
class TipoEntidade(StrEnum):
    LOTE = "lote"
    CONJUNTO_LOTES = "conjunto_lotes"   # ALTERADO nesta SPEC


class ConsultaAcoesEntidade(BaseModel):
    tipo: TipoEntidade
    # ALTERADO nesta SPEC: None para o conjunto, que não tem identificador — ele viaja no formulário da tabela.
    id: str | None = None
```

**Mock:** [002-mock-certidao-do-conjunto.html](002-mock-certidao-do-conjunto.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Distinção entre certidão "a maior" e "a menor", e o percentual de cada lote — SPEC
  [certidao_lancamento/003](003-certidao-a-maior-e-a-menor.md).
- Lote condominial dentro do conjunto — sem dono ainda.
- Limite de quantidade de lotes numa certidão além da área máxima do desenho — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/lotes_mais_proximos/conjunto.py` → `RevisarConjunto` (SPEC localizacao_lote/004).
- `@services/domain/certidao_lancamento/certidao.py` → `MontarCertidaoLancamento`, `CertidaoLancamento` (SPEC 001).
- `@apps/certidao_lancamento/emissao.py` → `emitir_certidao_lancamento` (SPEC 001).
- `@apps/acoes_entidade` → contrato, `acoes_liberadas` e a rota do poço (SPEC 001).
- `@services/domain/planta_localizacao` → `CamadaPlanta`, `EstiloGeometria` (SPEC documentos_oficiais/011).
- `@services/domain/geometry/reprojecao.py` → `reprojetar` (SPEC localizacao_lote/002).
- `@templates/lotes_mais_proximos/partials/_tabela_lotes.html` → o formulário `#conjunto-lotes` com desenho e removidos.
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

**`apps/certidao_lancamento/emissao.py`** — a planta do conjunto: lotes de contexto, desenho por cima.

```python
def camadas_da_planta_do_conjunto(apurado: LotesDoDesenho, crs_metrico: int) -> tuple[CamadaPlanta, ...]:
    lotes = tuple(reprojetar(l.geometry, l.crs, crs_metrico) for l in apurado.lotes)
    desenho = reprojetar(apurado.conjunto.desenho.geometria, apurado.conjunto.desenho.crs, crs_metrico)
    return (
        CamadaPlanta(geometrias=lotes, estilo=EstiloGeometria.CONTEXTO),
        CamadaPlanta(geometrias=(desenho,), estilo=EstiloGeometria.DESTAQUE),
    )


def conferir_confirmados(apurado: LotesDoDesenho, confirmados: frozenset[str]) -> None:
    # O modal mostrou uma lista; a certidão atesta exatamente essa lista ou não sai.
    refeitos = frozenset(l.attributes.id_poligono for l in apurado.lotes)
    if refeitos != confirmados:
        raise ConjuntoAlteradoError(entraram=refeitos - confirmados, sairam=confirmados - refeitos)
```

**`apps/certidao_lancamento/views.py`**

```python
@acao_protegida(ACAO_EMITIR_CERTIDAO_LANCAMENTO)
@require_GET
def modal_conjunto(request: HttpRequest) -> HttpResponse:
    # GET com hx-include do formulário da tabela: abrir o modal é leitura e não vira linha no registro.
    apurado = revisar_conjunto(conjunto_do_request(request.GET))
    return render(request, TEMPLATE_MODAL_CONJUNTO, contexto_modal_conjunto(apurado))


@acao_protegida(ACAO_EMITIR_CERTIDAO_LANCAMENTO)
@require_POST
def emitir_conjunto(request: HttpRequest) -> HttpResponse:
    leitura = ler_pedido_certidao(request.POST)
    apurado = revisar_conjunto(conjunto_do_request(request.POST))
    if leitura.recusa is not None:
        contexto = contexto_modal_conjunto(apurado, valores=request.POST, recusa=leitura.recusa)
        return render(request, TEMPLATE_MODAL_CONJUNTO, contexto, status=422)
    try:
        conferir_confirmados(apurado, frozenset(request.POST.getlist("confirmados")))
    except ConjuntoAlteradoError as erro:
        return render(request, TEMPLATE_CONJUNTO_ALTERADO, {"erro": erro}, status=409)
    documento = emitir_certidao_do_conjunto(
        autor=_perfil(request),
        pedido=leitura.dto,
        apurado=apurado,
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

**`apps/certidao_lancamento/emissao.py`** — o envelope do conjunto.

```python
        alvo=AlvoDoAto(tipo="conjunto_lotes", identificador=f"{len(apurado.lotes)} lotes"),
        operacao="emitir_conjunto",
        campos_publicos=("contribuintes", "processo"),
        extras={
            "contribuintes": ", ".join(l.attributes.sql or "" for l in apurado.lotes),
            "processo": pedido.processo,
        },
```

**`templates/acoes_entidade/partials/_poco_acoes.html`** — no conjunto, o botão leva o formulário da tabela.

```html
{# ALTERADO nesta SPEC: sem id de entidade, o botão inclui #conjunto-lotes em vez de ?lote= #}
{% if itens %}
  <div class="card-well p-4 flex flex-col gap-2">
    <p class="text-overline">Ações</p>
    {% for item in itens %}
      <button type="button" class="btn btn-onsen btn-sm"
              hx-get="{% url item.url_name %}{% if id_entidade %}?lote={{ id_entidade }}{% endif %}"
              {% if not id_entidade %}hx-include="#conjunto-lotes"{% endif %}
              hx-target="#poco-modal">
        {{ item.acao.acao.nome_curto }}
      </button>
    {% endfor %}
  </div>
{% endif %}
```

```html
{# templates/lotes_mais_proximos/partials/_gaveta_desenho.html — o resumo do desenho pede o poço ao router #}
<div hx-get="{% url 'acoes_entidade:acoes' %}?tipo=conjunto_lotes" hx-trigger="load" hx-swap="outerHTML"></div>
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

O modal do conjunto abre por GET com o desenho e os removidos na query string (`hx-include`). Abrir o
modal é leitura, e POST gravaria uma execução a cada abertura. O custo é uma URL longa: desenho com
muitos vértices pode passar do limite de URL de algum proxy no caminho.

O conjunto é refeito no WFS três vezes: na tabela, no modal e na emissão. É o que impede que o
navegador acrescente lote e que a certidão ateste lista diferente da conferida. O custo são três
consultas `INTERSECTS` por certidão, e uma recusa `409` quando a camada muda entre o modal e a
emissão.

`CertidaoLancamentoInput` troca `imovel` por `objeto`, e o montador passa a despachar por subtipo.
Um documento só evita que o timbre, o selo e o rodapé das duas certidões divirjam no primeiro ajuste.
O custo é que mexer no texto de um subtipo exige rodar o teste do outro.

## 8 · Testes (TDD)

**Comportamento**
- `test_certidao_input_recusa_conjunto_com_lote_sem_lancamento` — a mensagem cita o lote impeditivo.
- `test_conjunto_desenhado_recusa_lista_vazia` — `ConjuntoDesenhado(lotes=())` falha na construção.
- `test_montar_certidao_do_conjunto_lista_todos_os_sqls_e_a_area` — a tabela tem uma linha por lote e
  o parágrafo cita a área formatada.
- `test_certidao_de_um_lote_mantem_o_texto` — com `LoteUnico`, os blocos saem como na SPEC 001.
- `test_planta_do_conjunto_poe_desenho_em_destaque_sobre_lotes_de_contexto` — `camadas_da_planta_do_conjunto`
  devolve os lotes em contexto e o desenho em destaque, todos no CRS métrico.
- `test_poco_de_acoes_do_desenho_so_para_quem_tem_concessao` *(marker `banco`)*.
- `test_modal_do_conjunto_com_lote_impeditivo_lista_os_lotes_sem_formulario` *(marker `banco`)*.
- `test_emissao_refaz_o_conjunto_e_ignora_lote_forjado` — id de lote de fora do desenho no POST não
  aparece na certidão *(marker `banco`)*.
- `test_conjunto_alterado_desde_o_modal_e_recusado_sem_emitir` — 409 e nenhum `DocumentoEmitido`
  *(marker `banco`)*.
- `test_amostra_certidao_do_conjunto` — PDF com tabela e planta fictícia *(marker `artefato`)*.

**Segurança da ação** (skill `acao-administrativa`, fora do teto; todos com marker `banco`)
- `test_anonimo_no_modal_do_conjunto_vai_ao_login_sem_linha` — #1.
- `test_sem_concessao_no_conjunto_recebe_403_e_linha_de_negativa` — #2.
- `test_emissao_do_conjunto_grava_autor_cargo_unidade_operacao_e_alvo` — #10.
- `test_emitir_e_emitir_conjunto_distinguiveis_no_registro` — #11.
- `test_abrir_modal_do_conjunto_nao_registra` — #12.
- `test_emitir_conjunto_so_por_post` — #15.
