---
spec: user_admin/031
versao: v1
atualizado_em: 2026-09-22
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC user_admin/031 — Tipos de unidade como ato administrativo

## 1 · User story
O administrador do sistema cria, edita, extingue e reativa tipos de unidade no catálogo da DIMAP para que a hierarquia do organograma reflita a estrutura administrativa da secretaria sem que novas unidades sejam criadas sob um tipo em extinção.

## 2 · Condições de pronto
- [ ] **Qualquer servidor autenticado** abre a lista de tipos de unidade na tabela-onsen com o toggle **Mostrar tipos extintos**; para quem **administra o sistema**, a tabela exibe a coluna de ações com o lápis e a lixeira por linha (que abrem os modais de editar e extinguir já com o tipo da linha escolhido); para os demais servidores, a tabela é exibida estritamente em modo de leitura, sem as ações nem os botões de ato. Os modais, quando abertos pelos cards do painel, vêm sem tipo escolhido.
- [ ] Criar, editar, extinguir e reativar são **exclusivos do administrador do sistema**: para os demais os cards não aparecem, e as rotas recusam mesmo com concessão gravada.
- [ ] Tipo de unidade **com unidades no organograma** tem **nível, permissão de raiz, tipos filhos vedados e requisitos de titular travados**, com aviso indicando quantas unidades o utilizam; **nome** segue editável, inclusive em tipo extinto.
- [ ] Extinguir **data** o tipo de unidade e o tira das opções de tipo no cadastro e na edição de unidade — **menos para unidades que já possuem aquele tipo**, que continuam vendo o seu marcado e selecionado.
- [ ] Tipo de unidade extinto **continua sendo avaliado normalmente**: as unidades daquele tipo seguem na hierarquia, subordinando e sendo subordinadas, com seus titulares e competências preservados.
- [ ] Em toda tela em que um tipo de unidade aparece, o extinto vem com **o mesmo rótulo** (`nome`) **em tom de warning e o tooltip "Tipo de unidade extinto"**; reativar devolve o tipo ao cadastro de unidades e retira a cor e o tooltip.
- [ ] Os quatro atos ficam **registrados** com a operação (`criar`, `editar`, `extinguir`, `reativar`), `alvo_tipo="tipo_unidade"` e o **nome do tipo de unidade**.
- [ ] O painel ganha, na aba **Estrutura Administrativa**, o grupo **"Tipos de Unidade"** com a **lista** e os quatro cards de ato. Como a lista é leitura aberta, quem não administra o sistema vê a lista do catálogo e nada mais.
- [ ] O design foi aprovado no mock, e as peças novas foram portadas para o tema e o styleguide antes de qualquer template da aplicação usá-las.

## 3 · Domínio

O tipo de unidade ganha a data que o retira da criação de unidades sem quebrá-las no organograma: o tipo entra em extinção e segue válido para as unidades existentes.

**`apps/unidades/models/unidade.py`**

```python
class TipoUnidade(models.Model):
    # ALTERADO nesta SPEC: ganha `extinto_em`. Os demais campos (`nome`, `nivel`,
    # `pode_ser_raiz`, `tipos_filhos_vedados`, `exige_alta_administracao`,
    # `nivel_minimo_titular`), constraints e o `clean()` seguem como estão.
    nome = models.CharField(max_length=60, unique=True)
    nivel = models.PositiveSmallIntegerField()
    pode_ser_raiz = models.BooleanField(default=False)
    tipos_filhos_vedados = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="vedado_como_filho_em",
        blank=True,
    )
    exige_alta_administracao = models.BooleanField(default=False)
    nivel_minimo_titular = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[...],
    )
    # NOVO: a data do ato que o retirou da criação de unidades. Nula é tipo vigente.
    extinto_em = models.DateField(null=True, blank=True)

    @property
    def extinto(self) -> bool:
        return self.extinto_em is not None
```

`TipoUnidade.objects` **continua devolvendo os extintos**, no mesmo molde de `CargoComissao`: quem filtra é a seleção de tipos permitidos no cadastro de unidades (§6).

**`services/domain/tipos_unidade/models.py`** — o domínio não conhece o ORM; do tipo só precisa disto.

