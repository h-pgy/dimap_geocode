---
spec: autorizacao/004
versao: v8
atualizado_em: 2026-08-17
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: registro passa a identificar a operação praticada; grava toda negativa e as execuções que
    alteram estado, não a leitura autorizada de tela; anônimo sai do critério de registro
  - v3: o registro passa a dizer por quem o autor respondia — com a substituição (SPEC
    user_admin/015) o ato pode ser praticado pela competência do cargo de outra pessoa, e só o
    cargo do autor descreveria o ato errado
  - v4: sem mudança de escopo — a SPEC foi reescrita no formato de seções numeradas da skill
    `specs`, com a justificativa toda concentrada em Caveats
  - v5: a ação declara no contrato o alcance do seu alvo, e a própria proteção confere a
    unidade-alvo antes de a view rodar, compondo a árvore hierárquica da SPEC `user_admin/018`
  - v6: o alcance passa a ser a união do que pende de cada unidade dirigida, uma pergunta por
    unidade à árvore hierárquica
  - v7: o alcance nomeia as peças que de fato consome da árvore — a posição e os ids do nó — e o
    custo de recalculá-lo passa a contar também as canetas
  - v8: nomenclatura mais aderente ao domínio — `execucoes` vira `acoes_executadas` no related_name
    do registro; o alcance ganha o tipo abstrato `TipoAlcance`, do qual `SubarvoreDirigida` (agora
    `UnidadesSubordinadas`) é subtipo, com o campo `parametro_id_unidade_alvo` explicitado como o
    nome do parâmetro na assinatura da view — nunca um id de unidade real — para que um alcance
    futuro entre como subtipo novo sem mudar `Acao`; `conferir_alvo` nomeia o valor bruto do request
    (`id_bruto`) e o id já convertido (`id_unidade_alvo`) como passos distintos, em vez de converter
    escondido dentro do `if` final; os snippets de `acao_protegida`/`registrar_ato` deixam explícito
    o `_registro_ato` como a única ponte entre view e decorator — a view nunca chama `gravar_execucao`
    —; e `conferir_alvo` passa a despachar a checagem de pertencimento por subtipo de `TipoAlcance`
    (`isinstance` no próprio corpo, chamando `_unidade_esta_subordinada`), com `NotImplementedError`
    no `else` marcando onde estender quando um alcance novo aparecer
---

# SPEC autorizacao/004 — Proteção de rota e registro de execução do ato

## 1 · User story
**Requisito não-funcional** — a competência da SPEC 003 vira barreira na rota e rastro no banco: todo
ato administrativo praticado na plataforma passa a ter autor conhecido, alvo conferido contra o alcance
que a ação declara, e toda tentativa negada passa a ser investigável.

## 2 · Condições de pronto
- [ ] Rota de ação **nega com 403** o perfil autenticado sem competência, e manda o **anônimo para o
      login** pelo caminho padrão do Django.
- [ ] Toda execução autorizada que **altera estado** fica registrada: quem, com qual cargo e unidade
      **no momento do ato**, qual ação, **qual operação**, quando.
- [ ] Quando o autor pratica o ato **cobrindo alguém**, o registro diz **por quem ele respondia**;
      quando não, o campo fica vazio.
- [ ] Toda tentativa **negada de perfil autenticado** fica registrada, inclusive a de leitura.
- [ ] Duas operações opostas da mesma ação — conceder e revogar, atribuir e remover — ficam
      **distinguíveis** no registro.
- [ ] A view pode acrescentar ao registro **sobre o que** o ato incidiu; esquecer de fazê-lo não impede
      o registro de existir.
- [ ] A proteção é declarada com o **contrato da ação**, não com uma string solta: slug inexistente é
      erro de import, não negação silenciosa.
- [ ] Ação que declara **alcance** tem a unidade-alvo conferida **pela própria proteção**: alvo fora do
      alcance é negado com **403 antes de a view rodar**, e a negativa fica registrada como as demais.
- [ ] Requisição que **altera estado** de ação com alcance declarado e **não traz o parâmetro do alvo**
      é recusada com **400**; a leitura sem alvo escolhido abre normalmente.

## 3 · Domínio
O ato praticado é a entidade nova, e ela guarda o que descreve o ato **no dia em que foi praticado** —
não o que o cadastro diz hoje.

