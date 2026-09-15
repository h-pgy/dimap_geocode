---
spec: certidao_lancamento/001
versao: v1
atualizado_em: 2026-09-15
testes_tdd: false
implementado: false
markers_obrigatorios: [banco, artefato]
changelog:
  - v1: versão inicial
---

# SPEC certidao_lancamento/001 — Certidão de Existência de Lançamento de um lote

## 1 · User story
O auditor fiscal com a concessão emite, pela gaveta do lote localizado, a Certidão de Existência de
Lançamento daquele lote para o interessado de um processo SEI, para obter um PDF selado que atesta o
lançamento do IPTU e mostra onde o imóvel fica.

## 2 · Condições de pronto
- [ ] A gaveta do lote traz o poço **"Ações"** com o botão **"Emitir certidão de lançamento"** só para
      quem tem a concessão; sem nenhuma ação liberada, o poço **não aparece**.
- [ ] O botão abre um modal que pede o **número do processo SEI** e o **nome do interessado**.
- [ ] Processo fora do formato `NNNN.AAAA/NNNNNNN-D`, ou interessado em branco, volta ao modal com o
      campo destacado e a mensagem em português.
- [ ] Lote **sem lançamento ativo**, **condominial** ou que **não existe mais** no GeoSampa abre o
      modal com o aviso de que a certidão não pode ser emitida pelo sistema, sem formulário — e a
      emissão recusa pelo mesmo critério.
- [ ] Na emissão, o lote é **lido de novo no GeoSampa** pelo identificador do polígono — nenhum dado
      do imóvel vem do navegador.
- [ ] A certidão traz o requerimento (interessado e processo), a identificação do imóvel, o despacho
      que declara o lançamento pelo SQL, a **planta de localização** do lote e o fecho selado.
- [ ] O rodapé de toda página declara que a certidão foi emitida de forma automatizada e **quando os
      dados cadastrais foram consultados**.
- [ ] A certidão emitida entra no **acervo**, confere pelo código e a segunda via devolve os mesmos
      bytes; o modal troca o formulário pelo botão de download.
- [ ] A emissão fica **registrada** no Registro de Ações, com o código da certidão como alvo.
- [ ] O design do poço de ações, do modal, do aviso e da confirmação foi aprovado no mock — incluindo
      o glifo do ícone da ação — e as peças novas portadas para o tema e o styleguide antes de
      qualquer template da aplicação usá-las.