```python
class IdentidadeTipoUnidade(BaseModel):
    model_config = ConfigDict(frozen=True)

    tipo_id: int
    nome: str
    nivel: int
    pode_ser_raiz: bool
    exige_alta_administracao: bool
    nivel_minimo_titular: int | None = None


class PreviaDaEdicaoTipoUnidade(BaseModel):
    model_config = ConfigDict(frozen=True)

    tipo: IdentidadeTipoUnidade
    # Unidades no organograma vinculadas a este tipo — impedem mudança estrutural.
    unidades_ativas: int


class TravasDaEdicaoTipoUnidade(BaseModel):
    """O que a edição não pode tocar, e a mensagem explicativa."""

    model_config = ConfigDict(frozen=True)

    estrutura_travada: bool
    motivo: str = ""


class PreviaDaExtincaoTipoUnidade(BaseModel):
    model_config = ConfigDict(frozen=True)

    tipo: IdentidadeTipoUnidade
    unidades_ativas: int
    ja_extinto: bool = False


class PreviaDaReativacaoTipoUnidade(BaseModel):
    model_config = ConfigDict(frozen=True)

    tipo: IdentidadeTipoUnidade
    ja_vigente: bool = False
```

Consumido de SPECs anteriores, sem recópia:

- [`Veredito`](029-cargos-em-comissao-como-ato-administrativo.md#3--domínio) — esta SPEC pergunta se o veredito com `pode` e `motivo` serve aos atos de extinção e reativação de tipo: serve, o tipo é idêntico.
- [`Acao` e `AcaoImplementada`](../autorizacao/001-catalogo-de-acoes-em-codigo.md) e a [proteção de rota com registro](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md) — esta SPEC pergunta como os quatro atos sem alcance e exclusivos de superusuário se inscrevem e se registram.
- [`ContratoPainel`, `Aba`, `Grupo`, `ItemAcao`, `ItemLivre`](../painel/001-painel-de-acoes-por-abas.md) — esta SPEC pergunta como o grupo novo entra na aba `ABA_ESTRUTURA`.
- [`Unidade.clean`](003-hierarquia-unidades.md) — esta SPEC pergunta o que acontece com a hierarquia das unidades quando o tipo entra em extinção: nada, as unidades seguem avaliadas normalmente.

**Mock:** [031-mock-tipos-de-unidade.html](031-mock-tipos-de-unidade.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Revalidação em lote das unidades e titularidades quando um tipo de unidade sem unidades ativas é editado — sem dono ainda.
- Histórico de alterações do tipo de unidade além do registro de execução — sem dono ainda.
- Página própria do tipo de unidade com a listagem de todas as unidades históricas daquele tipo — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/unidades/models/unidade.py` → `TipoUnidade`: o model do catálogo, constraints e validações de subordinação.
- `@apps/cargos/extincao.py` → `extinguir_cargo`/`reativar_cargo`: molde de extinção com data e veredito.
- `@services/domain/cargos` → `Veredito`: veredito booleano com motivo.
- `@templates/unidades/partials/_tabela_unidades.html`, `_barra_acoes_unidades.html` → tabela-onsen com coluna do lápis, lixeira, toggle e barra de ações.
- `@static/src/js/ui/filtro_linha_extinta.js` → filtro client-side do toggle de extintos.
- `@apps/competencias/utils.py` → `instanciar_acao`.
- `@apps/competencias/protecao.py` → `acao_protegida`, `registrar_ato`.
- Skills: `acao-administrativa`, `painel`, `componentes-frontend`, `mock`, `ontologia`, `escrever-testes`.

## 6 · Snippets

**`apps/unidades/acoes_declaradas.py`**

```python
# Quatro ações exclusivas do superusuário para o catálogo de tipos de unidade.
ACAO_CRIAR_TIPO_UNIDADE = instanciar_acao(
    slug="unidades.criar_tipo_unidade",
    nome="Cadastrar tipo de unidade",
    nome_curto="Novo tipo",
    tooltip="Cria um tipo de unidade no catálogo da DIMAP.",
    url_name="unidades:modal_criar_tipo_unidade",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    exclusiva_superusuario=True,
    alcance=None,
)

ACAO_EDITAR_TIPO_UNIDADE = instanciar_acao(
    slug="unidades.editar_tipo_unidade",
    nome="Editar tipo de unidade",
    nome_curto="Editar tipo",
    tooltip="Altera nome, regras de subordinação e requisitos de titular de um tipo de unidade.",
    url_name="unidades:modal_editar_tipo_unidade",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    exclusiva_superusuario=True,
    alcance=None,
)

ACAO_EXTINGUIR_TIPO_UNIDADE = instanciar_acao(
    slug="unidades.extinguir_tipo_unidade",
    nome="Extinguir tipo de unidade",
    nome_curto="Extinguir tipo",
    tooltip="Retira um tipo de unidade das opções de novas unidades — e a reverte.",
    url_name="unidades:modal_extinguir_tipo_unidade",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    exclusiva_superusuario=True,
    alcance=None,
)

ACAO_REATIVAR_TIPO_UNIDADE = instanciar_acao(
    slug="unidades.reativar_tipo_unidade",
    nome="Reativar tipo de unidade",
    nome_curto="Reativar tipo",
    tooltip="Devolve um tipo de unidade extinto às opções de criação de unidades.",
    url_name="unidades:modal_reativar_tipo_unidade",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    exclusiva_superusuario=True,
    alcance=None,
)
```

**`services/domain/tipos_unidade/avaliador.py`** — as três regras do ato, sem Django.

```python
class AvaliadorEdicaoTipoUnidade:
    """Estrutura travada quando há unidades vinculadas: alterar nível, titularidade ou subordinação
    sob unidades ativas quebraria a árvore ou destituiria titulares sem ato específico."""

    def __call__(self, previa: PreviaDaEdicaoTipoUnidade) -> TravasDaEdicaoTipoUnidade:
        if previa.unidades_ativas == 0:
            return TravasDaEdicaoTipoUnidade(estrutura_travada=False)
        return TravasDaEdicaoTipoUnidade(
            estrutura_travada=True,
            motivo=(
                f"{previa.unidades_ativas} unidade(s) utilizam este tipo. Realoque-as ou extinga-as "
                "antes de alterar nível, permissão de raiz, requisitos de titular ou regras de subordinação."
            ),
        )


class AvaliadorExtincaoTipoUnidade:
    def __call__(self, previa: PreviaDaExtincaoTipoUnidade) -> Veredito:
        if previa.ja_extinto:
            return Veredito(pode=False, motivo="Este tipo de unidade já está extinto.")
        return Veredito(pode=True)


class AvaliadorReativacaoTipoUnidade:
    def __call__(self, previa: PreviaDaReativacaoTipoUnidade) -> Veredito:
        if previa.ja_vigente:
            return Veredito(pode=False, motivo="Este tipo de unidade não está extinto.")
        return Veredito(pode=True)
```

**`apps/unidades/consulta.py`**

```python
def tipos_unidade_disponiveis(tipo_atual_id: int | None = None) -> QuerySet[TipoUnidade]:
    """Os tipos que uma nova unidade ou alteração pode escolher: os vigentes, mais o que a unidade JÁ possui."""
    disponiveis = Q(extinto_em__isnull=True)
    if tipo_atual_id is not None:
        disponiveis |= Q(pk=tipo_atual_id)
    return TipoUnidade.objects.filter(disponiveis).order_by("-nivel", "nome")


def unidades_ativas_do_tipo(tipo: TipoUnidade) -> int:
    """Unidades no organograma vinculadas ao tipo — extinguir uma unidade não a desvincula do tipo."""
    return tipo.unidades.filter(extinta_em__isnull=True).count()
```

**`apps/unidades/cadastro_tipo.py`** — as travas conferidas no backend.

```python
def editar_tipo_unidade(tipo: TipoUnidade, valores: Mapping[str, Any]) -> DesfechoTipoUnidade:
    leitura = ler_tipo_unidade(valores)
    if leitura.dto is None:
        return DesfechoTipoUnidade(tipo=None, recusa=leitura.recusa or RecusaDeFormulario())
    travas = avaliar_edicao_tipo(
        PreviaDaEdicaoTipoUnidade(
            tipo=_identidade(tipo),
            unidades_ativas=unidades_ativas_do_tipo(tipo),
        )
    )
    if travas.estrutura_travada and _estrutura_mudou(tipo, leitura.dto):
        return DesfechoTipoUnidade(tipo=None, recusa=recusa_de_estrutura(travas.motivo))
    tipo.nome = leitura.dto.nome
    if not travas.estrutura_travada:
        tipo.nivel = leitura.dto.nivel
        tipo.pode_ser_raiz = leitura.dto.pode_ser_raiz
        tipo.exige_alta_administracao = leitura.dto.exige_alta_administracao
        tipo.nivel_minimo_titular = leitura.dto.nivel_minimo_titular
    try:
        with transaction.atomic():
            tipo.full_clean()
            tipo.save()
            if not travas.estrutura_travada:
                tipo.tipos_filhos_vedados.set(leitura.dto.tipos_filhos_vedados_ids)
    except ValidationError as recusa:
        return DesfechoTipoUnidade(tipo=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    return DesfechoTipoUnidade(tipo=tipo)
```

**`apps/unidades/extincao_tipo.py`**

```python
def extinguir_tipo_unidade(tipo: TipoUnidade, hoje: date) -> DesfechoTipoUnidade:
    veredito = avaliar_extincao_tipo(previa_da_extincao_tipo(tipo))
    if not veredito.pode:
        return DesfechoTipoUnidade(tipo=None, recusa=recusa_do_veredito(veredito.motivo))
    tipo.extinto_em = hoje
    tipo.save(update_fields=["extinto_em"])
    return DesfechoTipoUnidade(tipo=tipo)
```

**`templates/unidades/partials/_rotulo_tipo_unidade.html`**

```django
<span class="rotulo-tipo-unidade{% if tipo.extinto %} rotulo-tipo-unidade-extinto{% endif %}"
      {% if tipo.extinto %}title="Tipo de unidade extinto"{% endif %}>{{ tipo.nome }}</span>
```

**`apps/painel/abas_declaradas.py`**

```python
# ABA_ESTRUTURA ganha o grupo "Tipos de Unidade" ao lado do organograma.
ABA_ESTRUTURA = Aba(
    slug="painel.estrutura_administrativa",
    rotulo="Estrutura Administrativa",
    titulo="Estrutura Administrativa",
    descricao=(
        "A forma da DIMAP: as unidades que a compõem, como se subordinam, os tipos de unidade e quem "
        "responde pela direção de cada uma."
    ),
    grupos=(
        Grupo(
            rotulo="Organograma",
            itens=(
                ItemLivre(
                    slug="painel.lista_unidades",
                    nome="Ver o organograma",
                    tooltip="A árvore de unidades e a tabela filtrável que a acompanha.",
                    url_name="unidades:listar_unidades",
                ),
                ItemAcao(acao=ACAO_CRIAR_UNIDADE),
                ItemAcao(acao=ACAO_CRIAR_UNIDADE_RAIZ),
                ItemAcao(acao=ACAO_DEFINIR_TITULAR, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_EXTINGUIR_UNIDADE, partial=PARTIAL_CARTAO_MODAL),
            ),
        ),
        Grupo(
            rotulo="Tipos de Unidade",
            itens=(
                ItemLivre(
                    slug="painel.lista_tipos_unidade",
                    nome="Tipos de unidade",
                    tooltip="O catálogo de tipos de unidade da DIMAP, seus níveis e requisitos de titular.",
                    url_name="unidades:listar_tipos_unidade",
                ),
                ItemAcao(acao=ACAO_CRIAR_TIPO_UNIDADE, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_EDITAR_TIPO_UNIDADE, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_EXTINGUIR_TIPO_UNIDADE, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_REATIVAR_TIPO_UNIDADE, partial=PARTIAL_CARTAO_MODAL),
            ),
        ),
    ),
)
```

## 7 · Caveats

A trava de estrutura do tipo vive em `services/` e na view, não no banco. As propriedades estruturais de tipo com unidades só são travadas no fluxo do ato administrativo. O banco não consegue verificar através da FK reversa se existem unidades ativas sem acoplar a constraint do model de tipo ao de unidade. Um comando SQL direto pode alterar nível ou restrições de um tipo em uso sem que o banco rejeite.

Extinguir tipo de unidade não altera unidades existentes. A extinção do tipo data o registro e impede seu uso em novas unidades, mantendo intocadas as unidades já criadas. A administração pública extingue tipologias organizacionais sem extinguir de imediato as unidades preexistentes que ainda operam sob ela. O organograma pode manter unidades ativas de tipo extinto até que sofram reforma administrativa própria.

`TipoUnidade.objects` continua trazendo os extintos. O gerente padrão do model não filtra tipos extintos, deixando o corte para a consulta de tipos disponíveis. Telas de detalhe, listagens e seletores de unidades existentes precisam renderizar e identificar o tipo mesmo após sua extinção. Qualquer nova funcionalidade que precise apenas de tipos vigentes deve lembrar de chamar o filtro específico.

Renomear pela tela briga com a seed. A edição de nome do tipo de unidade é permitida pela interface administrativa. `seed_unidades` utiliza o nome como chave natural para idempotência da carga inicial. Rodar a seed novamente após renomear um tipo pela tela recriará o tipo com o nome original da seed.

Quatro ações exclusivas de superusuário para um catálogo só. O catálogo de tipos de unidade é mantido por quatro ações administrativas distintas. Cada ato precisa registrar operação, card e ícone próprios no histórico de execuções. São quatro cards no painel e quatro conjuntos de ícones para ações que não oferecem granularidade de permissão entre si.

Aba Estrutura Administrativa exibe a lista a qualquer servidor autenticado. A lista de tipos de unidade entra como item livre no novo grupo da aba. Consultar os tipos de unidade existentes é informação pública e de leitura aberta dentro da organização. Usuários sem perfil de administração visualizam a aba com apenas a listagem liberada no grupo.

Campo travado sem input oculto apaga o valor no envio. Campos desabilitados por travas de negócio são acompanhados de campos ocultos correspondentes no formulário. Controles desabilitados no navegador não são submetidos no payload do formulário. O template precisa duplicar o envio dos valores atuais para evitar que o validador interprete ausência como alteração não autorizada.

Toggle de tipos extintos opera exclusivamente no cliente. A exibição de tipos extintos na tabela é controlada inteiramente por script no navegador. Enviar o estado do toggle ao servidor provocaria perda do filtro durante swaps fora de banda disparados pelos modais de ação. Todas as linhas, vigentes e extintas, são sempre trafegadas no HTML inicial e no corpo atualizado.

Corpo da tabela em swap fora de banda exige envelope de template. A resposta fora de banda do corpo da tabela vem envelopada pela tag template. O navegador descarta elementos de tabela avulsos quando o alvo principal da resposta não é uma tabela. O template de swap fora de banda precisa existir separadamente do fragmento usado nas ordenações diretas.

## 8 · Testes (TDD)

**Comportamento**

- `test_extinguir_data_o_tipo_e_o_tira_do_cadastro_de_unidades` — depois do ato, `extinto_em` está preenchido e `tipos_unidade_disponiveis()` não devolve o tipo. *(marker `banco`)*
- `test_tipo_extinto_segue_ofertado_a_unidade_que_ja_o_possui` — `tipos_unidade_disponiveis(tipo_atual_id=...)` devolve o extinto da própria unidade. *(marker `banco`)*
- `test_reativar_devolve_o_tipo_ao_cadastro_de_unidades` — `extinto_em` volta a ser nulo e o tipo reaparece na oferta. *(marker `banco`)*
- `test_unidades_de_tipo_extinto_seguem_na_hierarquia_e_exercem_competencia` — unidade cujo tipo foi extinto mantém subordinadas, titular e competências ativas. *(marker `banco`)*
- `test_edicao_recusa_nivel_raiz_e_titular_de_tipo_com_unidades` — POST que altera nível, permissão de raiz, alta administração ou nível mínimo titular de tipo com unidades é recusado. *(marker `banco`)*
- `test_edicao_altera_nome_de_tipo_com_unidades_e_extinto` — alterar o nome de tipo com unidades ativas ou extinto é aceito. *(marker `banco`)*
- `test_edicao_livre_quando_nenhuma_unidade_utiliza_o_tipo` — sem unidades vinculadas, todas as propriedades estruturais podem mudar. *(marker `banco`)*
- `test_veredito_recusa_ato_repetido` — extinguir tipo já extinto e reativar tipo vigente são recusados com motivo; domínio puro, sem banco.
- `test_corpo_sempre_traz_os_tipos_extintos_marcados` — o servidor sempre manda os tipos extintos com `class="linha-extinta"`; filtro é client-side. *(marker `banco`)*
- `test_listagem_aberta_a_qualquer_autenticado` — servidor sem caneta administrativa recebe status 200 na listagem sem botões de ato. *(marker `banco`)*

**Segurança da ação** (skill `acao-administrativa`; fora do teto)

- `test_anonimo_vai_ao_login_sem_registrar` — as quatro rotas redirecionam e não deixam linha no histórico. *(marker `banco`)*
- `test_autenticado_sem_competencia_recebe_403_e_fica_registrado` — negativa gera status 403 e registro de auditoria. *(marker `banco`)*
- `test_concessao_gravada_nao_abre_acao_exclusiva_de_superusuario` — nem concessão nem direção de unidade liberam os quatro atos. *(marker `banco`)*
- `test_ato_grava_quem_cargo_unidade_operacao_e_alvo` — execução grava a lotação do momento e o nome do tipo de unidade alvo. *(marker `banco`)*
- `test_extinguir_e_reativar_ficam_distinguiveis_no_registro` — operações opostas são distinguidas na coluna de operação. *(marker `banco`)*
- `test_gravacao_so_por_post` — rotas de gravação rejeitam GET e abertura de modal não pratica ato. *(marker `banco`)*