**`apps/competencias/models/execucao.py`**
```python
class ExecucaoAcao(models.Model):
    acao = models.ForeignKey(Acao, on_delete=models.PROTECT, related_name="acoes_executadas")
    perfil = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="acoes_executadas",
        null=True,
    )
    # Lotação no momento do ato: perfil muda de unidade, e o histórico não pode mudar junto.
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name="acoes_executadas")
    cargo_base = models.ForeignKey(CargoBase, on_delete=models.PROTECT, related_name="acoes_executadas")
    cargo_comissao = models.ForeignKey(
        CargoComissao,
        on_delete=models.PROTECT,
        related_name="acoes_executadas",
        null=True,
    )
    # Ato praticado cobrindo alguém: a pessoa, nunca a linha da Substituicao, que é encerrada e
    # reaberta ao longo do tempo.
    substituindo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="execucoes_cobertas",
        null=True,
        blank=True,
    )
    autorizado = models.BooleanField()
    # A ação é a competência; a operação é o que se fez com ela — atribuir não é remover.
    operacao = models.CharField(max_length=40, blank=True)
    # Entidade territorial não é model (vem de parquet e WFS): o alvo é texto livre. Par de alvos
    # vira identificador composto, em vez de multiplicar colunas por ação.
    alvo_tipo = models.CharField(max_length=40, blank=True)
    alvo_identificador = models.CharField(max_length=120, blank=True)
    momento = models.DateTimeField(auto_now_add=True)
```

E o **contrato conceitual** da ação — o Pydantic de `services/domain/`, não o model projetado acima —
passa a dizer sobre qual unidade ela pode incidir. O alcance fica ao lado de `estrutural`, e não em
`AcaoImplementada`: "sobre o que esta ação pode incidir" é o que a ação **é**, não como ela está montada
no Django.

**`services/domain/autorizacao/contratos.py`**
```python
class TipoAlcance(BaseModel):
    """O que todo alcance é: até onde a ação pode incidir, e o parâmetro do request que carrega o
    id da unidade-alvo. Abstrato — cada alcance concreto é um subtipo, nunca uma instância desta
    classe. Alcance sobre lote, logradouro ou endereço não é subtipo desta classe: é regra de
    domínio de cada ação (§4)."""

    model_config = ConfigDict(frozen=True)

    # O NOME do parâmetro na assinatura da view/formulário — não um id de unidade real. Fixo no
    # código porque é parte da assinatura da ação; o id concreto (de qualquer unidade) só existe em
    # tempo de requisição, e nada aqui pode depender do dado do banco.
    parametro_id_unidade_alvo: str


class UnidadesSubordinadas(TipoAlcance):
    """O alcance de quem dirige: as unidades que o perfil dirige e todas abaixo delas."""

    parametro_id_unidade_alvo: str = "unidade"


class Acao(BaseModel):
    """O que a ação é. Sem rota, sem template, sem Django."""

    model_config = ConfigDict(frozen=True)

    slug: str = Field(pattern=PADRAO_SLUG, max_length=LIMITE_SLUG)
    nome: str = Field(min_length=1, max_length=LIMITE_NOME)
    tooltip: str = Field(min_length=1, max_length=LIMITE_TOOLTIP)
    nome_curto: str | None = Field(default=None, max_length=LIMITE_NOME_CURTO)
    variantes_icone: frozenset[VarianteIcone] = frozenset()
    estrutural: bool = False
    # ALTERADO nesta SPEC: campo novo. Ausente, a ação não incide sobre unidade e não há alvo a
    # conferir — é o caso das que recebem uma entidade territorial. Tipado pelo alcance abstrato:
    # um alcance novo entra como subtipo de `TipoAlcance`, sem mexer neste campo.
    alcance: TipoAlcance | None = None
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`AcaoImplementada`](001-catalogo-de-acoes-em-codigo.md) — "qual ação esta rota executa?"; é o objeto
  que o decorator recebe, não o slug.
- [`Acao` projetada](002-competencia-no-banco.md) — o alvo da FK do registro.
- [`CompetenciaPermissionBackend`](003-avaliador-e-backend-de-autorizacao.md) — "este perfil pode executar esta
  ação?", já respondida; o decorator pergunta por `has_perm` e não reimplementa nada.
- [`substituicao_que_exerce`](../user_admin/015-exercicio-e-substituicao.md) — "quem o autor estava
  cobrindo no momento do ato?".
- [`unidades_dirigidas`](003-avaliador-e-backend-de-autorizacao.md) — "quais unidades este perfil dirige
  hoje?", que é de onde o alcance parte.
- [`PosicaoHierarquica.ego` e `NoHierarquia.ids`](../user_admin/018-arvore-hierarquica.md) — "o que
  pende desta unidade?"; a regra responde por uma unidade, e "unidades subordinadas" é a união do que
  pende de cada uma das dirigidas.

## 4 · Fora de escopo
- Tela de consulta do histórico de execuções — por ora sai pelo admin do Django; sem dono ainda.
- Retenção, expurgo e exportação do registro — sem dono ainda.
- Ação assíncrona ou enfileirada — ações são síncronas por padrão (§3.5).
- Registrar leitura de informação pública da ontologia — não é ação e não exige login.
- Gravar a unidade **em que o ato produziu efeito** quando ela não é a de lotação do autor — sem dono
  ainda (§7).
- Alcance que não seja unidades subordinadas — sem dono ainda; hoje o único subtipo de `TipoAlcance`
  implementado é `UnidadesSubordinadas`.
- A regra das unidades subordinadas em si — SPEC `user_admin/018`, **pré-requisito desta**.
- Conferir alvo que **não é unidade** — lote, logradouro e endereço são regra de domínio de cada ação;
  sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/competencias/backends.py` (SPEC 003) → `has_perm`: a decisão de acesso, já resolvida.
