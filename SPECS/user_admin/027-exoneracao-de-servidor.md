---
spec: user_admin/027
versao: v2
atualizado_em: 2026-08-31
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: listagem de servidores ganha o alternador "Mostrar servidores exonerados" (mesmo gesto do
    toggle de unidades extintas, SPEC 025), desligado por padrão, e `candidatos_a_titular` passa a
    excluir quem está fora do quadro — a garantia do item "Exonerado não recebe nada de novo" tinha
    lacuna nesse candidato; caveat da dependência da SPEC 025 corrigido — ela já está implementada
---

# SPEC user_admin/027 — Exoneração e reintegração de servidor

## 1 · User story
O servidor da DIMAP que dirige um ramo do organograma exonera um servidor lotado abaixo dele, e o
reintegra quando preciso, para que quem não integra mais o quadro deixe de entrar no sistema e de
exercer competência no mesmo ato.

## 2 · Condições de pronto
- [ ] A exoneração é praticada por **três portas** — o botão da seção Exercício da página do
      servidor, a coluna própria na tabela de servidores e o card **Exonerar servidor**, no grupo
      Servidores da aba Recursos Humanos do painel, que escolhe unidade e servidor —, servidas pela
      mesma competência e pelo mesmo modal, cuja **face é escolhida pelo estado do servidor**:
      vigente, a prévia da exoneração; exonerado, a confirmação da reintegração.
- [ ] Confirmada a exoneração, o servidor **deixa de entrar**: a sessão aberta dele não resolve no
      request seguinte e a próxima navegação cai no login.
- [ ] O ato é **um só, ou nenhum**: larga a titularidade da unidade que ele dirigia, encerra os
      impedimentos em aberto e as coberturas das duas pontas, encerra as delegações que ele recebeu e
      retira dele a condição de administrador.
- [ ] **Exonerado não exerce competência nenhuma** — nem a estrutural, nem a delegada, nem a do
      superusuário: a rota protegida recusa com 403 e **registra a negativa**, o painel não lhe
      oferece card de ação algum e nenhum botão de ato é renderizado para ele.
- [ ] A unidade que perdeu o titular passa a **aceitar a designação do próximo** no mesmo instante, e
      acende o alarme de unidade sem direção enquanto ninguém for designado.
- [ ] O selo **Exonerado** ganha a **data do ato** na página do servidor e na listagem, e a seção
      Exercício mostra a face de quem não integra mais o quadro.
- [ ] O ato é **recusado por inteiro, sem gravar nada**: exonerar a si mesmo, exonerar quem já está
      exonerado, reintegrar quem não está exonerado, e reintegrar para unidade extinta — esta última
      nomeando a sigla a reativar primeiro. A recusa vale **inclusive para o superusuário**.
- [ ] A reintegração devolve o **acesso e nada mais**: não devolve titularidade, coberturas,
      delegações nem a condição de administrador, que se refazem por seus próprios atos.
- [ ] **Exonerado não recebe nada de novo**: não é candidato a titular, a substituto nem a delegado, e
      a recusa alcança o superusuário — as telas já não o oferecem, mas quem barra é a gravação.
- [ ] A listagem de servidores ganha o alternador **Mostrar servidores exonerados** — mesmo gesto do
      toggle "Mostrar unidades extintas" (SPEC 025), reusando `.toggle-onsen` e `.barra-acoes-chave`
      tal como estão —, **desligado por padrão**: quem sai do quadro sai também da lista, até alguém
      pedir para revê-lo. Ligado, a linha volta com o selo **Exonerado**, e o estado sobrevive à
      filtragem seguinte, como o de unidades extintas.
- [ ] O design foi aprovado no **mock**, e as peças novas foram portadas para
      `static/src/tema-dimap.dev.css` e renderizadas no styleguide antes de qualquer template da
      aplicação usá-las.

