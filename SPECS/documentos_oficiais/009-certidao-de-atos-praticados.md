---
spec: documentos_oficiais/009
versao: v1
atualizado_em: 2026-09-08
testes_tdd: false
implementado: false
markers_obrigatorios: [banco, artefato]
changelog:
  - v1: versão inicial
---

# SPEC documentos_oficiais/009 — Certidão de atos praticados

## 1 · User story
O servidor da DIMAP emite, na tela do Registro de Ações, uma certidão dos atos que ele mesmo
praticou, no contexto de precisar comprovar seu trabalho a terceiros, para obter um PDF selado que
qualquer um pode conferir sem login.

## 2 · Condições de pronto
- [ ] O botão "Gerar documento com minhas ações" aparece na tela do Registro de Ações **só para quem
      pode executar a ação**, e abre um modal com período e tipos de ação.
- [ ] A certidão sai **selada**: quadro compacto no pé de toda página, quadro de fecho ao final, e o
      código do selo confere na tela de validação.
- [ ] A certidão lista **só os atos autorizados do próprio requerente** — ato de outro servidor não
      entra, nem que o requerente dirija a unidade dele.
- [ ] Cada ato é descrito pelo **cargo e pela unidade do dia em que foi praticado**; mudar a lotação
      depois não muda a certidão já emitida.
- [ ] Sem tipo de ação escolhido, a certidão traz todos os tipos; com tipos escolhidos, só eles — e
      a certidão **declara** o período e os tipos que a recortaram.
- [ ] Período sem ato algum emite **certidão negativa**, que afirma expressamente que nada foi
      praticado.
- [ ] A certidão emitida entra no acervo **inteira**, e a segunda via devolve os mesmos bytes.
- [ ] A emissão fica **registrada** no Registro de Ações, com o código da certidão como alvo.
- [ ] Período invertido, ou mais longo que o teto, é recusado com mensagem em português.
- [ ] O design do botão, do modal e do resultado foi aprovado no mock, e as peças portadas para o
      tema e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio
A certidão é **ato administrativo que fala do rastro de outros atos**. O que ela afirma é o que
`ExecucaoAcao` (épico `autorizacao`) gravou no dia de cada ato — cargo, unidade e cobertura do
momento —, e não o que o cadastro diz hoje. A pergunta que esta SPEC faz ao envelope da SPEC
[documentos_oficiais/007](007-envelope-do-ato-e-selo-no-papel.md) é quem assina e sob qual código; e a
que faz ao acervo da SPEC [documentos_oficiais/008](008-acervo-e-conferencia.md) é onde a via emitida
fica guardada.

O recorte da certidão **não é o do Registro de Ações**. Lá o universo são as unidades que o leitor
alcança; aqui é uma pessoa só, e ela pode ter praticado atos em unidades por onde passou — delimitar
por unidade faria a certidão omitir o que a pessoa fez antes de ser transferida.

**`services/domain/listagem_gestao/models/execucoes.py`** — o recorte próprio, ao lado do
`BuscaExecucoes` da SPEC [painel/002](../painel/002-registro-de-acoes.md), que segue intocado.
```python
class BuscaAtosProprios(BaseModel):
    """O recorte da certidão. Mesma propriedade de segurança do `BuscaExecucoes`: o primeiro campo é
    o delimitador do universo, sem default — esquecê-lo é erro de tipo, nunca certidão alheia."""

    model_config = ConfigDict(frozen=True)

    perfil_id: int
    inicio: date
    fim: date
    # Os slugs escolhidos no modal. Vazio quer dizer todos — critério em branco não estreita nada,
    # como no `BuscaExecucoes`.
    acoes: frozenset[str] = frozenset()

    @model_validator(mode="after")
    def periodo_coerente(self) -> Self:
        if self.fim < self.inicio:
            raise ValueError("A data final do período não pode ser anterior à inicial.")
        if (self.fim - self.inicio).days > JANELA_MAXIMA_DIAS:
            raise ValueError(f"O período da certidão não pode passar de {JANELA_MAXIMA_DIAS} dias.")
        return self
```