- `@apps/competencias/consulta.py` (SPEC 003) → `canetas_do_perfil`: quem o autor cobre já foi
  resolvido ali, na montagem da avaliação; e `unidades_dirigidas`, a origem do alcance.
- `@apps/competencias/utils.py` (SPEC 001) → `instanciar_acao`: ganha o parâmetro do alcance, com o
  mesmo default do contrato.
- `@apps/user_admin/consulta.py` (SPEC `user_admin/018`) → `posicao_de`: a árvore já sai montada dali,
  sem esta SPEC tocar em `Unidade`.
- `@apps/user_admin/exercicio.py` → `substituicao_que_exerce`: o substituído é `impedimento.perfil`.
- `@apps/competencias/schemas.py` (SPEC 001) → `AcaoImplementada`: é o que o decorator recebe.
- `@apps/competencias/models` (SPEC 002) → `Acao`: alvo da FK do registro.
- `django.contrib.auth.decorators` → `login_required`: o caminho do anônimo é o padrão.
- Skills: `escrever-testes`, `test-django-views`.

## 6 · Snippets

**`apps/competencias/protecao.py`** — a barreira, a conferência do alvo e o rastro no mesmo decorator:
autorizar sem registrar deixaria o rastro dependente de disciplina de quem escreve a view, e conferir o
alvo dentro de cada view deixaria a declaração do contrato sem quem a cumprisse.
```python
def acao_protegida(acao: AcaoImplementada) -> Callable[[ViewFunc], ViewFunc]:
    """Autoriza pelo contrato, confere o alvo declarado e grava a execução — autorizada ou não.

    403 para autenticado, login para anônimo: redirecionar quem já está logado não diz nada, e para
    o HTMX o redirect vira a página de login trocada dentro de um fragmento.

    Grava-se SEMPRE a negativa, e a execução quando ela altera estado: tela de ação é aberta por GET
    a cada navegação e a cada swap, e registrar tudo afogaria o ato de verdade em leitura.
    """

    def decorator(view: ViewFunc) -> ViewFunc:
        @wraps(view)
        def wrapper(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
            if not request.user.is_authenticated:
                ...  # redireciona ao login; nada gravado (Caveats)
            if not request.user.has_perm(acao.slug):
                gravar_execucao(request.user, acao, autorizado=False)
                raise PermissionDenied
            try:
                conferir_alvo(request, acao)
            except PermissionDenied:
                gravar_execucao(request.user, acao, autorizado=False)
                raise
            except BadRequest:
                # Parâmetro ausente ou malformado é requisição errada, não tentativa negada contra
                # o alcance — não gera linha.
                raise
            resposta = view(request, *args, **kwargs)
            # `_registro_ato` só existe se a view chamou `registrar_ato` (ver abaixo). É a ÚNICA
            # ponte entre as duas: a view nunca chama `gravar_execucao`, só deixa esse recado.
            registro = getattr(request, "_registro_ato", None)
            if request.method in METODOS_QUE_ALTERAM or registro is not None:
                gravar_execucao(
                    request.user,
                    acao,
                    autorizado=True,
                    operacao=registro.operacao if registro else "",
                    alvo_tipo=registro.alvo_tipo if registro else "",
                    alvo_identificador=registro.alvo_identificador if registro else "",
                )
            return resposta

        return wrapper

    return decorator


METODOS_QUE_ALTERAM = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def conferir_alvo(request: HttpRequest, acao: Acao) -> None:
    """Segunda barreira do decorator, e a que faz `alcance` valer alguma coisa. Levanta ou passa —
    quem precisa do alvo é a view, que o relê do próprio request.

    Roda DEPOIS do login e do `has_perm`: sem perfil autenticado não há unidade dirigida de onde
    partir, e perguntar o alcance do anônimo seria consulta jogada fora.
    """
    # Ação sem alcance declarado não incide sobre unidade — é o caso das que recebem uma entidade
    # territorial. Nada a conferir.
    if acao.alcance is None:
        return
    id_bruto = _valor_do_parametro(request, acao.alcance.parametro_id_unidade_alvo)
    if id_bruto is None:
        # A ausência tem duas leituras, e é aqui que elas se separam: em leitura é a tela ainda sem
        # alvo escolhido; em requisição que altera estado é alvo faltando, e sem este ramo um POST
        # que omitisse o parâmetro escaparia da conferência inteira.
        if request.method in METODOS_QUE_ALTERAM:
            raise BadRequest(...)
        return
    if not id_bruto.isdigit():
        # Id malformado é 400, não 500: o valor vem do cliente e nunca chega ao `int()` sem passar
        # por aqui.
        raise BadRequest(...)
    id_unidade_alvo = int(id_bruto)
    # Despacha pelo subtipo concreto de `alcance` — cada um tem sua própria regra de pertencimento,
    # e é por isso que `TipoAlcance` é herança e não enum. Alcance novo sem ramo aqui não passa
    # batido: `NotImplementedError` aponta exatamente este ponto de extensão.
    if isinstance(acao.alcance, UnidadesSubordinadas):
        if not _unidade_esta_subordinada(request.user, id_unidade_alvo):
            # Mesmo tratamento da falta de competência: 403 e linha de negativa. Alvo de outro ramo
            # é tentativa de praticar ato onde não se responde, e é isso que o histórico precisa
            # mostrar.
            raise PermissionDenied
    else:
        raise NotImplementedError(
            f"conferência de alvo não implementada para {type(acao.alcance).__name__}"
        )


def _unidade_esta_subordinada(perfil: Perfil, id_unidade_alvo: int) -> bool:
    return id_unidade_alvo in alcance_do_perfil(perfil)


def _valor_do_parametro(request: HttpRequest, parametro: str) -> str | None:
    """POST antes de GET, e string vazia conta como ausente: `select` sem escolha manda o campo com
    valor vazio, que não é um id."""
    ...


@dataclass(frozen=True)
class _RegistroAto:
    """Recado da view para o decorator — detalhe interno de `protecao.py`, nunca importado fora
    daqui. Não é DTO de domínio: não cruza a fronteira de nenhum serviço, só passa de uma função
    para a outra dentro do mesmo request."""

    operacao: str
    alvo_tipo: str
    alvo_identificador: str


def registrar_ato(
    request: HttpRequest,
    operacao: str,
    alvo_tipo: str = "",
    alvo_identificador: str = "",
) -> None:
    """Enriquece o registro que o decorator vai gravar — e força a gravação quando o ato é uma
    leitura (emitir um documento, por exemplo), que o decorator sozinho não registraria.

    Só a view sabe sobre o que o ato incidiu; o registro existe mesmo se ela não disser. A view
    NUNCA chama `gravar_execucao` — só grava este recado; quem lê e persiste é sempre o decorator,
    depois que a view retorna.
    """
    request._registro_ato = _RegistroAto(operacao, alvo_tipo, alvo_identificador)
```