## 3 · Domínio
A ação consome o exercício ([user_admin/015](015-exercicio-e-substituicao.md)) — a quem pergunta **o
que prende o servidor à cadeira** —, a destituição de titular
([user_admin/026](026-titularidade-como-ato-administrativo.md)), que já derruba as delegações feitas
por ele na unidade e as substituições daquela titularidade, a condição de administrador
([user_admin/022](022-tornar-administrador.md)), a delegação nominal
([autorizacao/009](../autorizacao/009-delegacao-de-competencia-estrutural.md)) e a extinção de
unidade ([user_admin/025](025-extincao-de-unidade.md)), a quem pergunta **se ainda há lotação para
onde voltar**.

Exoneração continua sendo o `is_active`, que é quem barra a entrada, e ganha ao lado a **data do
ato** — não um segundo booleano, mas o dia em que a pessoa saiu do quadro, que o selo e o histórico
leem sem consultar o registro de execução. Os dois são um valor só, e uma `CheckConstraint` torna a
discordância entre eles impossível em vez de vigiada.

**`apps/user_admin/models/user.py`**
```python
class Perfil(AbstractBaseUser, PermissionsMixin):
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    e_titular = models.BooleanField(default=False)
    # ALTERADO nesta SPEC: o dia do ato que tirou a pessoa do quadro. Nula é servidor no quadro, e é
    # o que a reintegração devolve.
    exonerado_em = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unidade"],
                condition=Q(e_titular=True),
                name="unidade_tem_um_titular",
            ),
            models.UniqueConstraint(
                fields=["email"],
                condition=~Q(email=""),
                name="email_unico_quando_preenchido",
                violation_error_code="unique",
                violation_error_message="Já existe servidor cadastrado com este e-mail.",
            ),
            # ALTERADO nesta SPEC: os dois campos dizem a mesma coisa e são gravados pelo mesmo ato.
            # A regra é da linha, então é do banco.
            models.CheckConstraint(
                condition=Q(is_active=True, exonerado_em__isnull=True)
                | Q(is_active=False, exonerado_em__isnull=False),
                name="perfil_exonerado_tem_data",
            ),
        ]

    # Inalterado: `is_active` segue sendo a fonte, porque é ele que o ModelBackend lê para recusar a
    # sessão. `exonerado_em` é a data do mesmo fato, não uma segunda resposta a ele.
    @property
    def exonerado(self) -> bool:
        return not self.is_active
```

As duas faces do ato são dois DTOs simétricos: o que se perde e o que volta. Cada um é o que a tela
mostra antes de perguntar **e** o que a regra decide.

**`services/domain/exoneracao/models.py`**
```python
class IdentidadeServidor(BaseModel):
    """O servidor projetado: o domínio não conhece o model, e do model só precisa disto."""

    model_config = ConfigDict(frozen=True)

    servidor_id: int
    rf: str
    nome_completo: str


class PreviaDaExoneracao(BaseModel):
    model_config = ConfigDict(frozen=True)

    servidor: IdentidadeServidor
    # A sigla da unidade que fica sem titular. Ausente é quem não dirige nada.
    unidade_que_dirige: str | None
    impedimentos_em_aberto: int
    coberturas_em_curso: int
    delegacoes_recebidas: int
    administrador: bool
    ja_exonerado: bool = False
    # Quem assina não se retira do quadro: a recusa é da relação entre alvo e autor, não do alvo.
    eh_o_proprio_autor: bool = False


class PreviaDaReintegracao(BaseModel):
    """O reverso: o que volta, não o que sai."""

    model_config = ConfigDict(frozen=True)

    servidor: IdentidadeServidor
    exonerado_em: date | None
    # A lotação que ele guardou, e para onde volta. Extinta, não há para onde.
    unidade: str
    unidade_extinta: bool
    ja_no_quadro: bool = False


class Veredito(BaseModel):
    """Um só para as duas faces: a pergunta muda, a resposta tem a mesma forma."""

    model_config = ConfigDict(frozen=True)

    pode: bool
    motivo: str = ""
```

O alternador da listagem é o mesmo padrão do toggle de unidades extintas (SPEC 025): a linha
materializada carrega a marca que o template lê, e quem decide se ela entra na lista é a borda que
consulta o banco — não o domínio, que não sabe o que é uma tela.

