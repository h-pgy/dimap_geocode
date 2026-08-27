---
spec: user_admin/025
versao: v4
atualizado_em: 2026-08-26
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a extinção alcança as atribuições e concessões da unidade, e a página da unidade extinta continua acessível com a marca de extinta
  - v3: a listagem ganha o toggle "Mostrar unidades extintas", e árvore, barra e tabela passam a viver num painel só
  - v4: extinguir e reativar viram uma competência só, com duas operações, e o modal ganha face por estado da unidade
---

# SPEC user_admin/025 — Extinção e reativação de unidade

## 1 · User story
O servidor da DIMAP que dirige um ramo do organograma extingue uma unidade subordinada, e a reativa
quando preciso, para manter o organograma fiel à estrutura sem perder os servidores lotados nela nem
o histórico dos atos ali praticados.

## 2 · Condições de pronto
- [ ] Entre o organograma e a tabela existe uma **barra de ações** com **Limpar filtros**, **Nova
      unidade**, **Extinguir unidade** (vermelho) e o toggle **Mostrar unidades extintas**; o botão de
      limpar filtros sai do cabeçalho, e **Nova unidade** leva à página de cadastro, que ganha
      **Voltar para a lista de unidades** no topo e um **Cancelar** que aponta para a listagem.
- [ ] A tabela ganha uma **coluna à direita da do lápis** com uma lixeira por linha; ela e o botão da
      barra abrem o mesmo modal — com a unidade da linha, ou a em foco, ou nenhuma —, que informa
      quantos servidores e quantas subordinadas serão transferidos e para qual **sigla**, atualizando
      o aviso quando o select muda.
- [ ] Confirmada a extinção, os servidores e as subordinadas passam a responder à unidade superior, o
      titular chega lá como servidor comum, e a resposta devolve o **painel inteiro** — árvore, barra
      e tabela — já atualizado, sem recarregar a página.
- [ ] As **atribuições e concessões da unidade extinta ficam extintas com ela** e deixam de liberar
      competência a quem quer que seja.
- [ ] O toggle nasce **desligado**: unidade extinta não aparece na árvore, na tabela nem em select
      algum. **Ligado**, ela aparece nas duas primeiras com a marca **Extinta** e sem a lixeira — e
      nunca nos selects. O estado do toggle sobrevive à filtragem e à ordenação seguintes.
- [ ] A **página da unidade extinta continua acessível**, com a marca **Extinta** e a data no
      cabeçalho, e traz **um único** botão de ato: **Reativar unidade**.
- [ ] O modal tem **duas faces, escolhidas pelo estado da unidade**: vigente, a prévia da extinção;
      extinta, a confirmação da reativação, dizendo quantas atribuições e concessões voltam a valer.
- [ ] A reativação devolve a unidade à estrutura e **restaura as atribuições e concessões que caíram
      com ela** — as retiradas antes da extinção não voltam —, mas **não** devolve os servidores nem
      as subordinadas, que se refazem à mão.
- [ ] O ato é **recusado por inteiro**, sem mover nada: extinguir a **raiz** (inclusive para o
      superusuário) ou unidade cuja subordinada não pende da superior por nível ou tipo vedado;
      reativar unidade **não extinta** ou cuja **superior está extinta** — esta última nomeando a
      sigla a reativar primeiro.
- [ ] O design foi aprovado no **mock**, e as peças novas foram portadas para
      `static/src/tema-dimap.dev.css` e renderizadas no styleguide antes de qualquer template da
      aplicação usá-las.

## 3 · Domínio
A ação consome a hierarquia de `Unidade` ([user_admin/003](003-hierarquia-unidades.md)) — a quem
pergunta **quem recebe o que a unidade carrega** —, a titularidade
([user_admin/014](014-titular-da-unidade.md)), os atos que mantêm o organograma
([user_admin/020](020-unidade-como-ato-administrativo.md)), a listagem
([user_admin/021](021-lista-de-unidades.md)) e os dois níveis da competência
([autorizacao/002](../autorizacao/002-competencia-no-banco.md)), a quem pergunta **o que deixa de
valer** quando a unidade sai da estrutura, e **o que volta** quando ela retorna.

`Unidade` ganha a data de extinção, e o gerente padrão passa a devolver só as vigentes — é essa troca
que faz a unidade extinta sumir da árvore, da tabela e dos selects de uma vez, em vez de um filtro
repetido em cada consulta. A raiz é protegida por constraint: extinção sem destino não chega a
existir no banco.