**`apps/competencias/consulta.py`** — a composição que dá nome ao alcance, ao lado da que monta a
avaliação (SPEC 003). Curta porque as duas peças já existem: uma diz de onde partir, a outra diz o que
pende dali.
```python
def alcance_do_perfil(perfil: Perfil) -> frozenset[int]:
    """"Unidades subordinadas" não é conceito, é esta composição: cada unidade que o perfil dirige (SPEC
    003) perguntada à árvore hierárquica (SPEC user_admin/018).

    A regra de lá responde por uma unidade só; dirigir duas é dirigir dois ramos, e o alcance é a
    união deles — a unidade que aparece nos dois entra uma vez, porque o resultado é conjunto.
    """
    return frozenset(
        alcancada
        for dirigida in unidades_dirigidas(perfil)
        for alcancada in posicao_de(dirigida).ego.ids
    )
```

**`apps/competencias/registro_execucao.py`** — a linha gravada, com a lotação do momento e quem o autor
cobria.
```python
def gravar_execucao(
    perfil: Perfil,
    acao: AcaoImplementada,
    autorizado: bool,
    operacao: str = "",
    ...
) -> ExecucaoAcao:
    # A competência que abriu a rota pode ser a de outra pessoa: sem isto a linha descreveria o ato
    # pelo cargo errado, e um subordinado sem chefia figuraria distribuindo competência.
    substituicao = substituicao_que_exerce(perfil)
    ...
```