**`services/domain/listagem_gestao/models/servidores.py`**
```python
class LinhaServidor(BaseModel):
    ...
    impedido: bool
    # SPEC user_admin/027: marca a linha quando o toggle "Mostrar servidores exonerados" a revela —
    # mesmo padrão de LinhaUnidade.extinta (SPEC 025).
    exonerado: bool = False
```

**Mock:** [027-mock-exoneracao-de-servidor.html](027-mock-exoneracao-de-servidor.html) — leia a
skill `mock`.

## 4 · Fora de escopo
- Exonerar com data retroativa ou agendada: o ato vale hoje, e o campo não é preenchido pela tela —
  sem dono ainda.
- Devolver titularidade, coberturas, delegações e condição de administrador ao reintegrado — feito à
  mão, pelos atos das SPECs 014, 024, autorizacao/009 e 022; sem dono ainda.
- Transferir a lotação do exonerado ou apagá-la: ele guarda a unidade em que estava, que é o que a
  página dele mostra — sem dono ainda.
- Excluir o cadastro do servidor: exoneração é saída do quadro, não apagamento de histórico — sem
  dono ainda.
- Marcar "exonerado" ao lado do nome nas telas de histórico de execução — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/competencias/protecao.py` → `acao_protegida`, `conferir_alvo`, `pode_executar`: barreira,
  conferência do alvo e a mesma resposta na forma da tela.
- `@apps/competencias/resolucao.py` → `slugs_liberados`: o conjunto que alimenta a cascata do painel.
- `@apps/painel/abas_declaradas.py` → `ABA_RECURSOS_HUMANOS`, `ItemAcao`, `PARTIAL_CARTAO_MODAL`: o
  card da ação e a forma que ele toma quando a rota abre modal.
- `@apps/competencias/utils.py` → `instanciar_acao`: construção do contrato da ação.
- `@apps/user_admin/exercicio.py` → `retornar_ao_exercicio`, `impedimentos_em_aberto`: o encerramento
  de impedimento e cobertura que já decide entre encurtar e apagar.
- `@apps/user_admin/substituicao.py` → `encerrar_substituicao_em`: a cobertura truncada num dia.
- `@apps/unidades/titularidade.py` → `destituir_titular`: a marca de titular largada, com as
  delegações feitas por ele na unidade e as substituições daquela titularidade encerradas junto.
- `@apps/user_admin/administrador.py` → `recusa_de_auto_revogacao`, `DesfechoAdministrador`: a recusa
  de quem assina contra si mesmo e a forma de desfecho dos atos sobre servidor.
- `@apps/user_admin/formularios.py` → `traduzir_recusa`: erro bruto → mensagem em português e
  controle realçado.
- `@templates/user_admin/partials/_modal_retorno.html` → a forma de um modal de confirmação sem
  formulário: tarja, dois botões, nada a preencher.
- `@apps/unidades/schemas.py` → `ConsultaDeUnidades`, `@apps/unidades/views.py` → `painel_unidades`,
  `@templates/unidades/partials/_barra_acoes_unidades.html` e `_tabela_unidades.html`: o par
  toggle + campo oculto que o alternador de exonerados reproduz na listagem de servidores.
- `@apps/unidades/titularidade.py` → `candidatos_a_titular`: filtro que passa a excluir quem está
  fora do quadro, mesmo filtro que `candidatos_a_delegado` já aplica.
- Skills: `acao-administrativa`, `painel`, `componentes-frontend`, `mock`, `erros-de-formulario`,
  `escrever-testes`.

## 6 · Snippets

O contrato: estrutural como as demais ações de cadastro, e com o alcance de um alvo só que já
existe — a unidade sai da lotação do servidor, lida no banco, e nunca chega pelo corpo da requisição.

**`apps/user_admin/acoes_declaradas.py`**
```python
ACAO_EXONERAR_SERVIDOR = instanciar_acao(
    slug="user_admin.exonerar_servidor",
    nome="Exonerar servidor",
    nome_curto="Exonerar",
    tooltip="Retira o servidor do quadro da DIMAP — e o reintegra.",
    # Precisa reverter sem argumento (`competencias.E004`): é a rota do modal direto, e não as de
    # gravação, que recebem o servidor no caminho.
    url_name="user_admin:modal_exonerar_servidor",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Titular da área a exerce por dirigir, sem concessão gravada — e é por ser estrutural que ela é
    # delegável (SPEC autorizacao/009).
    estrutural=True,
    # Um alvo só, e ele é uma PESSOA: a unidade sai da lotação dela, lida no banco.
    alcance=LotacaoDoServidor(),
)
```

**`apps/competencias/registro.py`**
```python
def _construir_registro() -> RegistroAcoes:
    # Não há autodiscover, e é deliberado: a inscrição é a linha que distingue ato administrativo de
    # rota que só exige login.
    return RegistroAcoes(acoes=(..., ACAO_EXONERAR_SERVIDOR))