## 3 · Domínio
A certidão é ato administrativo sobre um [LoteAttributes](../localizacao_lote/001-dados-do-lote-na-gaveta.md#3--domínio)
que `possui_lancamento`. Ao envelope da SPEC [documentos_oficiais/007](../documentos_oficiais/007-envelope-do-ato-e-selo-no-papel.md)
esta SPEC pergunta quem assina e sob qual código; ao acervo da [008](../documentos_oficiais/008-acervo-e-conferencia.md),
onde a via fica; à [planta](../documentos_oficiais/011-planta-de-localizacao.md), a imagem do lote em
destaque; e ao [LotePorIdentificador](../localizacao_lote/003-lotes-do-desenho.md#3--domínio), o lote
relido na emissão.

As ações sobre entidade territorial ganham aqui o **router** do §3.5 do CLAUDE.md: um contrato em
código diz quais ações cada tipo de entidade oferece, e a gaveta recebe só as liberadas ao perfil.

**`services/domain/certidao_lancamento/models.py`**

```python
PADRAO_PROCESSO_SEI = r"^\d{4}\.\d{4}/\d{7}-\d$"


class PedidoCertidao(BaseModel):
    """O que o modal colhe: quem pede e em qual processo. É o que instrui a certidão junto com o lote."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    processo: str = Field(pattern=PADRAO_PROCESSO_SEI)
    interessado: str = Field(min_length=3, max_length=200)


class CertidaoLancamentoInput(BaseModel):
    """Tudo já apurado: o domínio do documento não vai ao WFS nem ao banco."""

    model_config = ConfigDict(frozen=True)

    envelope: EnvelopeAto
    pedido: PedidoCertidao
    imovel: LoteAttributes
    planta: PlantaLocalizacao
    # O instante da leitura do lote no GeoSampa: é ele, e não o da assinatura, que o rodapé declara.
    consultado_em: AwareDatetime
    base_url: str

    @model_validator(mode="after")
    def _imovel_certificavel(self) -> Self:
        if self.imovel.is_condominio:
            raise ValueError("Lote condominial: a certidão ainda não é emitida pelo sistema.")
        if not self.imovel.possui_lancamento:
            raise ValueError("O lote não possui lançamento ativo no cadastro.")
        return self
```

**`apps/acoes_entidade/estrutura.py`** — o contrato do router.

```python
class TipoEntidade(StrEnum):
    LOTE = "lote"


class AcaoDeEntidade(BaseModel):
    """Uma ação oferecida sobre um tipo de entidade. A rota recebe o identificador da entidade por query."""

    model_config = ConfigDict(frozen=True)

    acao: AcaoImplementada
    url_name: str   # rota do modal; pode diferir do url_name do contrato quando a ação opera sobre mais de um tipo
    variante_icone: VarianteIcone = VarianteIcone.PEQUENO


class ContratoAcoesEntidade(BaseModel):
    model_config = ConfigDict(frozen=True)

    por_tipo: Mapping[TipoEntidade, tuple[AcaoDeEntidade, ...]]
```

**Mock:** [001-mock-certidao-de-um-lote.html](001-mock-certidao-de-um-lote.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Certidão de conjunto de lotes — SPEC [certidao_lancamento/002](002-certidao-do-conjunto.md).
- Lote condominial — sem dono ainda (provável caso particular da certidão "a menor").
- Certidão negativa (inexistência de lançamento) — sem dono; emitida manualmente pelo técnico.
- Conferência do dígito verificador do processo SEI — sem dono ainda; só o formato é conferido.
- Card da ação no painel — não entra: a ação só existe sobre um lote localizado.

## 5 · Peças de referência a compor
- `@apps/competencias/emissao_certidao.py` → `emitir_certidao_atos`: sequência envelope → render → selo → acervo.
- `@services/domain/certidao_atos_administrativos/certidao.py` → `MontarCertidaoAtos`/`CertidaoAtos`: o molde do tipo selado.
- `@apps/competencias/protecao.py` → `acao_protegida`, `registrar_ato`.
- `@apps/competencias/resolucao.py` → `slugs_liberados`: o conjunto que o router filtra.
- `@services/utils/erros_formulario` → `Formulario`, `LeitorDeFormulario`: o modal com realce.
- `@services/domain/lote_geocod` → `LotePorIdentificador` (SPEC localizacao_lote/003).
- `@services/domain/planta_localizacao` → `GerarPlantaLocalizacao` (SPEC documentos_oficiais/011).
- Skills: `acao-administrativa`, `documento-oficial`, `erros-de-formulario`, `painel`, `mock`, `escrever-testes`.

## 6 · Snippets

> Comentários didáticos: **não são portados** para o código (§7.2 do CLAUDE.md).

**`services/domain/certidao_lancamento/certidao.py`** — o único lugar em que esta certidão é redigida.

```python
TITULO = "Certidão de Existência de Lançamento"
DESPACHO = "Solicitação deferida."
FUNDAMENTO = (
    "Com base nas informações consultadas de forma automatizada junto à base de dados oficial do "
    "Município de São Paulo, declara-se que o imóvel acima identificado possui lançamento do Imposto "
    "Predial e Territorial Urbano (IPTU) pelo contribuinte número {sql}."
)
LARGURA_PLANTA_MM = 150.0


class MontarCertidaoLancamentoInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    certidao: CertidaoLancamentoInput
    selo: SeloImpresso
    quadro: QuadroSeloConfig


class MontarCertidaoLancamento:
    def __call__(self, pedido: MontarCertidaoLancamentoInput) -> ConteudoDocumento:
        return self.pipeline(pedido)

    def pipeline(self, pedido: MontarCertidaoLancamentoInput) -> ConteudoDocumento:
        return ConteudoDocumento(
            titulo=TITULO,
            nome_arquivo=f"certidao_lancamento_{pedido.certidao.envelope.codigo}.pdf",
            blocos=self._blocos(pedido),
        )

    def _blocos(self, pedido: MontarCertidaoLancamentoInput) -> tuple[Bloco, ...]:
        certidao = pedido.certidao
        return (
            Titulo(texto=TITULO),
            Subtitulo(texto="Requerimento"),
            Paragrafo(texto=self._requerimento(certidao.pedido)),
            Subtitulo(texto="Identificação do Imóvel"),
            Paragrafo(texto=self._identificacao(certidao.imovel)),
            Subtitulo(texto="Despacho"),
            Paragrafo(texto=DESPACHO),
            Paragrafo(texto=FUNDAMENTO.format(sql=certidao.imovel.sql)),
            Subtitulo(texto="Localização do Imóvel"),
            ImagemRaster(conteudo=certidao.planta.png, largura_mm=LARGURA_PLANTA_MM),
            Paragrafo(texto=f"São Paulo, {por_extenso(certidao.envelope.emitido_em)}."),
            SeloDeFecho(selo=pedido.selo, quadro=pedido.quadro),
        )

    def _identificacao(self, imovel: LoteAttributes) -> str:
        texto = (
            f"O imóvel objeto desta certidão está localizado no endereço {imovel.nome_logradouro} "
            f"(codlog: {imovel.codlog[:5]}-{imovel.codlog[5:]}), número {imovel.numero_porta}"
        )
        return f"{texto}, complemento {imovel.complemento}." if imovel.complemento else f"{texto}."

    def _requerimento(self, pedido: PedidoCertidao) -> str:
        return f"Interessado: {pedido.interessado}. Processo SEI nº {pedido.processo}."


class CertidaoLancamento:
    """O tipo: conteúdo + papel selado com nota de rodapé + tema. Quem emite só preenche o DTO."""

    def __init__(self, tema: Tema, config: MarcacaoConfig, selo_config: SeloConfig) -> None:
        self._montar = MontarCertidaoLancamento()
        self._tema = tema
        self._config = config
        self._selo_config = selo_config
        self._renderizar = RenderizarDocumentoOficial(tema)

    def pipeline(self, pedido: CertidaoLancamentoInput) -> DocumentoRenderizado:
        selo = montar_selo_impresso(SeloImpressoInput(
            envelope=pedido.envelope,
            base_url=pedido.base_url,
        ))
        conteudo = self._montar(MontarCertidaoLancamentoInput(
            certidao=pedido,
            selo=selo,
            quadro=self._selo_config.fecho,
        ))
        marcacao = marcacao_fazenda_dimap_selado_com_nota(
            self._config,
            self._tema,
            selo,
            self._selo_config.compacto,
            nota=self._nota(pedido),
        )
        return self._renderizar(RenderizarDocumentoInput(conteudo=conteudo, marcacao=marcacao))

    def _nota(self, pedido: CertidaoLancamentoInput) -> tuple[str, ...]:
        # `consultado_em` chega no fuso local, resolvido pela orquestração: o domínio não importa
        # `django.utils.timezone`.
        momento = pedido.consultado_em
        return (
            "Certidão emitida de forma automatizada. Dados cadastrais consultados no GeoSampa em "
            f"{momento:%d/%m/%Y} às {momento:%H:%M}.",
        )
```

**`services/domain/documento_oficial/marcacoes_concretas/fazenda_dimap_selado_com_nota.py`** —
papel novo ao lado; `fazenda_dimap_selado` não muda.

```python
def marcacao_fazenda_dimap_selado_com_nota(
    config: MarcacaoConfig,
    tema: Tema,
    selo: SeloImpresso,
    quadro: QuadroSeloConfig,
    *,
    nota: tuple[str, ...],
) -> MarcacaoDocumento:
    # O mesmo papel selado, com a nota empilhada acima do endereço. A nota é de CADA emissão, como o selo.
    rodape = MarcasEmpilhadas(
        (
            NotaDeRodape(nota, tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
            RodapeEndereco(config.endereco, tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
            NumeracaoPaginas(tema.estilo_rodape_marca, tema.entrelinha_marca_mm),
        ),
        Posicao.INFERIOR,
    )
    ...
```

**`apps/certidao_lancamento/acoes_declaradas.py`**

```python
ACAO_EMITIR_CERTIDAO_LANCAMENTO = instanciar_acao(
    slug="certidao_lancamento.emitir",
    nome="Emitir certidão de existência de lançamento",
    nome_curto="Certidão de lançamento",
    tooltip="Emite o PDF selado que atesta o lançamento do IPTU do lote.",
    url_name="certidao_lancamento:modal",
    variantes_icone=frozenset({VarianteIcone.PEQUENO}),
    estrutural=False,
    alcance=None,
)
```

**`apps/acoes_entidade/declaradas.py` e `resolucao.py`** — o router: tipo × perfil.

```python
ACOES_ENTIDADE = ContratoAcoesEntidade(por_tipo={
    TipoEntidade.LOTE: (AcaoDeEntidade(acao=ACAO_EMITIR_CERTIDAO_LANCAMENTO, url_name="certidao_lancamento:modal"),),
})


def acoes_liberadas(tipo: TipoEntidade, slugs: frozenset[str]) -> tuple[AcaoDeEntidade, ...]:
    # O router filtra; a rota decide. Esconder o botão não protege nada.
    return tuple(item for item in ACOES_ENTIDADE.por_tipo.get(tipo, ()) if item.acao.acao.slug in slugs)
```

**`apps/acoes_entidade/views.py`** — rota aberta: anônimo recebe o poço vazio, não um login.

```python
@require_GET
def acoes(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaAcoesEntidade.model_validate(request.GET.dict())   # tipo + id da entidade
    itens = acoes_liberadas(consulta.tipo, slugs_liberados(request.user))
    return render(request, TEMPLATE_POCO_ACOES, {"itens": itens, "id_entidade": consulta.id})
```

```html
{# templates/lote_geocoder/partials/_gaveta_lote.html — a busca conhece o router, não as ações #}
<div hx-get="{% url 'acoes_entidade:acoes' %}?tipo=lote&id={{ lote.id_poligono }}" hx-trigger="load" hx-swap="outerHTML"></div>
```

**`apps/certidao_lancamento/views.py`**

```python
@acao_protegida(ACAO_EMITIR_CERTIDAO_LANCAMENTO)
@require_GET
def modal(request: HttpRequest) -> HttpResponse:
    # contexto_modal decide entre formulário e aviso (lote que sumiu, sem lançamento, condominial).
    lote = ler_lote(request.GET.get("lote", ""))
    return render(request, TEMPLATE_MODAL, contexto_modal(lote))


@acao_protegida(ACAO_EMITIR_CERTIDAO_LANCAMENTO)
@require_POST
def emitir(request: HttpRequest) -> HttpResponse:
    leitura = ler_pedido_certidao(request.POST)
    lote = ler_lote(request.POST.get("lote", ""))
    if leitura.recusa is not None or not certificavel(lote):
        contexto = contexto_modal(lote, valores=request.POST, recusa=leitura.recusa)
        return render(request, TEMPLATE_MODAL, contexto, status=422)
    documento = emitir_certidao_lancamento(
        autor=_perfil(request),
        pedido=leitura.dto,
        lote=lote,
        base_url=request.build_absolute_uri("/"),
    )
    registrar_ato(
        request,
        operacao="emitir",
        alvo_tipo="documento",
        alvo_identificador=documento.codigo,
    )
    return render(request, TEMPLATE_CERTIDAO_EMITIDA, {"codigo": documento.codigo})
```

**`templates/core/home.html`** — o poço dos modais que as ações de entidade abrem.

```html
<div id="poco-modal"></div>
```

**`templates/acoes_entidade/partials/_poco_acoes.html`** — sem item liberado, nada é desenhado.

```html
{% if itens %}
  <div class="card-well p-4 flex flex-col gap-2">
    <p class="text-overline">Ações</p>
    {% for item in itens %}
      <button type="button" class="btn btn-onsen btn-sm"
              hx-get="{% url item.url_name %}?lote={{ id_entidade }}"
              hx-target="#poco-modal">
        {{ item.acao.acao.nome_curto }}
      </button>
    {% endfor %}
  </div>
{% endif %}
```

**`apps/certidao_lancamento/emissao.py`** — orquestração; único ponto que lê settings.

```python
class LoteLido(BaseModel):
    """O lote como o GeoSampa respondeu na hora: geometria no CRS métrico (a planta a usa) e o instante."""

    feature: LoteFeature
    consultado_em: AwareDatetime


def ler_lote(id_poligono: str) -> LoteLido | None:
    # None = o polígono não existe mais na camada; o modal mostra o aviso em vez do formulário.
    feature = LotePorIdentificador(build_fetcher(settings))(LotePorIdentificadorInput(
        id_poligono=id_poligono,
        layer_name=WFS_LAYER_LOTE_CIDADAO,
        output_crs=MAP_INTERPOLATION_CRS,
    ))
    if feature is None:
        return None
    return LoteLido(feature=feature, consultado_em=timezone.localtime())


def emitir_certidao_lancamento(
    autor: Perfil,
    pedido: PedidoCertidao,
    lote: LoteLido,
    base_url: str,
) -> DocumentoEmitido:
    imovel = lote.feature.attributes
    envelope = EnvelopeAto(
        codigo=gerar_codigo(),
        acao=ACAO_EMITIR_CERTIDAO_LANCAMENTO.acao.slug,
        operacao="emitir",
        # Extraído de `competencias/emissao_certidao._envelope`, que passa a usá-lo: autor e cargo
        # substituído se redigem num lugar só para as duas certidões.
        autor=autor_do_ato(autor),
        alvo=AlvoDoAto(tipo="lote", identificador=imovel.sql or ""),
        emitido_em=timezone.localtime(),
        # O interessado é pessoa: fica no PDF, que só circula com quem o recebeu, e fora da ficha pública.
        campos_publicos=("contribuinte", "processo"),
        extras={"contribuinte": imovel.sql, "processo": pedido.processo},
    )
    planta = GerarPlantaLocalizacao(build_wms_fetcher(settings))(PlantaLocalizacaoInput(
        camadas=(CamadaPlanta(geometrias=(lote.feature.geometry,), estilo=EstiloGeometria.DESTAQUE),),
        config=planta_config(),
    ))
    renderizado = _tipo_certidao()(CertidaoLancamentoInput(
        envelope=envelope,
        pedido=pedido,
        imovel=imovel,
        planta=planta,
        consultado_em=lote.consultado_em,
        base_url=base_url,
    ))
    selado = selar_documento(SelarInput(
        pdf=renderizado.pdf,
        dados=montar_envelope(envelope),
        campos_publicos=envelope.campos_publicos,
        segredo=settings.ASSINATURA_SEGREDO,
        id_chave=settings.ASSINATURA_ID_CHAVE,
    ))
    return guardar_documento(selado, envelope, execucao=None)
```

**`apps/painel/checks.py`**

```python
ACOES_SEM_CARD: frozenset[str] = frozenset({
    "user_admin.editar_servidor",
    "unidades.editar_unidade",
    # Opera sobre um lote localizado: o botão mora na gaveta do lote (apps/acoes_entidade).
    "certidao_lancamento.emitir",
})
```

## 7 · Caveats
O router de ações de entidade (`apps/acoes_entidade`) é um contrato próprio, parecido com o
`ItemAcao` do painel. O card do painel e o botão da gaveta têm destino, variante de ícone e
parâmetro diferentes, e reusar o `ItemAcao` acoplaria a gaveta ao painel. O custo são duas
estruturas quase irmãs, e `painel.E004` só enxerga a ação pela linha em `ACOES_SEM_CARD`.

A gaveta do lote (busca) carrega o poço de ações por `hx-get` ao router. É o que mantém a busca sem
importar ação alguma. O custo é uma segunda requisição por lote localizado, também para o anônimo,
que recebe o poço vazio.

O lote é lido **duas vezes** no WFS: ao abrir o modal (para decidir se há formulário) e na emissão.
A leitura da emissão é a que vale, porque o modal pode ficar aberto enquanto a camada muda. O custo é
uma ida a mais ao GeoSampa por certidão, e a certidão pode recusar na emissão o que o modal ofereceu.

O rodapé declara o instante da leitura do lote no WFS, e não a data da última carga do daemon. A
certidão atesta o que o GeoSampa respondeu naquele momento, e os parquets locais não entram na
emissão. O custo é que a data não diz desde quando o próprio GeoSampa foi atualizado pela fonte
dele.

O interessado fica fora de `campos_publicos`. É dado de pessoa, e a ficha de conferência abre para
quem tiver o código. O custo é que quem confere pelo código vê o SQL e o processo, mas não a quem a
certidão foi emitida.

Só o **formato** do processo SEI é conferido, não o dígito verificador. O algoritmo do dígito não
está documentado no projeto. O custo é aceitar número bem formado que não existe.

`CertidaoLancamentoInput` recusa lote sem lançamento ou condominial também no domínio, além do aviso
do modal. A regra "só se certifica lançamento que existe" não pode depender da tela. O custo é a
mesma condição escrita no template do modal e no validador.

## 8 · Testes (TDD)

**Comportamento**
- `test_pedido_recusa_processo_fora_do_formato_sei` — `6017.2026/123-4` e texto livre falham; o
  formato completo passa.
- `test_certidao_input_recusa_lote_sem_lancamento_ou_condominial` — lote municipal e lote-mãe de
  condomínio falham na construção.
- `test_montar_certidao_declara_requerimento_identificacao_e_despacho` — os blocos trazem interessado,
  processo, endereço com codlog-DV e o SQL no despacho.
- `test_certidao_traz_planta_e_nota_com_instante_da_consulta` — há um `ImagemRaster` e a nota do rodapé
  cita data e hora de `consultado_em`.
- `test_poco_de_acoes_so_para_quem_tem_concessao` — anônimo e autenticado sem concessão recebem o poço
  vazio; com concessão, o botão aponta para o modal com o id do lote *(marker `banco`)*.
- `test_modal_de_lote_sem_lancamento_ou_inexistente_mostra_aviso_sem_formulario` — lote municipal e
  fetcher vazio abrem o aviso *(marker `banco`)*.
- `test_emissao_rele_lote_pelo_identificador` — o imóvel certificado é o que o fetcher fake devolve
  para o `cd_identificador` do POST; campos de endereço mandados no POST são ignorados
  *(marker `banco`)*.
- `test_emissao_guarda_via_no_acervo_e_devolve_download` — `DocumentoEmitido` gravado, segunda via com
  os mesmos bytes, resposta com o link *(marker `banco`)*.
- `test_formulario_invalido_volta_ao_modal_com_realce` — 422 com `campo-realce-erro` no processo
  *(marker `banco`)*.
- `test_amostra_certidao_de_lancamento` — PDF com planta fictícia para conferência *(marker `artefato`)*.

**Segurança da ação** (skill `acao-administrativa`, fora do teto; todos com marker `banco`)
- `test_anonimo_no_modal_vai_ao_login_sem_linha` — #1.
- `test_sem_concessao_recebe_403_e_linha_de_negativa` — #2.
- `test_concessao_em_outra_unidade_nao_passa` — #3.
- `test_impedido_recebe_403_e_exonerado_vai_ao_login` — #4.
- `test_emissao_grava_autor_cargo_unidade_operacao_e_alvo` — #10.
- `test_abrir_modal_nao_registra_e_negativa_registra` — #12.
- `test_acao_inativa_nao_libera_com_concessao_gravada` — #13.
- `test_emitir_so_por_post` — #15.