**`apps/competencias/views.py`** — o decorator já chegou aqui com o alvo conferido; à view sobra o que é
dela.
```python
@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
def definir_atribuicao(request: HttpRequest) -> HttpResponse:
    # Nenhuma conferência de alcance escrita aqui: `ACAO_DEFINIR_ATRIBUICAO` declara o alcance e o
    # decorator o cumpriu. A view que a repetisse duplicaria a regra em cada ação nova — que é o
    # que a declaração existe para evitar.
    ...
    # Só deixa o recado — quem grava é o `wrapper` de `acao_protegida`, depois que esta função
    # retornar. A view nunca importa nem chama `gravar_execucao`.
    registrar_ato(
        request,
        operacao="atribuir",
        alvo_tipo="unidade_acao",
        alvo_identificador=f"{unidade.sigla}:{acao.slug}",
    )
```

## 7 · Caveats
**O registro é gravado pelo decorator, e não por signal.** Signal esconderia do ponto de chamada o
efeito que mais precisa ser visível — e o CLAUDE.md §3.2 o recusa justamente quando o efeito é ato
auditável. Custo: quem lê a view não vê a gravação acontecer em lugar nenhum.

**A conferência do alvo também é do decorator, e não de cada view.** Uma declaração de alcance no
contrato que ninguém cumprisse seria documentação com cara de garantia, e conferência repetida view a
view fica aberta na primeira ação que a esquecer. Custo: `acao_protegida` acumula três
responsabilidades — autorizar, conferir o alvo e gravar —, e nenhuma delas aparece na view que ele
protege.

**A ação nomeia o parâmetro do alvo por string, e a requisição que altera estado é obrigada a
carregá-lo.** Sem o nome declarado o decorator não acha a unidade em requisições de formatos diferentes,
e sem a obrigatoriedade a ausência do parâmetro viraria porta de saída da conferência. Custo: o nome no
contrato e o `name` do campo no template divergem sem ninguém avisar — o 400 do POST é o que contém o
erro —, e uma ação futura cujo POST identificaria o alvo só pelo id da linha filha passa a ter de mandar
a unidade junto.

**O alcance fica só no registro em código, sem coluna na projeção**, ao contrário de `estrutural`. Quem
o lê é o decorator, que já tem o contrato em mãos, e uma coluna que ninguém consulta é o mesmo dado em
dois lugares livres para divergir. Custo: o admin não mostra o alcance de cada ação, e conferi-lo exige
abrir `acoes_declaradas.py`.

**A conferência de pertencimento é despachada por `isinstance` no corpo de `conferir_alvo`, um `if` por
subtipo de `TipoAlcance`, não um método de cada subtipo.** A regra depende de `alcance_do_perfil`
(`apps/competencias/consulta.py`), que por sua vez depende de `unidades_dirigidas` e `posicao_de` —
peças do app, não do domínio (§3.3 proíbe `services/domain/` de depender de `apps/`); um método em
`UnidadesSubordinadas` teria que carregar essa dependência para dentro do contrato Pydantic. Custo:
diferente do slug de ação inexistente (erro de import, §2), um `TipoAlcance` novo sem ramo no
`isinstance` de `conferir_alvo` só estoura `NotImplementedError` na primeira requisição que exercitar
aquela ação — declarar o alcance no contrato
não obriga, sozinho, a estender o dispatcher.