```

O card, no fim do grupo que já é o ciclo do cadastro. `PARTIAL_CARTAO_MODAL` porque o `url_name` da
ação abre um fragmento sem `{% extends "base.html" %}`: um `<a href>` levaria o clique ao HTML cru.
Reintegrar não ganha card próprio — é a segunda face do mesmo modal, e quem a escolhe é o estado do
servidor.

**`apps/painel/abas_declaradas.py`**
```python
ABA_RECURSOS_HUMANOS = Aba(
    ...
    grupos=(
        Grupo(
            rotulo="Servidores",
            itens=(
                ItemLivre(slug="painel.lista_servidores", ...),
                ItemAcao(acao=ACAO_CRIAR_SERVIDOR),
                # Consultar, cadastrar, exonerar: a ordem declarada é a ordem exibida, e é a ordem
                # em que o ciclo acontece. Sem esta linha, `painel.E004` derruba a subida.
                ItemAcao(acao=ACAO_EXONERAR_SERVIDOR, partial=PARTIAL_CARTAO_MODAL),
            ),
        ),
        ...
    ),
)
```

O guardrail nas três portas. O avaliador de competência já zera o conjunto de quem não está em
exercício, mas o superusuário nunca chega até ele: `PermissionsMixin.has_perm` responde `True` antes
de consultar backend algum. As três linhas abaixo são o que faz a recusa não depender do
`ModelBackend` do Django ter desautenticado a sessão primeiro.

**`apps/competencias/protecao.py`**
```python
def acao_protegida(acao: AcaoImplementada) -> Callable[[ViewFunc], ViewFunc]:
    def decorator(view: ViewFunc) -> ViewFunc:
        @wraps(view)
        def wrapper(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            perfil = cast(Perfil, request.user)
            # ANTES do has_perm, e sem saída para o superusuário: quem saiu do quadro não pratica
            # ato administrativo nenhum, e a tentativa fica registrada como qualquer outra negativa.
            if perfil.exonerado:
                gravar_execucao(perfil, acao, autorizado=False)
                raise PermissionDenied
            if not perfil.has_perm(acao.acao.slug):
                ...


def pode_executar(
    usuario: Perfil | AnonymousUser,
    acao: AcaoImplementada,
    id_unidade_alvo: int | None = None,
) -> bool:
    # A mesma recusa do decorator, na forma de que a tela precisa — inclusive para o superusuário,
    # que passaria direto pelo `has_perm` abaixo.
    if getattr(usuario, "exonerado", False):
        return False
    if not usuario.has_perm(acao.acao.slug):
        return False
    ...
```

**`apps/competencias/resolucao.py`**
```python
def slugs_liberados(usuario: Perfil | AnonymousUser) -> frozenset[str]:
    # A cascata do painel some com todo card de AÇÃO do exonerado pelo mesmo motivo: o atalho do
    # superusuário abaixo devolveria o registro inteiro a quem a rota vai recusar card por card. O
    # item livre não passa por aqui e continua de pé — ele não é ato.
    if getattr(usuario, "exonerado", False):
        return frozenset()
    if getattr(usuario, "is_superuser", False):
        return frozenset(item.acao.slug for item in REGISTRO.todas())
    return frozenset(usuario.get_all_permissions())
```

As duas regras, sem banco, no mesmo módulo: só sai do quadro quem está nele e não é quem assina, e só
volta quem está fora e tem lotação de pé para onde voltar.

**`services/domain/exoneracao/avaliador.py`**
```python
MOTIVO_JA_EXONERADO = "Este servidor já foi exonerado."
MOTIVO_NO_QUADRO = "Este servidor não está exonerado."
MOTIVO_AUTO_EXONERACAO = (
    "Você não pode exonerar a si mesmo: peça a quem dirige a unidade superior."
)
MOTIVO_UNIDADE_EXTINTA = "Reative antes a {sigla}: um servidor não é lotado em unidade extinta."


class AvaliadorExoneracao:
    def __call__(self, previa: PreviaDaExoneracao) -> Veredito:
        # Antes de tudo: o POST repetido chega com o servidor já fora do quadro.
        if previa.ja_exonerado:
            return Veredito(pode=False, motivo=MOTIVO_JA_EXONERADO)
        if previa.eh_o_proprio_autor:
            return Veredito(pode=False, motivo=MOTIVO_AUTO_EXONERACAO)
        return Veredito(pode=True)


class AvaliadorReintegracao:
    def __call__(self, previa: PreviaDaReintegracao) -> Veredito:
        if previa.ja_no_quadro:
            return Veredito(pode=False, motivo=MOTIVO_NO_QUADRO)
        if previa.unidade_extinta:
            return Veredito(
                pode=False,
                motivo=MOTIVO_UNIDADE_EXTINTA.format(sigla=previa.unidade),
            )
        return Veredito(pode=True)
```

O encerramento de impedimento e cobertura já existe e já decide entre encurtar e apagar; o que muda
entre voltar ao exercício e sair do quadro é **qual recorte** se encerra e **em que dia**. O recorte
desce como dado, e nenhuma das duas regras é reescrita.

**`apps/user_admin/exercicio.py`**
```python
def encerrar_impedimentos(impedimentos: QuerySet[Impedimento], dia: date) -> None:
    """Extraída de `retornar_ao_exercicio`, que já a executava sobre os vigentes: trunca as
    coberturas em aberto e depois cada impedimento, um a um — o que ainda não vigorou é apagado, não
    encerrado."""
    for substituicao in Substituicao.objects.filter(
        q_em_aberto_em(dia),
        impedimento__in=impedimentos,
    ):
        encerrar_substituicao_em(substituicao, dia)
    for impedimento in impedimentos:
        _encerrar_impedimento_em(impedimento, dia)


def retornar_ao_exercicio(perfil: Perfil) -> None:
    # A véspera, e não hoje: o período é inclusivo no fim, e quem volta ao exercício volta agora.
    hoje = timezone.localdate()
    with transaction.atomic():
        encerrar_impedimentos(
            Impedimento.objects.filter(q_vigente_em(hoje), perfil=perfil),
            hoje - DIA,
        )
```

O ato, na borda. Uma transação por operação, e a ordem importa: a titularidade sai primeiro porque é
ela que destrava a designação do próximo, e o `is_active` sai por último porque é o único passo que a
`CheckConstraint` observa.

**`apps/user_admin/exoneracao.py`**
```python
@dataclass(frozen=True)
class DesfechoExoneracao:
    """Mesma forma do `DesfechoAdministrador` (SPEC 022): gravou (`perfil`) ou recusou (`recusa`).
    Serve às duas operações — o que muda entre elas é o que a transação faz, não o recado à view."""

    perfil: Perfil | None
    recusa: RecusaDeFormulario = RecusaDeFormulario()


def exonerar_servidor(comando: ComandoExoneracao, hoje: date) -> DesfechoExoneracao:
    servidor = get_object_or_404(Perfil.objects.select_related("unidade"), pk=comando.servidor_id)
    veredito = avaliar_exoneracao(previa_da_exoneracao(servidor, autor_id=comando.autor_id))
    if not veredito.pode:
        return DesfechoExoneracao(perfil=None, recusa=_recusa(veredito.motivo))
    with transaction.atomic():
        # Primeiro: enquanto a marca estiver de pé, a `UniqueConstraint` de um titular por unidade
        # recusa a designação do próximo, e a unidade fica travada sem direção. É a destituição da
        # SPEC 026 que leva junto as delegações FEITAS por ele e as substituições da titularidade.
        if servidor.e_titular:
            destituir_titular(servidor.unidade)
        # Hoje, e não a véspera: o afastamento valeu até o dia em que a pessoa saiu do quadro. O
        # que ainda não vigorou é apagado lá dentro, e as coberturas caem junto.
        encerrar_impedimentos(impedimentos_em_aberto(servidor), hoje)
        _encerrar_coberturas_exercidas(servidor, hoje)
        _encerrar_delegacoes_recebidas(servidor, hoje)
        servidor.is_superuser = False
        servidor.is_staff = False
        servidor.is_active = False
        servidor.exonerado_em = hoje
        servidor.save(
            update_fields=[
                "is_superuser",
                "is_staff",
                "is_active",
                "exonerado_em",
            ],
        )
    return DesfechoExoneracao(perfil=servidor)


def reintegrar_servidor(comando: ComandoExoneracao) -> DesfechoExoneracao:
    """O reverso devolve o acesso e nada mais: titularidade, cobertura, delegação e caneta de
    administrador se refazem por seus próprios atos."""
    servidor = get_object_or_404(Perfil.objects.select_related("unidade"), pk=comando.servidor_id)
    veredito = avaliar_reintegracao(previa_da_reintegracao(servidor))
    if not veredito.pode:
        return DesfechoExoneracao(perfil=None, recusa=_recusa(veredito.motivo))
    servidor.is_active = True
    servidor.exonerado_em = None
    servidor.save(update_fields=["is_active", "exonerado_em"])
    return DesfechoExoneracao(perfil=servidor)


def _encerrar_coberturas_exercidas(servidor: Perfil, dia: date) -> None:
    # A outra ponta da substituição: as que ele EXERCE sobre o impedimento de terceiros. As do
    # próprio impedimento dele caem com o impedimento, em `encerrar_impedimentos`.
    for substituicao in Substituicao.objects.filter(q_em_aberto_em(dia), substituto=servidor):
        encerrar_substituicao_em(substituicao, dia)


def _encerrar_delegacoes_recebidas(servidor: Perfil, dia: date) -> None:
    # A outra ponta da delegação: as que ele RECEBEU. As que ele fez como titular caem com a
    # destituição (SPEC 026), e as duas pontas nunca se sobrepõem.
    # Importado aqui dentro, como em `competencias/consulta.py`: `competencias` já importa
    # `user_admin` no topo, e o import de módulo fecharia o ciclo.
    from apps.competencias.models.delegacao import Delegacao

    Delegacao.objects.filter(q_em_aberto_em(dia), delegado=servidor).update(data_fim=dia)
```

A view, fina: o DTO na fronteira, o ato no módulo e o recado que o decorator lê depois do `return` —
é a `operacao` que separa os dois atos opostos no histórico.

**`apps/user_admin/views.py`**
```python
@acao_protegida(ACAO_EXONERAR_SERVIDOR)
@require_POST
def gravar_exoneracao(request: HttpRequest, servidor: int) -> HttpResponse:
    comando = ComandoExoneracao(servidor_id=servidor, autor_id=request.user.pk)
    desfecho = exonerar_servidor(comando, timezone.localdate())
    if desfecho.perfil is None:
        return render(request, TEMPLATE_MODAL, contexto_da_recusa(servidor, desfecho.recusa))
    registrar_ato(
        request,
        operacao="exonerar",
        alvo_tipo="servidor",
        alvo_identificador=desfecho.perfil.rf,
    )
    return render(request, TEMPLATE_PAGINA, contexto_do_servidor(desfecho.perfil))
```

O alternador da listagem — mesmo par toggle + campo oculto de `_barra_acoes_unidades.html` e
`_tabela_unidades.html`, sem manager novo em `Perfil`: o recorte é da borda que materializa a linha,
não do `objects` que o resto do sistema usa para achar o exonerado (a própria página dele, a
reintegração).

**`apps/user_admin/context.py`**
```python
def _linhas_de_servidores(com_exonerados: bool = False) -> list[LinhaServidor]:
    perfis = Perfil.objects.select_related("unidade", "cargo_base", "cargo_comissao").order_by(
        "nome", "sobrenome"
    )
    if not com_exonerados:
        perfis = perfis.filter(is_active=True)
    return [_linha_do_perfil(perfil) for perfil in perfis]
```

E a lacuna que o item "Exonerado não recebe nada de novo" cobra: `candidatos_a_delegado` já filtra
`is_active=True`, e a designação de substituto já recusa pelo `Substituto.exonerado` do avaliador
(SPEC 015) — só `candidatos_a_titular` faltava.

**`apps/unidades/titularidade.py`**
```python
def candidatos_a_titular(unidade: Unidade) -> list[Perfil]:
    lotados = Perfil.objects.filter(
        unidade=unidade,
        cargo_comissao__isnull=False,
        is_active=True,
    ).select_related("cargo_comissao")
    ...
```

## 7 · Caveats

A ação mora em `user_admin` em vez de app próprio, contrariando o §3.5 do CLAUDE.md. Administrar o
quadro de servidores não é processo da DIMAP e opera sobre os models deste app, que já hospeda as
quatro ações de cadastro pela mesma exceção declarada. O custo é um app que concentra cinco ações e
cresce mais que os demais.

`exonerado_em` é o mesmo fato que `is_active` guardado em duas colunas, contrariando a decisão da
SPEC 015 de não pôr campo ao lado dele. A data não é uma segunda resposta a "está no quadro?" — é
*quando* saiu, que o selo e a listagem leem sem varrer o registro de execução —, e a
`CheckConstraint` torna a discordância impossível em vez de vigiada. O custo é que toda escrita de
`is_active` passa a ter que escrever os dois: a carga de fictícios e os testes que hoje gravam
`is_active=False` direto precisam acompanhar, e a migração que cria a constraint precisa de uma
migração de dados antes dela, preenchendo a data de quem já está inativo.

A exoneração acumula os efeitos de quatro atos que existem separados — destituir titular, encerrar
impedimento, encerrar cobertura, retirar administrador — numa transação só. Ela é a saída do quadro,
e deixar qualquer um desses vínculos de pé é deixar o sistema afirmando duas coisas sobre a mesma
pessoa. O custo é que este módulo passa a conhecer titularidade, exercício e delegação ao mesmo
tempo, e cada vínculo novo que a plataforma criar sobre `Perfil` terá que lembrar de cair aqui.

A recusa da reintegração para unidade extinta depende do `extinta_em` da SPEC 025 — **implementada**
desde 2026-08-31 (commit `08916dc`), o que destrava esta SPEC. A alternativa — reintegrar para
unidade extinta e deixar a inconsistência para alguém notar — recriaria por baixo o ramo que a
extinção desfez.

A linha exonerada da listagem reusa `.linha-extinta` (tinta de erro sobre a linha), o mesmo token
de "vínculo administrativo encerrado" que unidade extinta já usa — em vez de um `.linha-exonerado`
novo que pintaria de propósito o mesmo tom. O custo é o nome da classe não bater com o texto que ela
tinge; o selo `Exonerado` ao lado é quem desfaz a ambiguidade.

O guardrail de `acao_protegida` é redundante enquanto a autenticação for o `ModelBackend`, que já
recusa resolver a sessão do `is_active=False` a cada request. Ele existe porque essa recusa é
encanamento do Django e não regra deste sistema: um `force_login`, um management command ou um
backend novo entregariam ao decorator um `Perfil` exonerado, e o superusuário atravessaria `has_perm`
sem tocar no avaliador que hoje contém todo mundo. O custo é uma consulta a atributo por request
protegido, e uma regra escrita em dois lugares — aqui e no avaliador de competência.

## 8 · Testes (TDD)

**Comportamento**
- `test_exoneracao_larga_tudo_num_ato_so` — titular com impedimento em aberto, cobertura exercida,
  delegação recebida e marca de administrador sai do quadro com os quatro vínculos encerrados e a
  data gravada. *(marker `banco`)*
- `test_titularidade_largada_libera_a_designacao_do_proximo` — designar outro titular para a unidade
  do exonerado é aceito, sem esbarrar na unicidade. *(marker `banco`)*
- `test_impedimento_futuro_e_apagado_e_o_vigente_e_encerrado_hoje` — o que não chegou a vigorar some,
  o que vigorava termina no dia da exoneração, e as coberturas de cada um acompanham. *(marker
  `banco`)*
- `test_exonerado_nao_autentica` — sessão aberta antes do ato não resolve no request seguinte e a
  navegação cai no login. *(marker `banco`)*
- `test_banco_recusa_exoneracao_sem_data` — gravar `is_active=False` deixando `exonerado_em` nula
  levanta `IntegrityError`, e o inverso também. *(marker `banco`)*
- `test_avaliador_recusa_auto_exoneracao_e_quem_ja_saiu` — as duas recusas da face de exoneração,
  cada uma com seu motivo.
- `test_avaliador_recusa_reintegracao_de_quem_esta_no_quadro_e_de_unidade_extinta` — as duas recusas
  da face de reintegração, e a segunda nomeia a sigla a reativar.
- `test_recusa_nao_grava_nada` — exonerar a si mesmo devolve a tarja e deixa titularidade,
  impedimentos, coberturas, delegações e `is_active` como estavam. *(marker `banco`)*
- `test_reintegracao_devolve_so_o_acesso` — o servidor volta a entrar sem titularidade, sem
  cobertura, sem delegação e sem a condição de administrador. *(marker `banco`)*
- `test_exonerado_some_da_listagem_ate_o_toggle_revela` — a linha soma no total desligado, some do
  corpo da tabela, e volta com o selo Exonerado quando `?exonerados=1`; o estado sobrevive à
  filtragem seguinte. *(marker `banco`)*
- `test_exonerado_nao_e_candidato_a_titular` — servidor fora do quadro, com cargo em comissão
  compatível e lotado na unidade, não entra em `candidatos_a_titular`. *(marker `banco`)*

**Segurança da ação** *(bateria da skill `acao-administrativa`; todos com marker `banco`)*
- `test_anonimo_vai_ao_login_sem_registrar` — a rota de gravação redireciona e não gera linha.
- `test_autenticado_sem_competencia_recebe_403_e_fica_registrado` — quem não dirige nem recebeu
  concessão é recusado, com negativa gravada.
- `test_dirigente_de_outro_ramo_recebe_403` — servidor-alvo com id válido, lotado fora do alcance de
  quem assina, é recusado antes de a view rodar.
- `test_estrutural_dispensa_concessao_gravada` — quem responde pela direção da unidade do alvo
  executa sem concessão; quem não dirige e não tem concessão, não.
- `test_impedido_recebe_403_e_exonerado_302` — titular com impedimento vigente é recusado ao praticar
  o ato; titular exonerado chega como anônimo e recebe 302 para o login, sem linha de negativa.
- `test_perfil_exonerado_injetado_no_decorator_recebe_403_e_fica_registrado` — `acao_protegida`
  chamado com um `Perfil` exonerado no request, **inclusive superusuário**, recusa e grava a
  negativa, sem depender da desautenticação do `ModelBackend`.
- `test_exonerado_nao_enxerga_acao_alguma` — `slugs_liberados` devolve vazio e `pode_executar`
  devolve `False` para o exonerado superusuário; o painel dele resolve sem card de ação nenhum, e os
  itens livres continuam de pé.
- `test_registro_distingue_exonerar_de_reintegrar` — as duas operações gravam quem, cargo e unidade
  do momento, e ficam distinguíveis pela operação e pelo RF do alvo.
- `test_abrir_o_modal_nao_vira_linha` — o GET autorizado não registra; o mesmo GET negado, sim.