**`apps/unidades/models/unidade.py`**
```python
ERRO_PAI_EXTINTO = "A unidade superior está extinta."


class UnidadeVigenteManager(models.Manager["Unidade"]):
    def get_queryset(self) -> models.QuerySet["Unidade"]:
        return super().get_queryset().filter(extinta_em__isnull=True)


class Unidade(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    sigla = models.CharField(max_length=20, unique=True)
    tipo = models.ForeignKey(TipoUnidade, on_delete=models.PROTECT, related_name="unidades")
    pai = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="filhas",
        null=True,
        blank=True,
    )
    cor = models.CharField(max_length=20, choices=CorUnidade, default=CorUnidade.AGUA_700)
    # ALTERADO nesta SPEC: a data do ato que a retirou da estrutura. Nula é unidade vigente, e é o
    # que a reativação devolve.
    extinta_em = models.DateField(null=True, blank=True)

    # ALTERADO nesta SPEC: o padrão são as vigentes; `todas` é a porta de quem precisa da extinta —
    # o histórico, a página dela e o toggle. O `_base_manager` segue sem filtro, e a travessia de FK
    # não muda.
    objects = UnidadeVigenteManager()
    todas = models.Manager()

    class Meta:
        base_manager_name = "todas"
        constraints = [
            models.CheckConstraint(
                condition=~Q(pai=F("id")),
                name="unidade_nao_e_pai_de_si_mesma",
            ),
            # ALTERADO nesta SPEC: sem unidade superior não há para onde mandar servidores e filhas,
            # e a raiz não se extingue. A regra é da linha, então é do banco.
            models.CheckConstraint(
                condition=Q(pai__isnull=False) | Q(extinta_em__isnull=True),
                name="unidade_raiz_nao_se_extingue",
            ),
        ]

    @property
    def titular(self) -> "Perfil | None": ...

    def clean(self) -> None: ...

    def _checar_hierarquia(self) -> None:
        ...
        # ALTERADO nesta SPEC: pendurar unidade viva em unidade extinta recria, por baixo, o ramo
        # que a extinção desfez. Vale para criar, para transferir e para reativar.
        if self.pai.extinta_em is not None:
            raise ValidationError({"pai": ERRO_PAI_EXTINTO})
```

Os dois níveis da competência acompanham a unidade nas duas direções: o que ela fazia deixa de valer
no mesmo ato, e com data própria — é a data que diz, na volta, o que caiu junto.

**`apps/competencias/models/competencia.py`**
```python
class AtribuicaoUnidade(models.Model):
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name="atribuicoes")
    acao = models.ForeignKey(Acao, on_delete=models.PROTECT, related_name="atribuicoes")
    # ALTERADO nesta SPEC: extinta COM a unidade. Retirar a atribuição por ato próprio continua
    # apagando a linha — o que esta data marca é só o que caiu junto com a unidade.
    extinta_em = models.DateField(null=True, blank=True)


class Concessao(models.Model):
    atribuicao = models.ForeignKey(
        AtribuicaoUnidade,
        on_delete=models.CASCADE,
        related_name="concessoes",
    )
    cargo_base = models.ForeignKey(CargoBase, on_delete=models.PROTECT, null=True, blank=True, related_name="concessoes")
    cargo_comissao = models.ForeignKey(CargoComissao, on_delete=models.PROTECT, null=True, blank=True, related_name="concessoes")
    concedida_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="concessoes_feitas")
    concedida_em = models.DateTimeField(auto_now_add=True)
    # ALTERADO nesta SPEC: própria, e não lida pela atribuição — é o campo que o avaliador filtra,
    # e resolvê-lo por join deixaria a competência dependendo de uma segunda tabela a cada request.
    extinta_em = models.DateField(null=True, blank=True)
```

Ver as extintas é uma pergunta da consulta, não um estado guardado: o DTO da listagem ganha o campo,
e árvore e tabela leem o mesmo.

**`apps/unidades/schemas.py`**
```python
class ConsultaDeUnidades(BaseModel):
    foco: int | None = None
    # ALTERADO nesta SPEC: viaja na query string e no campo oculto do cabeçalho da tabela, nunca na
    # sessão — a listagem nasce mostrando a estrutura viva a cada visita.
    extintas: bool = False
```

O alcance da ação é a terceira resposta a "sobre qual unidade": o ramo abaixo, **sem** as unidades de
onde o alcance parte — ninguém extingue nem reativa a unidade que dirige.

**`services/domain/autorizacao/contratos.py`**
```python
class UnidadesEstritamenteSubordinadas(TipoAlcance):
    """O ramo, menos as unidades de onde ele parte: o alvo precisa estar ABAIXO de quem se dirige ou
    de quem se recebeu por delegação."""

    parametros_alvo: tuple[str, ...] = ("unidade",)
```

As duas faces do ato são dois DTOs simétricos: o que sai e o que volta. Cada um é o que a tela mostra
antes de perguntar **e** o que a regra decide — uma projeção só para as duas pontas.