**O alcance é recalculado a cada requisição protegida, sem cache** — ao contrário dos slugs liberados,
que a SPEC 003 guarda na instância de usuário. Cachear exigiria invalidar a cada mudança de organograma
ou de titularidade, que é o mesmo problema que a 003 já assume e resolveu adiando. Custo: toda
requisição de ação com alcance carrega a árvore inteira (SPEC `user_admin/018`) uma vez por unidade
dirigida, e refaz por dentro de `unidades_dirigidas` as canetas que o `has_perm` da mesma requisição
acabou de montar.

**Grava-se toda negativa e só a execução que altera estado.** Uma tela de ação é aberta por GET a cada
navegação e a cada swap do HTMX, e registrar tudo encheria o histórico de "atos" que são leitura. Custo:
ação cujo ato **é** uma leitura — emitir um documento — só fica registrada se a view chamar
`registrar_ato`, e esquecer disso não quebra nada visivelmente.

**Acesso anônimo não gera registro.** Ele é redirecionado ao login antes de haver perfil, unidade e
cargo, que são os campos que dão sentido à linha. Custo: varredura de URL por quem não está logado não
aparece no histórico de atos — só no log do servidor.

**O alvo é texto livre, em dois campos opcionais.** Lote, logradouro e endereço não são models — vêm dos
parquets e do WFS —, e `GenericForeignKey` não os alcança. Custo: nada garante que o identificador
gravado ainda exista nem que esteja bem formado, e consultar o histórico por alvo é busca em texto.

**Cargo e unidade são copiados para a linha, mas a sigla não.** Sem a cópia, a consulta de amanhã
descreveria o ato de ontem com a lotação de hoje. Custo aceito: renomear a sigla de uma unidade reescreve
como todo o histórico dela se lê.

**A unidade gravada é a de lotação do autor, não aquela em que o ato produziu efeito.** Quem cobre alguém
de outra unidade (SPEC `user_admin/015`) pratica o ato pela caneta do coberto, e fazer o decorator
descobrir qual caneta autorizou exigiria o avaliador devolver a origem de cada slug liberado. Custo: nesse
caso a unidade da linha descreve onde o autor está lotado, e chegar à unidade do ato exige passar por
`substituindo`.

## 8 · Testes (TDD)
Todos exercitam view real com `Perfil` gravado e carregam o marker `banco`. A regra das unidades
subordinadas é testada na SPEC `user_admin/018`; aqui se fixa a composição dela com as unidades
dirigidas.

- `test_rota_confere_o_alvo_declarado` — POST com unidade fora do alcance de subordinadas recebe 403 e deixa
  linha de negativa; POST sem o parâmetro declarado é recusado com 400 antes de a view rodar; e o GET
  sem alvo escolhido abre normalmente. *(marker `banco`)*

- `test_rota_nega_autenticado_sem_competencia_com_403` — perfil logado sem concessão recebe 403, não
  redirect. *(marker `banco`)*
- `test_rota_manda_anonimo_para_o_login` — anônimo é redirecionado, não recebe 403, e não deixa linha.
  *(marker `banco`)*
- `test_execucao_autorizada_fica_registrada_com_a_lotacao_do_momento` — o POST autorizado guarda unidade
  e cargos vigentes no ato, e mudar a lotação do perfil depois não altera a linha gravada.
  *(marker `banco`)*
- `test_ato_praticado_em_substituicao_diz_por_quem_responde` — o substituto que age pela competência do
  afastado deixa gravado quem ele cobria; quem age por competência própria deixa o campo vazio.
  *(marker `banco`)*
- `test_tentativa_negada_fica_registrada` — o 403 também deixa rastro, marcado como não autorizado.
  *(marker `banco`)*
- `test_leitura_autorizada_nao_vira_registro` — o GET autorizado da tela não gera linha; o mesmo GET
  negado gera. *(marker `banco`)*
- `test_operacoes_opostas_ficam_distinguiveis` — duas operações da mesma ação geram registros que se
  distinguem pela operação gravada. *(marker `banco`)*
- `test_alvo_e_opcional_no_registro` — view que informa o alvo o grava; view que não informa gera registro
  mesmo assim. *(marker `banco`)*