**`services/domain/certidao_atos/models.py`** — o que a certidão diz.
```python
class RecorteDeclarado(BaseModel):
    """Os critérios, já redigidos para sair impressos. A certidão que não declara o que recortou faz
    o leitor confundir "não praticou" com "não foi pedido"."""

    model_config = ConfigDict(frozen=True)

    inicio: date
    fim: date
    # Os NOMES das ações escolhidas, não os slugs: o slug é chave de código, não texto de papel.
    tipos: tuple[str, ...] = ()


class CertidaoAtosInput(BaseModel):
    """Recebe as linhas já lidas: o domínio do documento não vai ao banco, e é isso que o torna
    testável sem Django."""

    model_config = ConfigDict(frozen=True)

    # O ato inteiro, não os campos dele soltos: é ele que carrega autor, código e instante.
    envelope: EnvelopeAto
    recorte: RecorteDeclarado
    # A linha do rastro como o sistema já a materializa — a mesma que a tela do registro mostra.
    atos: tuple[LinhaExecucao, ...] = ()
    # O que é do processo: o endereço do ambiente, que o domínio não conhece.
    base_url: str
```

**Mock:** [009-mock-certidao-de-atos-praticados.html](009-mock-certidao-de-atos-praticados.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Certidão dos atos de **outro** servidor — a que o dirigente emitiria sobre a equipe; sem dono ainda.
- **Tentativas negadas** na certidão — ela atesta o que foi praticado, não o que foi recusado; sem
  dono ainda.
- Emissão **assíncrona** para período longo, e o teto que ela dispensaria — sem dono ainda.
- Revogação da certidão emitida — mesma fila da SPEC
  [documentos_oficiais/008](008-acervo-e-conferencia.md), sem dono ainda.
- A **certidão de lançamento de IPTU**, a outra produtora do acervo — SPEC própria, sem dono ainda.
- Filtro por tipo de ação na própria tela do Registro de Ações — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/competencias/historico.py` → `_linha`: o `ExecucaoAcao` virando `LinhaExecucao`.
- `@apps/competencias/protecao.py` → `acao_protegida`, `registrar_ato`: a rota protegida e o recado
  do rastro.
- `@apps/competencias/utils.py` → `instanciar_acao`: o contrato da ação.
- `@services/domain/documento_selado` → `gerar_codigo`, `montar_envelope`, `montar_selo_impresso`.
- `@services/utils/assinatura` → `selar_documento`: os bytes selados.
- `@services/domain/documento_oficial` → `marcacao_fazenda_dimap_selado`, `SeloDeFecho`,
  `RenderizarDocumentoOficial`: o papel selado, o quadro de fecho e o render.
- `@apps/documentos/acervo.py` → `guardar_documento` (SPEC 008): a linha do acervo.
- `@templates/competencias/partials/_busca_execucoes.html` → `.campo-periodo` + `data-campo-data`:
  o par de datas do modal.
- Skills: `acao-administrativa`, `documento-oficial`, `painel`, `ontologia`, `mock`,
  `componentes-frontend`, `escrever-testes`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`apps/competencias/acoes_declaradas.py`** — a terceira ação do app, ao lado das duas que já existem.
```python
ACAO_EMITIR_CERTIDAO_ATOS = instanciar_acao(
    slug="competencias.emitir_certidao_atos",
    nome="Emitir certidão de atos praticados",
    nome_curto="Certidão de atos",
    tooltip="Emite o PDF selado com os atos que você praticou no período.",
    # Abre o MODAL, e por isso o card do painel é o `_card_item_modal.html`. Resolve sem argumento,
    # como o check `competencias.E004` exige.
    url_name="competencias:modal_certidao_atos",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Concedida, não estrutural: emitir certidão não é atributo de quem dirige.
    estrutural=False,
    # Sem alcance: a ação não incide sobre unidade nenhuma. Quem delimita é o perfil do autor, que
    # vem da sessão — nunca do request.
    alcance=None,
)
```

**`apps/competencias/historico.py`** — a segunda leitura do rastro, ao lado da que a tela usa. O
recorte muda; a materialização da linha é a mesma função.
```python
def atos_proprios(busca: BuscaAtosProprios) -> list[LinhaExecucao]:
    return [_linha(execucao) for execucao in _recortadas_proprias(busca)]


def _recortadas_proprias(busca: BuscaAtosProprios) -> QuerySet[ExecucaoAcao]:
    # `perfil_id` primeiro e incondicional, como as unidades em `_recortadas`: é ele que delimita o
    # universo, e não um critério que o usuário pudesse relaxar. `autorizado=True` porque a certidão
    # atesta ato praticado, e tentativa recusada não é ato (§4).
    consulta = (
        ExecucaoAcao.objects.select_related("acao", "perfil", "unidade", "cargo_base", "cargo_comissao", "substituindo")
        .filter(perfil_id=busca.perfil_id, autorizado=True)
        .filter(momento__date__gte=busca.inicio, momento__date__lte=busca.fim)
    )
    if busca.acoes:
        consulta = consulta.filter(acao__slug__in=busca.acoes)
    # Cronológica direta, ao contrário do registro: a certidão se lê como uma narrativa do período.
    return consulta.order_by("momento")
```

**`services/domain/certidao_atos/certidao.py`** — o que a certidão diz e o tipo que a emite, as duas
peças da skill `documento-oficial`.
```python
class MontarCertidaoInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    # O pedido inteiro (§3), não os campos dele soltos.
    certidao: CertidaoAtosInput
    # E o que o tipo do documento resolveu: o selo já redigido e a medida do quadro de fecho.
    selo: SeloImpresso
    quadro: QuadroSeloConfig


class MontarCertidaoAtos:
    """Callable: o pedido → o conteúdo. Único lugar em que esta certidão é redigida."""

    def __call__(self, pedido: MontarCertidaoInput) -> ConteudoDocumento:
        return self.pipeline(pedido)

    def pipeline(self, pedido: MontarCertidaoInput) -> ConteudoDocumento:
        return ConteudoDocumento(
            titulo=TITULO,
            nome_arquivo=f"certidao_atos_{pedido.certidao.envelope.codigo}.pdf",
            blocos=self._blocos(pedido),
        )

    def _blocos(self, pedido: MontarCertidaoInput) -> tuple[Bloco, ...]:
        # A certidão negativa NÃO é outro documento: é o mesmo, com o corpo dizendo que nada houve.
        # Dois tipos de documento divergiriam no timbre, no fecho e no selo com o primeiro ajuste.
        corpo = self._tabela(pedido) if pedido.certidao.atos else self._negativa()
        return (
            Titulo(texto=TITULO),
            Paragrafo(texto=self._abertura(pedido)),
            Paragrafo(texto=self._criterios(pedido.certidao.recorte)),
            corpo,
            Paragrafo(texto=FE_PUBLICA),
            SeloDeFecho(selo=pedido.selo, quadro=pedido.quadro),
        )

    def _criterios(self, recorte: RecorteDeclarado) -> str:
        # Sem esta frase, "nenhum ato" e "nenhum ato DESTE tipo" saem indistinguíveis no papel.
        tipos = ", ".join(recorte.tipos) if recorte.tipos else "todos os tipos de ato"
        return (
            f"Período de {recorte.inicio:%d/%m/%Y} a {recorte.fim:%d/%m/%Y}. Tipos considerados: {tipos}."
        )

    def _tabela(self, pedido: MontarCertidaoInput) -> Tabela:
        return Tabela(
            colunas=(
                ColunaFixa(largura_mm=28.0),
                ColunaFluida(),
                ColunaFixa(largura_mm=32.0),
                ColunaFixa(largura_mm=22.0),
            ),
            cabecalho=("Data e hora", "Ato praticado", "Sobre o quê", "Unidade"),
            linhas=tuple(self._celulas(ato) for ato in pedido.certidao.atos),
        )

    def _celulas(self, ato: LinhaExecucao) -> tuple[str, ...]:
        # Cargo e unidade saem da LINHA, não do cadastro: é a cópia que a SPEC autorizacao/004 fez
        # no dia do ato, e é ela que faz a certidão continuar verdadeira depois de uma transferência.
        praticado = f"{ato.acao} — {ato.operacao}" if ato.operacao else ato.acao
        return (ato.momento, praticado, ato.alvo, ato.unidade)


class CertidaoAtos:
    """Callable: o tipo amarra o que a certidão diz, o papel SELADO em que ela sai e o tema. Quem
    emite só preenche o DTO."""

    def __init__(self, tema: Tema, config: MarcacaoConfig, selo_config: SeloConfig) -> None:
        self._montar = MontarCertidaoAtos()
        self._tema = tema
        self._config = config
        self._selo_config = selo_config
        self._renderizar = RenderizarDocumentoOficial(tema)

    def __call__(self, pedido: CertidaoAtosInput) -> DocumentoRenderizado:
        return self.pipeline(pedido)

    def pipeline(self, pedido: CertidaoAtosInput) -> DocumentoRenderizado:
        # O selo entra pelo `__call__`, nunca pelo construtor: "sempre selada" é política do tipo,
        # mas autor, código e instante são de CADA emissão.
        selo = montar_selo_impresso(
            SeloImpressoInput(envelope=pedido.envelope, base_url=pedido.base_url)
        )
        return self._renderizar(
            RenderizarDocumentoInput(
                conteudo=self._montar(
                    MontarCertidaoInput(
                        certidao=pedido,
                        selo=selo,
                        quadro=self._selo_config.fecho,
                    )
                ),
                marcacao=marcacao_fazenda_dimap_selado(
                    self._config,
                    self._tema,
                    selo,
                    self._selo_config.compacto,
                ),
            )
        )
```

**`apps/competencias/emissao_certidao.py`** — a emissão: ler o rastro, montar o envelope, renderizar,
selar e guardar. Camada de app, ao lado do `registro_execucao.py` — é ela que toca banco e `settings`.
```python
def emitir_certidao_atos(
    autor: Perfil,
    busca: BuscaAtosProprios,
    recorte: RecorteDeclarado,
    base_url: str,
) -> DocumentoEmitido:
    # Parâmetros soltos, e não um DTO: quem fala com o domínio são os DTOs abaixo; esta função é
    # orquestração de app, e envelopá-la só acrescentaria um tipo que ninguém mais lê.
    envelope = _envelope(autor, recorte)
    renderizado = _tipo_certidao()(
        CertidaoAtosInput(
            envelope=envelope,
            recorte=recorte,
            atos=tuple(atos_proprios(busca)),
            base_url=base_url,
        )
    )
    # Selar DEPOIS de renderizar, sobre os bytes finais: o selo cobre o arquivo inteiro, quadro de
    # fecho incluído.
    selado = selar_documento(
        SelarInput(
            pdf=renderizado.pdf,
            dados=montar_envelope(envelope),
            campos_publicos=envelope.campos_publicos,
            segredo=ASSINATURA_SEGREDO,
            id_chave=ASSINATURA_ID_CHAVE,
        )
    )
    # `execucao=None`: quem grava a execução é o decorator, depois que a view retorna (Caveats).
    return guardar_documento(selado, envelope, execucao=None)


def _envelope(perfil: Perfil, recorte: RecorteDeclarado) -> EnvelopeAto:
    return EnvelopeAto(
        codigo=gerar_codigo(),
        acao=ACAO_EMITIR_CERTIDAO_ATOS.acao.slug,
        operacao="emitir",
        autor=AutorDoAto(
            nome=f"{perfil.nome} {perfil.sobrenome}",
            unidade=perfil.unidade.sigla,
            cargo_base=perfil.cargo_base.nome,
            cargo_comissao=perfil.cargo_comissao.nome if perfil.cargo_comissao else None,
            substituindo=_cargo_substituido(perfil),
        ),
        # O alvo da certidão é a própria pessoa: é sobre os atos DELA que o documento fala.
        alvo=AlvoDoAto(tipo="servidor", identificador=perfil.rf),
        emitido_em=timezone.now(),
        # O que a conferência mostra sem login: o período e os tipos, nunca a lista de atos — o que
        # a pessoa fez não é público só porque o código dela vazou.
        campos_publicos=("periodo", "tipos"),
        extras={
            "periodo": f"{recorte.inicio:%d/%m/%Y} a {recorte.fim:%d/%m/%Y}",
            "tipos": ", ".join(recorte.tipos) or "todos",
        },
    )


def recorte_declarado(busca: BuscaAtosProprios) -> RecorteDeclarado:
    """Os slugs viram NOMES aqui, na borda: slug é chave de código, e papel não se lê em
    `competencias.conceder`. Vazio segue vazio — é o `_criterios` do documento que o redige."""
    return RecorteDeclarado(
        inicio=busca.inicio,
        fim=busca.fim,
        # `por_slug` devolve `None` para slug que não está no registro — o forjado some do
        # recorte declarado, e some da consulta pelo mesmo motivo: ele não é ação nenhuma.
        tipos=tuple(sorted(acao.acao.nome for slug in busca.acoes if (acao := REGISTRO.por_slug(slug)))),
    )


def _cargo_substituido(perfil: Perfil) -> str | None:
    """O CARGO de quem se cobre, e não a pessoa: descrever o ato pelo cargo de quem assinou, sem
    dizer por quem ele respondia, atribui a competência à pessoa errada (SPEC 007)."""
    substituicao = substituicao_que_exerce(perfil)
    if substituicao is None:
        return None
    coberto = substituicao.impedimento.perfil
    return coberto.cargo_comissao.nome if coberto.cargo_comissao else coberto.cargo_base.nome
```

**`apps/competencias/views.py`** e **`apps/competencias/urls.py`** — duas rotas, as duas protegidas.
```python
@acao_protegida(ACAO_EMITIR_CERTIDAO_ATOS)
def modal_certidao_atos(request: HttpRequest) -> HttpResponse:
    """Leitura: abrir o modal não pratica ato nenhum, e o decorator não grava linha por isso. Quem
    não pode executar a ação já foi recusado aqui — e ESSA negativa fica registrada."""
    return render(request, TEMPLATE_MODAL_CERTIDAO, contexto_modal_certidao(_perfil(request)))


@acao_protegida(ACAO_EMITIR_CERTIDAO_ATOS)
@require_POST
def emitir_certidao_atos_view(request: HttpRequest) -> HttpResponse:
    perfil = _perfil(request)
    # `perfil_id` sai da SESSÃO, nunca do POST: o campo forjado não muda de quem é a certidão.
    busca = BuscaAtosProprios(
        perfil_id=perfil.pk,
        # `.get`, e não `[...]`: campo ausente num POST forjado vira 422 no middleware, e não o
        # 500 da chave que não existe.
        inicio=request.POST.get("inicio"),
        fim=request.POST.get("fim"),
        acoes=frozenset(request.POST.getlist("acoes")),
    )
    documento = emitir_certidao_atos(
        autor=perfil,
        busca=busca,
        recorte=recorte_declarado(busca),
        base_url=request.build_absolute_uri("/"),
    )
    registrar_ato(
        request,
        operacao="emitir",
        alvo_tipo="documento",
        alvo_identificador=documento.codigo,
    )
    # O PDF não volta aqui: ele está no acervo, e quem o entrega é a segunda via da SPEC 008 — uma
    # via emitida, um lugar de onde ela sai.
    return render(request, TEMPLATE_CERTIDAO_EMITIDA, {"codigo": documento.codigo})
```
```python
urlpatterns = [
    ...
    path("registro-acoes/certidao/", views.modal_certidao_atos, name="modal_certidao_atos"),
    # Leitura e escrita em rotas separadas: é essa separação, e não uma flag no formulário, que faz
    # "abrir o modal não emite nada" ser estrutural.
    path("registro-acoes/certidao/emitir/", views.emitir_certidao_atos_view, name="emitir_certidao_atos"),
]
```

**`apps/painel/abas_declaradas.py`** — o card, no grupo em que a tela do registro já mora.
```python
Grupo(
    rotulo="Registro de Ações",
    itens=(
        ItemLivre(slug="painel.lista_registro_acoes", ...),
        ItemAcao(acao=ACAO_EMITIR_CERTIDAO_ATOS, partial=PARTIAL_CARTAO_MODAL),
    ),
),
```

**`templates/competencias/registro_acoes_list.html`** — o botão, ao lado do título.
```html
{# Esconder o botão é UX; a barreira é o `acao_protegida` da rota. #}
{% if perms.competencias.emitir_certidao_atos %}
  <button class="btn btn-onsen" hx-get="{% url 'competencias:modal_certidao_atos' %}" hx-target="#poco-modal">
    Gerar documento com minhas ações
  </button>
{% endif %}
```

## 7 · Caveats
A ação mora em `competencias`, e não em app próprio como o CLAUDE.md §3.5 manda. O rastro que ela
certifica é o domínio deste app — `ExecucaoAcao`, `historico.py` e a tela de onde o botão sai já vivem
aqui —, e um app novo existiria só para importar tudo isso de volta. O custo é `competencias` crescer
para três ações, e a exceção passar a ter dois precedentes em vez de um.

O `DocumentoEmitido` nasce com `execucao` nula, e o vínculo com o ato existe pelo código gravado no
`alvo_identificador` da execução. O decorator grava a execução depois que a view retorna, e a certidão
precisa estar no acervo antes disso — inverter a ordem exigiria a view chamar `gravar_execucao`, que é
exatamente o que a maquinaria da SPEC autorizacao/004 impede. O custo é uma coluna do acervo que esta
ação não preenche, e uma junção que se faz por texto em vez de chave.

`services/domain/certidao_atos` passa a conhecer `services/domain/listagem_gestao`, para consumir
`LinhaExecucao`. Materializar a linha de novo, com outro nome, duplicaria a extração que
`historico._linha` já faz e deixaria as duas livres para divergir. O custo é que mudar `LinhaExecucao`
passa a mexer no que sai impresso num documento assinado.

A emissão é síncrona, com teto de período. Certidão de dez anos de um servidor ativo é um PDF de
centenas de páginas montado dentro do request, e fila só se paga quando o caso comum a exige — que não
é este. O custo é o teto, que recusa um pedido legítimo de período longo.

A certidão atesta que o ato foi praticado, nunca que ele ainda vale. Revogação de ato não existe no
sistema, e o acervo da SPEC 008 tem a mesma limitação pelo mesmo motivo. O custo é que uma certidão
continua afirmando um ato depois de o ato ser desfeito por outro meio.

O que a conferência sem login mostra desta certidão é o período e os tipos, não a lista de atos. Quem
tem o papel já leu a lista, e quem só pegou o código não precisa dela para saber que a via é
autêntica. O custo é que a conferência pública não permite comparar o conteúdo da tabela, só o
recorte que a gerou.

## 8 · Testes (TDD)

**Comportamento**
- `test_certidao_lista_so_os_atos_autorizados_do_requerente` — ato de outro servidor e tentativa
  negada ficam de fora, mesmo com o requerente dirigindo a unidade do outro. *(marker `banco`)*
- `test_certidao_descreve_o_ato_pelo_cargo_e_unidade_do_dia` — transferir o servidor depois não muda
  o que a certidão já emitida diz sobre o ato. *(marker `banco`)*
- `test_atos_praticados_em_unidade_anterior_entram_na_certidao` — o recorte é a pessoa, não a
  unidade. *(marker `banco`)*
- `test_filtro_por_tipo_restringe_e_o_recorte_sai_declarado` — escolhidos dois tipos, só eles saem, e
  o documento nomeia período e tipos.
- `test_periodo_sem_ato_emite_certidao_negativa` — a certidão sai, com o corpo afirmando que nada foi
  praticado, e com o mesmo timbre e o mesmo selo.
- `test_certidao_emitida_sai_selada_e_confere` — os bytes emitidos passam em `conferir_selo` como
  `INTEGRO`, e o código do envelope é o da linha do acervo. *(marker `banco`)*
- `test_certidao_emitida_entra_no_acervo_inteira` — a segunda via devolve bytes idênticos aos da
  emissão. *(marker `banco`)*
- `test_emissao_fica_registrada_com_o_codigo_como_alvo` — a execução gravada traz `operacao="emitir"`
  e o código da certidão em `alvo_identificador`. *(marker `banco`)*
- `test_periodo_invertido_ou_longo_demais_eh_recusado` — 422 com mensagem em português, e nenhum
  documento no acervo.
- `test_amostra_da_certidao_para_conferencia` — grava a certidão de amostra e imprime o caminho, para
  conferir a olho a tabela, o quadro compacto e o quadro de fecho. *(marker `artefato`)*

**Segurança da ação** *(bateria da skill `acao-administrativa`; fora do teto)*
- `test_anonimo_vai_ao_login_e_nao_deixa_linha` — nas duas rotas. *(marker `banco`)*
- `test_sem_competencia_recebe_403_e_a_negativa_fica_registrada` — inclusive ao abrir o modal.
  *(marker `banco`)*
- `test_concessao_em_outra_unidade_nao_libera` — a competência não se herda pelo organograma.
  *(marker `banco`)*
- `test_impedido_recebe_403_e_exonerado_recebe_302` — quem está fora de exercício não emite.
  *(marker `banco`)*
- `test_abrir_o_modal_autorizado_nao_vira_linha` — leitura autorizada não afoga o registro.
  *(marker `banco`)*
- `test_perfil_forjado_no_post_nao_muda_de_quem_eh_a_certidao` — o `perfil_id` sai da sessão.
  *(marker `banco`)*