**`services/domain/extincao_unidade/models.py`**
```python
class IdentidadeUnidade(BaseModel):
    """A unidade projetada: o domínio não conhece o model, e do model só precisa disto."""

    model_config = ConfigDict(frozen=True)

    unidade_id: int
    sigla: str


class PreviaDaExtincao(BaseModel):
    model_config = ConfigDict(frozen=True)

    unidade: IdentidadeUnidade
    # Ausente é raiz — e raiz não tem para onde mandar o que carrega.
    destino: IdentidadeUnidade | None
    servidores: int
    subordinadas: int
    ja_extinta: bool = False


class PreviaDaReativacao(BaseModel):
    """O reverso: o que volta, não o que sai."""

    model_config = ConfigDict(frozen=True)

    unidade: IdentidadeUnidade
    # A unidade superior de onde ela volta a pender. Extinta, não há para onde voltar.
    superior: IdentidadeUnidade
    superior_extinta: bool
    atribuicoes: int
    concessoes: int
    ja_vigente: bool = False


class Veredito(BaseModel):
    """Um só para as duas faces: a pergunta muda, a resposta tem a mesma forma."""

    model_config = ConfigDict(frozen=True)

    pode: bool
    motivo: str = ""
```

**Mock:** [025-mock-extincao-de-unidade.html](025-mock-extincao-de-unidade.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Devolver os servidores e as subordinadas à unidade reativada — feito à mão, pelo cadastro de cada
  servidor e pela transferência da SPEC 020; sem dono ainda.
- Reativar ou extinguir um ramo inteiro num ato só — sem dono ainda.
- Filtrar e ordenar **por** extinção (coluna própria na tabela): o toggle mostra ou esconde, não
  ordena — sem dono ainda.
- Marcar "extinta" ao lado da sigla nas telas de histórico de execução — sem dono ainda.
- Restaurar as delegações encerradas pela extinção: encerrada é encerrada, e delegar de novo é ato
  próprio (autorizacao/009) — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/competencias/protecao.py` → `acao_protegida`, `conferir_alvo`, `pode_executar`: barreira,
  conferência do alvo e a mesma resposta na forma da tela.
- `@apps/competencias/utils.py` → `instanciar_acao`: construção do contrato da ação.
- `@apps/competencias/consulta.py` → `alcance_do_perfil`, `unidades_dirigidas`, `unidades_delegadas`:
  o ramo alcançado e as unidades de onde ele parte.
- `@apps/unidades/consulta.py` → `posicao_de`: a subárvore a partir de uma unidade.
- `@apps/unidades/cadastro.py` → `DesfechoUnidade`: a forma de desfecho dos atos de unidade.
- `@apps/unidades/formularios.py` → `traduzir_recusa`: erro bruto → mensagem em português e controle
  realçado.
- `@templates/partials/_tarja_recusa.html` → a tarja de recusa dentro do modal.
- `@templates/unidades/partials/_modal_destituir_titular.html` → a forma de um modal de confirmação
  sem formulário: tarja, dois botões, nada a preencher.
- `@static/src/js/ui/tabela_onsen.js` → `data-limpar-filtros`: o botão de limpeza recebe o seletor da
  tabela e funciona onde estiver no DOM.
- `@static/src/tema-dimap.dev.css` → `.toggle-onsen`: o interruptor liga/desliga do design system.
- Skills: `acao-administrativa`, `componentes-frontend`, `mock`, `erros-de-formulario`,
  `escrever-testes`.

## 6 · Snippets

O alcance estrito reaproveita a conta que já existe: o ramo, menos as partidas dele. E é o único que
enxerga unidade extinta — sem isso, a unidade que acabou de sair da estrutura sairia também do
alcance de quem a extinguiu, e ninguém poderia reativá-la.

**`apps/unidades/consulta.py`**
```python
def posicao_de(unidade_id: int, com_extintas: bool = False) -> PosicaoHierarquica:
    gerente = Unidade.todas if com_extintas else Unidade.objects
    pares = tuple(
        ParHierarquia(unidade_id=pk, pai_id=pai_id)
        for pk, pai_id in gerente.values_list("id", "pai_id")
    )
    return ArvoreHierarquica()(ComandoPosicao(unidade_id=unidade_id, pares=pares))
```

**`apps/competencias/consulta.py`**
```python
def partidas_do_alcance(perfil: Perfil) -> frozenset[int]:
    """As unidades de onde o alcance parte: as dirigidas e as recebidas por delegação. Extraída de
    `ramos_do_alcance`, que já a calculava para descartar o ramo contido."""
    return unidades_dirigidas(perfil) | unidades_delegadas(perfil)
```

**`apps/competencias/protecao.py`**
```python
def _conjunto_alcancado(alcance: TipoAlcance, perfil: Perfil) -> frozenset[int]:
    # A conferência de pertencimento continua escrita uma vez só, em `conferir_alvo`; o que muda por
    # alcance é o CONJUNTO em que se procura.
    if isinstance(alcance, UnidadesEstritamenteSubordinadas):
        return alcance_do_perfil(perfil, com_extintas=True) - partidas_do_alcance(perfil)
    return alcance_do_perfil(perfil)


def _unidades_alvo(alcance: TipoAlcance, valores: Mapping[str, int]) -> tuple[int, ...]:
    # Os dois alcances de unidade extraem o alvo do mesmo jeito — cada parâmetro declarado carrega
    # uma unidade. O que os separa é o conjunto, não a extração.
    if isinstance(alcance, UnidadesSubordinadas | UnidadesEstritamenteSubordinadas):
        return tuple(
            valores[parametro]
            for parametro in alcance.parametros_alvo
            if parametro in valores
        )
    ...
```

As duas regras, sem banco, no mesmo módulo: só sai o que tem para onde mandar o que carrega, e só
volta o que está fora e tem onde pendurar.

**`services/domain/extincao_unidade/avaliador.py`**
```python
MOTIVO_RAIZ = "A unidade raiz não se extingue: não há unidade superior para receber o que ela carrega."
MOTIVO_JA_EXTINTA = "Esta unidade já foi extinta."
MOTIVO_JA_VIGENTE = "Esta unidade não está extinta."
MOTIVO_SUPERIOR_EXTINTA = "Reative antes a {sigla}: uma unidade não pende de unidade extinta."


class AvaliadorExtincao:
    def __call__(self, previa: PreviaDaExtincao) -> Veredito:
        # Antes do destino: o POST repetido chega com a unidade já extinta e o destino ainda de pé.
        if previa.ja_extinta:
            return Veredito(pode=False, motivo=MOTIVO_JA_EXTINTA)
        if previa.destino is None:
            return Veredito(pode=False, motivo=MOTIVO_RAIZ)
        return Veredito(pode=True)


class AvaliadorReativacao:
    def __call__(self, previa: PreviaDaReativacao) -> Veredito:
        if previa.ja_vigente:
            return Veredito(pode=False, motivo=MOTIVO_JA_VIGENTE)
        if previa.superior_extinta:
            return Veredito(
                pode=False,
                motivo=MOTIVO_SUPERIOR_EXTINTA.format(sigla=previa.superior.sigla),
            )
        return Veredito(pode=True)
```

O ato, na borda: uma transação por operação, e a recusa da hierarquia traduzida na mesma forma dos
outros atos de unidade.

**`apps/unidades/extincao.py`**
```python
@dataclass(frozen=True)
class DesfechoExtincao:
    """Mesma forma do `DesfechoUnidade` (SPEC 020): gravou (`unidade`) ou recusou (`recusa`). Serve
    às duas operações — o que muda entre elas é o que a transação faz, não o recado à view."""

    unidade: Unidade | None
    destino: Unidade | None = None
    recusa: RecusaDeFormulario = RecusaDeFormulario()


def extinguir_unidade(valores: Mapping[str, Any], hoje: date) -> DesfechoExtincao:
    leitura = ler_ato_de_unidade(valores)
    if leitura.dto is None:
        return DesfechoExtincao(unidade=None, recusa=leitura.recusa or RecusaDeFormulario())
    unidade = get_object_or_404(
        Unidade.todas.select_related("pai"), pk=leitura.dto.unidade_id
    )
    veredito = avaliar_extincao(previa_da_extincao(unidade))
    if not veredito.pode:
        return DesfechoExtincao(unidade=None, recusa=_recusa(veredito.motivo))
    destino = unidade.pai
    try:
        with transaction.atomic():
            # As filhas primeiro: é a única etapa que pode recusar, e recusar depois de mover
            # servidor obrigaria a transação a desfazer trabalho que ninguém precisava ter feito.
            _subir_filhas(unidade, destino)
            _transferir_servidores(unidade, destino)
            _extinguir_competencias(unidade, hoje)
            _encerrar_delegacoes(unidade, hoje)
            unidade.extinta_em = hoje
            unidade.save(update_fields=["extinta_em"])
    except ValidationError as recusa:
        return DesfechoExtincao(unidade=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    return DesfechoExtincao(unidade=unidade, destino=destino)


def reativar_unidade(valores: Mapping[str, Any]) -> DesfechoExtincao:
    leitura = ler_ato_de_unidade(valores)
    if leitura.dto is None:
        return DesfechoExtincao(unidade=None, recusa=leitura.recusa or RecusaDeFormulario())
    unidade = get_object_or_404(
        Unidade.todas.select_related("pai"), pk=leitura.dto.unidade_id
    )
    veredito = avaliar_reativacao(previa_da_reativacao(unidade))
    if not veredito.pode:
        return DesfechoExtincao(unidade=None, recusa=_recusa(veredito.motivo))
    # Lida ANTES de zerar o campo: é a chave de tudo que a restauração vai procurar.
    extinta_em = unidade.extinta_em
    try:
        with transaction.atomic():
            unidade.extinta_em = None
            # Entre a extinção e agora o tipo do superior pode ter mudado: quem barra é a mesma
            # validação de hierarquia que barra na criação.
            unidade.full_clean()
            unidade.save(update_fields=["extinta_em"])
            _restaurar_competencias(unidade, extinta_em)
    except ValidationError as recusa:
        return DesfechoExtincao(unidade=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    return DesfechoExtincao(unidade=unidade, destino=unidade.pai)


def _subir_filhas(unidade: Unidade, destino: Unidade) -> None:
    # Uma a uma, com `full_clean`: nível e tipo vedado são regras de `Unidade.clean()` e nenhum
    # `update()` em massa as cobra.
    for filha in unidade.filhas.all():
        filha.pai = destino
        filha.full_clean()
        filha.save(update_fields=["pai"])


def _transferir_servidores(unidade: Unidade, destino: Unidade) -> None:
    # A titularidade cai no mesmo `update`: o vínculo é com a unidade que deixou de existir, e a
    # unicidade de um titular por unidade barraria o segundo marcado no destino.
    unidade.perfis.update(unidade=destino, e_titular=False)


def _extinguir_competencias(unidade: Unidade, hoje: date) -> None:
    """O que a unidade fazia sai com ela, nos dois níveis. A data é a mesma da unidade: é por ela
    que a reativação reconhece o que caiu junto."""
    atribuicoes = unidade.atribuicoes.filter(extinta_em__isnull=True)
    Concessao.objects.filter(atribuicao__in=atribuicoes, extinta_em__isnull=True).update(
        extinta_em=hoje
    )
    atribuicoes.update(extinta_em=hoje)


def _restaurar_competencias(unidade: Unidade, extinta_em: date) -> None:
    """Só o que caiu NAQUELE ato: a data é o que separa a atribuição extinta com a unidade da que foi
    retirada por ato próprio — essa última nem existe mais, porque retirar apaga a linha."""
    atribuicoes = unidade.atribuicoes.filter(extinta_em=extinta_em)
    Concessao.objects.filter(atribuicao__in=atribuicoes, extinta_em=extinta_em).update(
        extinta_em=None
    )
    atribuicoes.update(extinta_em=None)


def _encerrar_delegacoes(unidade: Unidade, hoje: date) -> None:
    """Vigente encerra hoje; a que ainda não começou é apagada — mesmo tratamento que a SPEC 023 dá
    ao impedimento que nunca vigorou, e pelo mesmo motivo: encerrar antes do início é recusado pelo
    `CheckConstraint`."""
    vigentes = unidade.delegacoes.filter(data_inicio__lte=hoje)
    vigentes.filter(Q(data_fim__isnull=True) | Q(data_fim__gt=hoje)).update(data_fim=hoje)
    unidade.delegacoes.filter(data_inicio__gt=hoje).delete()
```

A extinção da competência só vale se o avaliador a enxergar — é este filtro que faz o campo carregar
peso, em vez de ser anotação.

**`apps/competencias/consulta.py`**
```python
concessoes = tuple(
    ConcessaoVigente(...)
    for concessao in Concessao.objects.filter(
        atribuicao__unidade_id__in=unidades_das_canetas,
        # Competência de unidade extinta não é competência de ninguém.
        extinta_em__isnull=True,
    ).select_related("atribuicao__acao")
)
```

Uma ação, duas operações — e o mesmo padrão da SPEC 023: o slug nomeia a face principal e o tooltip
carrega a outra.

**`apps/unidades/acoes_declaradas.py`**
```python
ACAO_EXTINGUIR_UNIDADE = instanciar_acao(
    slug="unidades.extinguir_unidade",
    nome="Extinguir unidade",
    nome_curto="Extinguir",
    tooltip="Retira da estrutura uma unidade subordinada, transferindo servidores e subordinadas para a unidade superior — e a reativa.",
    # Precisa reverter sem argumento (`competencias.E004`): é a rota que abre o modal, e não as de
    # gravação.
    url_name="unidades:extinguir_unidade",
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=True,
    alcance=UnidadesEstritamenteSubordinadas(),
)
```

O toggle troca **o painel inteiro** — árvore, barra e tabela —, porque ligar as extintas muda os três.
Filtro e ordenação continuam trocando só o corpo da tabela, e é o campo oculto do cabeçalho que
carrega o estado do toggle junto com eles.

**`apps/unidades/urls.py`**
```python
# O painel é alvo de swap por dois caminhos: o toggle e a conclusão do ato.
path("painel/", views.painel_unidades, name="painel_unidades"),
# Uma porta para abrir (a face sai do estado da unidade) e uma por operação para gravar: é essa
# separação, e não uma flag no formulário, que faz "abrir o modal não pratica o ato" ser estrutural.
path("extinguir/", views.extinguir_unidade, name="extinguir_unidade"),
path("extinguir/previa/", views.previa_do_ato, name="previa_do_ato"),
path("extinguir/gravar/", views.gravar_extincao_unidade, name="gravar_extincao_unidade"),
path("reativar/gravar/", views.gravar_reativacao_unidade, name="gravar_reativacao_unidade"),
```

**`templates/unidades/partials/_barra_acoes_unidades.html`**
```html
{# Sem JS: o checkbox é o próprio campo, e o `change` é o gatilho padrão do HTMX. `hx-include` leva #}
{# os filtros do cabeçalho, para que ligar as extintas não apague o que já estava filtrado.         #}
<input type="checkbox"
       class="toggle-onsen"
       name="extintas"
       value="1"
       {% if extintas %}checked{% endif %}
       hx-get="{% url 'unidades:painel_unidades' %}"
       hx-target="#painel-unidades"
       hx-swap="outerHTML"
       hx-include="#tabela-unidades thead"
       aria-label="Mostrar unidades extintas" />
```

**`apps/unidades/context.py`**
```python
def contexto_corpo_unidades(
    consulta: ConsultaUnidades,
    unidade_em_foco: Unidade | None = None,
    extintas: bool = False,
) -> dict[str, Any]:
    # O recorte desce como DADO até a borda que lê o banco, e o mesmo valor vai para a árvore: as
    # duas nunca discordam sobre quem existe.
    linhas = _linhas_de_unidades(com_extintas=extintas)
    ...


def contexto_organograma(
    unidade_em_foco: Unidade | None = None,
    extintas: bool = False,
) -> dict[str, Any]:
    """A árvore obedece ao MESMO toggle que a tabela: com ele desligado, a extinta não é nó.

    `com_extintas` aqui é a pergunta da TELA, e não a do alcance estrito — que também o usa, por
    outro motivo (a unidade recém-extinta tem de continuar alcançável para ser reativada). Mesmo
    parâmetro, duas perguntas: nenhuma das duas decide pela outra."""
    gerente = Unidade.todas if extintas else Unidade.objects
    ramos = [
        posicao_de(raiz.pk, com_extintas=extintas).ego
        for raiz in gerente.filter(pai__isnull=True)
    ]
    ...


def contexto_modal_do_ato(unidade: Unidade | None, alcance: frozenset[int]) -> dict[str, Any]:
    """A face é o estado da unidade, resolvido uma vez e entregue pronto ao template: perguntar
    `extinta_em` dentro do HTML espalharia a decisão por cada bloco do modal."""
    if unidade is not None and unidade.extinta_em is not None:
        return {"face": "reativar", "previa": previa_da_reativacao(unidade)}
    return {"face": "extinguir", "previa": ..., "unidades": _unidades_extinguiveis(alcance)}
```

**`apps/unidades/views.py`**
```python
def painel_unidades(request: HttpRequest) -> HttpResponse:
    """Rota de leitura, alvo do toggle. Troca o painel inteiro porque ligar as extintas muda a
    árvore, a tabela e o próprio estado da barra."""
    consulta = consulta_da_listagem(request.GET.dict(), ColunaUnidade)
    parametros = ConsultaDeUnidades.model_validate(request.GET.dict())
    unidade_em_foco = Unidade.todas.filter(pk=parametros.foco).first() if parametros.foco else None
    return render(
        request,
        TEMPLATE_PAINEL_UNIDADES,
        contexto_listagem_unidades(consulta, unidade_em_foco, parametros.extintas),
    )


@acao_protegida(ACAO_EXTINGUIR_UNIDADE)
@require_POST
def gravar_reativacao_unidade(request: HttpRequest) -> HttpResponse:
    """A outra operação da MESMA ação: mesma barreira, mesmo alcance, outro desfecho e outra palavra
    no histórico."""
    valores = {"unidade_id": request.POST.get("unidade", "")}
    desfecho = reativar_unidade(valores)
    if desfecho.unidade is None:
        return render(
            request,
            TEMPLATE_MODAL_ATO,
            contexto_ato_recusado(valores, desfecho.recusa),
            status=422,
        )
    registrar_ato(
        request,
        # `extinguir` e `reativar` sob a mesma ação: é a operação que distingue as duas no rastro.
        operacao="reativar",
        alvo_tipo="unidade",
        alvo_identificador=desfecho.unidade.sigla,
    )
    return render(request, TEMPLATE_ATO_CONCLUIDO, contexto_unidade(desfecho.unidade) | ...)


def pagina_unidade(request: HttpRequest, pk: int) -> HttpResponse:
    # `todas`: a página é o único lugar em que a unidade extinta se mostra por si, e é onde mora o
    # gesto de trazê-la de volta.
    unidade = get_object_or_404(Unidade.todas.select_related("tipo", "pai"), pk=pk)
    extinta = unidade.extinta_em is not None
    return render(
        request,
        TEMPLATE_PAGINA_UNIDADE,
        contexto_unidade(unidade)
        | {
            # Gesto de unidade viva não se oferece a unidade extinta, e vice-versa: a barreira segue
            # na rota, e a tela não convida ao 403.
            "pode_editar": not extinta and pode_executar(request.user, ACAO_EDITAR_UNIDADE, unidade.pk),
            "pode_designar_substituto": not extinta
            and pode_executar(request.user, ACAO_DESIGNAR_SUBSTITUTO, unidade.pk),
            "pode_reativar": extinta
            and pode_executar(request.user, ACAO_EXTINGUIR_UNIDADE, unidade.pk),
        },
    )
```

## 7 · Caveats
Extinguir e reativar são **uma competência só**, com duas operações, e não duas ações inscritas —
mesma decisão da SPEC 023 para impedimento e retorno. Separá-las permitiria conceder o poder de
extinguir sem o de desfazer, deixando um organograma mutilado por quem não pode remendá-lo. O custo é
que o histórico só as distingue pela operação gravada, e uma futura política que queira conceder só
uma delas terá de quebrar a ação em duas.

A unidade extinta continua no banco em vez de ser apagada. Todo FK que aponta para `Unidade` é
`PROTECT`, e o de `ExecucaoAcao` guarda a unidade do autor **no dia do ato** — apagar a linha ou
repontá-la reescreveria o histórico que o registro existe para fixar. O custo é uma tabela que só
cresce, e uma segunda porta (`Unidade.todas`) que qualquer consulta nova pode escolher por engano.

`Unidade.objects` passa a filtrar, e é a `Meta.base_manager_name = "todas"` que mantém a travessia de
FK devolvendo a unidade extinta. O ganho é a unidade sumir de árvore, tabela e selects sem um filtro
repetido em dez consultas. O custo é que o filtro fica implícito: quem escrever `Unidade.objects`
esperando o cadastro inteiro recebe menos linhas do que pediu, e nada no ponto de chamada avisa.

`AtribuicaoUnidade` e `Concessao` **não** ganham gerente filtrado, ao contrário de `Unidade`. As duas
são alcançadas por join a partir de `Acao` e de `Perfil` (`exclude(atribuicoes__unidade=…)`), e join
não passa por gerente algum — um filtro padrão valeria em metade dos caminhos e mentiria na outra. O
custo é que a vigência é conferida à mão, e hoje só o avaliador de competência a confere.

A reativação devolve a unidade e as competências, mas não os servidores nem as subordinadas. Devolver
lotação exigiria guardar, por servidor, de onde ele veio — uma coluna de histórico de lotação que o
sistema não tem e que esta iteração não vai inventar. O custo é uma reativação incompleta: a unidade
volta vazia, e quem a reabre relota servidor por servidor sem que nada na tela lhe diga quem estava lá.

A restauração casa pela **data**, não por um identificador do ato. Duas extinções da mesma unidade no
mesmo dia, com uma reativação no meio, restaurariam junto o que a segunda derrubou. Evitá-lo exigiria
uma tabela de atos de extinção só para dar nome ao lote. O custo é essa janela de 24 horas.

Ligar o toggle **remonta a árvore do zero**, e com ela o que estava aberto ou recolhido: a abertura de
cada nó é classe no DOM, escrita por `arvore_hierarquica.js`, e não sobrevive ao swap. Preservá-la
exigiria devolver ao servidor um estado que hoje só existe no cliente. O custo é o gesto obrigar o
usuário a reabrir o caminho em que estava — atenuado por ser gesto raro e por mudar justamente o
conteúdo da árvore.

A transferência dos servidores usa `update()` em massa, sem `full_clean()`. A única invariante que a
lotação toca é a de titularidade, e o mesmo `update` a desfaz; o resto continua garantido pela
`UniqueConstraint` no banco. O custo é uma escrita de `Perfil` que não passa pelo `clean()` — regra
nova de lotação que nasça lá não valerá para este caminho.

O superusuário não passa pela conferência de alcance e pode extinguir a própria unidade. Prendê-lo ao
alcance é o que a SPEC 020 já recusou, para não deixar o administrador sem poder agir no topo, e a
única unidade que ele não pode extinguir — a raiz — é barrada por `CheckConstraint`, não por alcance.
O custo é que ele pode se retirar do ramo em que está lotado, sendo transferido para a unidade
superior pelo próprio ato.

O alcance passa a ser calculado de **duas** maneiras: sobre o organograma vigente para todas as ações,
e sobre o organograma com as extintas para `UnidadesEstritamenteSubordinadas`. Sem a segunda, a
unidade recém-extinta sairia do alcance de quem a extinguiu e ninguém poderia reativá-la. O custo é
uma pergunta que admite duas respostas conforme quem a faz, e a obrigação de que só este alcance use a
segunda.

`UnidadesEstritamenteSubordinadas` é o quarto subtipo de `TipoAlcance`, e o primeiro em que o
`isinstance` decide **o conjunto** e não a extração do alvo. Fundir os dois numa função só esconderia
que são perguntas diferentes. O custo é um segundo ponto de extensão em `protecao.py`: alcance novo
agora pode precisar de ramo em dois lugares, e só um deles tem `NotImplementedError` guardando o
esquecimento.

A prévia do modal é recalculada a cada troca do select, numa rota própria. Mandá-la junto com a lista
de unidades exigiria contar servidores, filhas e competências de todo o ramo para mostrar as de uma. O
custo é uma requisição por troca de select, sobre um organograma de dezenas de unidades.

## 8 · Testes (TDD)

**Comportamento do ato**
- `test_extincao_transfere_servidores_e_filhas_para_o_pai` — o POST marca a unidade como extinta, e
  seus servidores e subordinadas passam a responder à unidade superior; o titular chega ao destino
  sem titularidade, e a resposta devolve o painel já sem a unidade. *(marker `banco`)*
- `test_extincao_extingue_atribuicoes_e_concessoes` — as atribuições da unidade e as concessões delas
  ficam com a data do ato, e quem tinha a concessão deixa de exercer a ação. *(marker `banco`)*
- `test_extinta_some_da_listagem_ate_o_toggle_revela` — com o toggle desligado a unidade não aparece
  na árvore, na tabela nem no select de unidade superior do cadastro; ligado, ela volta às duas
  primeiras com a marca de extinta e sem a lixeira, segue fora do select, e o filtro seguinte mantém o
  estado. *(marker `banco`)*
- `test_extincao_recusa_por_inteiro` — extinguir a raiz (inclusive como superusuário) e extinguir
  unidade cuja subordinada não pende do destino devolvem a recusa em português; nenhuma filha sobe,
  nenhum servidor muda de lotação, nenhuma atribuição é extinta. *(marker `banco`)*
- `test_delegacoes_da_extinta_sao_encerradas` — delegação vigente na unidade extinta passa a ter fim
  hoje, e a que começaria depois é apagada. *(marker `banco`)*
- `test_modal_abre_com_previa_e_select_recortado` — na face de extinção, o modal traz o número de
  servidores, o de subordinadas e a sigla do destino, e o select lista as subordinadas do ramo sem a
  unidade que o perfil dirige e sem as raízes. *(marker `banco`)*
- `test_face_do_modal_segue_o_estado_da_unidade` — unidade vigente devolve a face da extinção; unidade
  extinta devolve a da reativação, com a contagem do que volta. *(marker `banco`)*
- `test_reativacao_devolve_unidade_e_as_competencias_que_cairam` — a unidade volta à árvore, à tabela
  e aos selects; as atribuições e concessões extintas com ela voltam a valer e quem tinha o cargo
  concedido volta a exercer a ação; atribuição retirada antes da extinção não é recriada; e os
  servidores e as subordinadas continuam onde estavam. *(marker `banco`)*
- `test_reativacao_recusa_por_inteiro` — reativar unidade vigente e reativar unidade cuja superior
  está extinta são recusados, o segundo nomeando a sigla a reativar primeiro, e nada muda.
  *(marker `banco`)*
- `test_pagina_da_extinta_oferece_so_reativar` — o GET responde 200, traz a marca de extinta com a
  data e o botão de reativar, e não traz os de editar e de designar substituto; depois do ato, o
  inverso. *(marker `banco`)*

**Segurança da ação** (skill `acao-administrativa`; fora do teto)
- `test_anonimo_vai_ao_login_sem_registrar` — POST anônimo nas duas rotas de gravação redireciona e
  não deixa linha. *(marker `banco`)*
- `test_sem_competencia_recebe_403_registrado` — servidor comum recebe 403 e a tentativa fica
  registrada. *(marker `banco`)*
- `test_quem_dirige_pratica_sem_concessao_gravada` — titular da unidade superior extingue e reativa a
  subordinada sem atribuição nem concessão; quem não dirige e não tem concessão, não.
  *(marker `banco`)*
- `test_propria_unidade_dirigida_e_recusada` — POST nomeando a unidade que o próprio perfil dirige
  recebe 403 registrado nas duas operações, e o botão dela não é renderizado na tabela.
  *(marker `banco`)*
- `test_alvo_de_outro_ramo_e_recusado` — titular de um ramo recebe 403 registrado ao nomear unidade de
  outro, com id válido, e nada é movido. *(marker `banco`)*
- `test_post_sem_o_parametro_do_alvo_e_400` — POST sem `unidade` é recusado com 400 e não gera linha
  de negativa. *(marker `banco`)*
- `test_impedido_recebe_403_e_exonerado_302` — titular com impedimento vigente recebe 403; titular
  exonerado chega como anônimo e recebe 302 para o login, sem linha de negativa. *(marker `banco`)*
- `test_substituto_pratica_durante_a_cobertura` — quem cobre o titular responde pela direção e pratica
  o ato; o registro grava o cargo e a unidade do substituído no momento. *(marker `banco`)*
- `test_ato_grava_quem_cargo_unidade_operacao_e_alvo` — a execução autorizada registra autor, cargo e
  unidade do momento, a operação e a sigla; mudar a lotação depois não altera a linha.
  *(marker `banco`)*
- `test_extinguir_e_reativar_sao_distinguiveis_no_historico` — as duas operações gravam valores
  diferentes sob a mesma ação, e o histórico da unidade mostra o par. *(marker `banco`)*
- `test_historico_da_extinta_continua_integro` — as execuções gravadas na unidade antes do ato
  continuam legíveis depois dele. *(marker `banco`)*
- `test_leitura_autorizada_nao_vira_linha` — os GET do painel, do modal e da prévia não registram
  nada; o mesmo GET negado, sim. *(marker `banco`)*
- `test_escrita_so_por_post` — GET nas duas rotas de gravação é recusado e nada muda.
  *(marker `banco`)*
