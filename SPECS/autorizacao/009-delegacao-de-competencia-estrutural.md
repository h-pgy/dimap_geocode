---
spec: autorizacao/009
versao: v3
atualizado_em: 2026-08-25
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: delegar e revogar competência estrutural passam a exigir direção — a cadeia de delegação para no primeiro elo
  - v3: delegação de competência estrutural passa a ser nominal a um servidor (Perfil) com herança de alcance do ramo, espelhando o padrão de substituição
---

# SPEC autorizacao/009 — Delegação nominal de competência estrutural

## 1 · User story
Quem responde pela direção de uma unidade da DIMAP delega nominalmente a um servidor do seu ramo a
execução de uma competência estrutural que é sua por direção, na tela de competências, para que a
pessoa designada possa praticar aquele ato específico na unidade e nas subordinadas sem herdar a
titularidade nem as demais competências da cadeira.

## 2 · Condições de pronto
- [ ] **Delegação é nominal a um servidor**: quem responde pela direção da unidade delega uma
      competência **estrutural** a um `Perfil` específico do seu ramo — e não a um cargo genérico.
- [ ] **Delegação herda o alcance do ramo**: o delegado alcança a unidade em que a competência foi
      delegada e **todas as subordinadas a ela** para a prática do ato delegado. Quem não recebeu
      delegação alguma e não dirige unidade continua com alcance vazio.
- [ ] **O delegado pratica o ato delegado de verdade**: executa a ação estrutural no ramo delegado
      sem concessão de cargo e sem dirigir unidade alguma. Fora do ramo delegado ou para ação não
      delegada, é recusado com **403 registrado**.
- [ ] **Delegação não transfere a cadeira**: o delegado recebe **apenas a competência específica
      delegada** — não herda as demais competências do titular nem a direção da unidade.
- [ ] **Candidatos restritos ao alcance**: o diálogo de delegação lista servidores lotados na unidade
      e nas suas **subordinadas**; servidor de fora do ramo não é oferecido e POST forjado é
      recusado como **recusa de formulário com realce no controle**, sem gravar nada.
- [ ] **Vigência por período**: a delegação possui `data_inicio` e `data_fim` opcional; fora da
      vigência ou com perfil **fora de exercício** (impedido ou exonerado), a delegação não libera
      competência nem alcance.
- [ ] **Delegação não se re-delega**: só quem responde pela direção **delega e revoga** competência
      estrutural. O delegado não vê botão de delegar nem lata de revogação nos cartões estruturais,
      e o POST forjado é **403 registrado**, sem gravar nada.
- [ ] **Revogar encerra a delegação**: delegação em curso encerrada tem a `data_fim` fixada na data
      do ato e fica no histórico; delegação futura que ainda não iniciou é apagada.
- [ ] **Ato registrado com operação própria**: delegar e revogar registram execuções com operações
      distinguíveis (`delegar` e `revogar`), com o **RF do delegado** e o slug da ação como alvo.
- [ ] O design foi aprovado no **mock**: o cartão de competência estrutural com o badge/toast de **"Estrutural"** em cor `success` (`badge badge-success badge-soft badge-sm`) ao lado do nome da ação, a lista de delegados nominais com o badge/toast de **"Delegada"** em cor `info` (`badge badge-info badge-soft badge-sm`) na linha do servidor, o modal de delegar com a `.aura-onsen`, o select de servidores do ramo e o cartão bloqueado para quem não dirige a unidade.

## 3 · Domínio
A competência estrutural decorre da direção da unidade, e delegá-la é transferir o exercício de um ato
específico a uma pessoa física (`Perfil`), mantendo a titularidade e as demais competências no titular.
`Delegacao` é a entidade que representa esse vínculo direcionado, com período de vigência próprio no
molde de `Substituicao`.

Diferente da concessão (SPEC [002](002-competencia-no-banco.md)), que distribui ações comuns a cargos,
a delegação recai sobre um servidor determinado e carrega a nascente do alcance da unidade delegante.
O avaliador de competência passa a compor canetas, concessões de cargo e delegações vigentes numa única
avaliação.

**`apps/competencias/models/delegacao.py`**
```python
class Delegacao(models.Model):
    acao = models.ForeignKey("competencias.Acao", on_delete=models.PROTECT, related_name="delegacoes")
    unidade = models.ForeignKey("unidades.Unidade", on_delete=models.PROTECT, related_name="delegacoes")
    delegante = models.ForeignKey("user_admin.Perfil", on_delete=models.PROTECT, related_name="delegacoes_feitas")
    delegado = models.ForeignKey("user_admin.Perfil", on_delete=models.PROTECT, related_name="delegacoes_recebidas")
    data_inicio = models.DateField()
    data_fim = models.DateField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
```

**`services/domain/autorizacao/models.py`**
```python
class DelegacaoVigente(BaseModel):
    """Uma competência estrutural delegada nominalmente a um servidor, com o ramo de onde parte o alcance."""

    model_config = ConfigDict(frozen=True)

    acao_slug: str
    acao_ativa: bool
    unidade_id: int
    delegado_id: int


class AvaliacaoCompetenciaInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    perfil: PerfilCompetencia
    concessoes: tuple[ConcessaoVigente, ...]
    slugs_estruturais: frozenset[str] = frozenset()
    slugs_exclusivos: frozenset[str] = frozenset()
    # ALTERADO nesta SPEC: delegações nominais vigentes que o perfil recebeu.
    delegacoes: tuple[DelegacaoVigente, ...] = ()


class AvaliacaoCompetenciaOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    slugs_liberados: frozenset[str]
    # ALTERADO nesta SPEC: as unidades de onde partem os ramos delegados ao perfil.
    unidades_delegadas: frozenset[int] = frozenset()
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`AvaliadorCompetencia`, `Caneta`, `ConcessaoVigente`, `PerfilCompetencia`](003-avaliador-e-backend-de-autorizacao.md) —
  "quais competências este perfil possui?"; passa a cruzar canetas, concessões e delegações nominais.
- [`alcance_do_perfil`, `ramos_do_alcance`, `conferir_alvo`](004-protecao-de-rota-e-registro-de-execucao.md) —
  "quais unidades o perfil alcança?"; passa a compor unidades dirigidas e unidades delegadas.
- [`Acao.estrutural`](001-catalogo-de-acoes-em-codigo.md) — "esta ação é estrutural?"; apenas ações
  estruturais admitem delegação nominal.
- [`dirige`, `unidades_dirigidas`](004-protecao-de-rota-e-registro-de-execucao.md) — "quem responde
  pela direção?"; apenas quem dirige pode delegar e revogar competência estrutural.
- [`Substituicao`, `TemPeriodo`, `periodo_de`](../user_admin/015-exercicio-e-substituicao.md) — a
  convenção de vigência temporal e encerramento de vínculo.
- [`.aura-onsen`](../user_admin/022-tornar-administrador.md) — o átomo visual que destaca o ato de delegação.

**Mock:** [009-mock-delegacao.html](009-mock-delegacao.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Concessão de competência não-estrutural a cargos — SPEC [008](008-acao-conceder-competencia.md).
- Re-delegação de competência estrutural por delegado — expressamente vedada (§3).
- Notificação automática (e-mail ou webhook) ao servidor sobre delegação recebida — sem dono ainda.
- Anexo de documento formal ou portaria de delegação em PDF — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/user_admin/substituicao.py` → `Substituicao`, `_desfecho`, `recusa_de_substituto_fora_do_alcance`:
  molde do ato nominal com vigência, desfecho e conferência de alcance do candidato.
- `@services/domain/autorizacao/avaliador.py` → `AvaliadorCompetencia`: resolução de competências.
- `@apps/competencias/consulta.py` → `montar_avaliacao`, `unidades_dirigidas`, `ramos_do_alcance`,
  `alcance_do_perfil`: a borda banco → DTO e cálculo do alcance composto.
- `@apps/competencias/views.py` → `conceder_cargo`, `revogar_cargo`, `_atribuicao_no_alvo`: rotas de
  concessão e barreiras de direção.
- `@apps/competencias/context.py` → `contexto_modal_conceder`, `contexto_poco_concessoes`: contextos dos painéis.
- `@templates/user_admin/partials/_modal_designar.html` → molde do select de servidores e inputs de data.
- Skills: `acao-administrativa`, `ontologia`, `componentes-frontend`, `daisyui`, `htmx`, `mock`,
  `escrever-testes`, `test-django-views`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`apps/competencias/models/delegacao.py`** — a entidade de delegação nominal e suas restrições de integridade.
```python
class Delegacao(models.Model):
    acao = models.ForeignKey(
        "competencias.Acao",
        on_delete=models.PROTECT,
        related_name="delegacoes",
    )
    unidade = models.ForeignKey(
        "unidades.Unidade",
        on_delete=models.PROTECT,
        related_name="delegacoes",
    )
    delegante = models.ForeignKey(
        "user_admin.Perfil",
        on_delete=models.PROTECT,
        related_name="delegacoes_feitas",
    )
    delegado = models.ForeignKey(
        "user_admin.Perfil",
        on_delete=models.PROTECT,
        related_name="delegacoes_recebidas",
    )
    data_inicio = models.DateField()
    data_fim = models.DateField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Delegação de competência"
        verbose_name_plural = "Delegações de competência"
        constraints = [
            models.CheckConstraint(
                condition=Q(data_fim__isnull=True) | Q(data_fim__gte=F("data_inicio")),
                name="delegacao_fim_nao_antecede_inicio",
            ),
        ]

    def clean(self) -> None:
        if not self.acao.estrutural:
            raise ValidationError("Apenas competências estruturais podem ser delegadas nominalmente.")
        if self.delegante_id == self.delegado_id:
            raise ValidationError("O titular não pode delegar competência a si mesmo.")
        if self.delegado.exonerado:
            raise ValidationError("Servidor exonerado não pode receber delegação de competência.")
```

**`services/domain/autorizacao/avaliador.py`** — resolução unificada de concessões e delegações.
```python
class AvaliadorCompetencia:
    def __call__(self, entrada: AvaliacaoCompetenciaInput) -> AvaliacaoCompetenciaOutput:
        if not entrada.perfil.em_exercicio:
            return AvaliacaoCompetenciaOutput(slugs_liberados=frozenset())

        concessoes_batidas = self._concessoes_que_batem(entrada)
        delegacoes_batidas = self._delegacoes_que_batem(entrada)

        slugs_concedidos = frozenset(c.acao_slug for c in concessoes_batidas)
        slugs_delegados = frozenset(d.acao_slug for d in delegacoes_batidas)
        slugs_direcao = self._por_direcao(entrada)

        return AvaliacaoCompetenciaOutput(
            slugs_liberados=(slugs_concedidos | slugs_delegados | slugs_direcao) - entrada.slugs_exclusivos,
            unidades_delegadas=frozenset(d.unidade_id for d in delegacoes_batidas),
        )

    def _concessoes_que_batem(self, entrada: AvaliacaoCompetenciaInput) -> tuple[ConcessaoVigente, ...]:
        return tuple(
            c for c in entrada.concessoes
            if c.acao_ativa and any(self._caneta_bate(caneta, c) for caneta in entrada.perfil.canetas)
        )

    def _delegacoes_que_batem(self, entrada: AvaliacaoCompetenciaInput) -> tuple[DelegacaoVigente, ...]:
        return tuple(
            d for d in entrada.delegacoes
            if d.acao_ativa
        )
```

**`apps/competencias/schemas.py`** — DTO do formulário de delegação nominal.
```python
class NovaDelegacao(BaseModel):
    model_config = ConfigDict(frozen=True)

    delegado: int
    data_inicio: date
    data_fim: DataOpcional = None

    @field_validator("data_fim")
    @classmethod
    def _fim_nao_antecede_inicio(cls, fim: date | None, info: ValidationInfo) -> date | None:
        return conferir_fim(fim, info.data.get("data_inicio"), "Fim da delegação não pode anteceder o início.")
```

**`apps/competencias/delegacao.py`** — atos administrativos de delegação com conferência de alcance.
```python
@dataclass(frozen=True)
class DesfechoDelegacao:
    delegacao: Delegacao | None
    recusa: RecusaDeFormulario = RecusaDeFormulario()


def delegar_competencia(
    atribuicao: AtribuicaoUnidade,
    dados: NovaDelegacao,
    delegante: Perfil,
    alcance: Collection[int],
) -> DesfechoDelegacao:
    recusa = recusa_de_delegado_fora_do_alcance(dados.delegado, alcance)
    if recusa is not None:
        return DesfechoDelegacao(delegacao=None, recusa=recusa)
    return _desfecho(lambda: _gravar_delegacao(atribuicao, dados, delegante))


def encerrar_delegacao(delegacao: Delegacao) -> None:
    with transaction.atomic():
        encerrar_delegacao_em(delegacao, timezone.localdate())


def encerrar_delegacao_em(delegacao: Delegacao, dia: date) -> None:
    if dia < delegacao.data_inicio:
        delegacao.delete()
        return
    delegacao.data_fim = dia
    delegacao.save(update_fields=["data_fim"])


def recusa_de_delegado_fora_do_alcance(
    delegado_id: int,
    alcance: Collection[int],
) -> RecusaDeFormulario | None:
    lotacao = Perfil.objects.filter(pk=delegado_id).values_list("unidade_id", flat=True).first()
    if lotacao is not None and lotacao in alcance:
        return None
    return traduzir_recusa_delegacao(
        (ErroBruto(controle="delegado", tipo="fora_do_alcance", mensagem="Servidor fora do seu alcance."),)
    )


def candidatos_a_delegado(unidade: Unidade, alcance: Collection[int]) -> list[Perfil]:
    return list(
        Perfil.objects.filter(unidade_id__in=alcance, is_active=True)
        .exclude(impedimentos__data_fim__isnull=True)
        .select_related("unidade", "cargo_base", "cargo_comissao")
        .order_by("nome", "sobrenome")
    )
```

**`apps/competencias/consulta.py`** — cálculo do alcance compondo unidades dirigidas e delegadas.
```python
def montar_avaliacao(perfil: Perfil) -> AvaliacaoCompetenciaInput:
    canetas = canetas_do_perfil(perfil)
    unidades_das_canetas = frozenset(caneta.unidade_id for caneta in canetas)
    concessoes = ...
    hoje = timezone.localdate()
    delegacoes = tuple(
        DelegacaoVigente(
            acao_slug=d.acao.slug,
            acao_ativa=d.acao.ativa,
            unidade_id=d.unidade_id,
            delegado_id=d.delegado_id,
        )
        for d in Delegacao.objects.filter(
            delegado=perfil,
            data_inicio__lte=hoje,
        ).filter(
            Q(data_fim__isnull=True) | Q(data_fim__gte=hoje)
        ).select_related("acao")
    )
    return AvaliacaoCompetenciaInput(
        perfil=PerfilCompetencia(em_exercicio=perfil.em_exercicio, canetas=canetas),
        concessoes=concessoes,
        slugs_estruturais=_slugs_estruturais(),
        slugs_exclusivos=slugs_exclusivos(),
        delegacoes=delegacoes,
    )


def unidades_delegadas(perfil: Perfil) -> frozenset[int]:
    return avaliar_competencia(montar_avaliacao(perfil)).unidades_delegadas


def ramos_do_alcance(perfil: Perfil) -> tuple[NoHierarquia, ...]:
    if perfil.is_superuser:
        return tuple(posicao_de(raiz.pk).ego for raiz in Unidade.objects.filter(pai__isnull=True))
    partidas = unidades_dirigidas(perfil) | unidades_delegadas(perfil)
    arvores = {partida: posicao_de(partida).ego for partida in partidas}
    return tuple(
        arvore
        for partida, arvore in arvores.items()
        if not any(outra != partida and partida in arvores[outra].ids for outra in arvores)
    )
```

**`apps/competencias/views.py`** — rotas de delegação e revogação exigindo direção da unidade.
```python
@acao_protegida(ACAO_CONCEDER)
@require_POST
def delegar_servidor(request: HttpRequest) -> HttpResponse:
    unidade_id = int(request.POST["unidade"])
    atribuicao_id = int(request.POST["atribuicao"])
    atribuicao = _atribuicao_no_alvo(atribuicao_id, unidade_id)
    _exigir_direcao_para_delegar(atribuicao.unidade, _perfil(request))

    leitura = ler_nova_delegacao(request.POST.dict())
    alcance = alcance_do_perfil(_perfil(request))
    if leitura.dto is None:
        return _delegacao_recusada(request, atribuicao, leitura.recusa or RecusaDeFormulario())

    desfecho = delegar_competencia(atribuicao, leitura.dto, _perfil(request), alcance)
    if desfecho.delegacao is None:
        return _delegacao_recusada(request, atribuicao, desfecho.recusa)

    registrar_ato(
        request,
        operacao="delegar",
        alvo_tipo="acao_servidor",
        alvo_identificador=f"{atribuicao.acao.slug}:{desfecho.delegacao.delegado.rf}",
    )
    return render(
        request,
        TEMPLATE_POCO_CONCESSOES,
        contexto_poco_concessoes(atribuicao.unidade, _perfil(request), fechar_modal=True),
    )


@acao_protegida(ACAO_CONCEDER)
@require_POST
def revogar_delegacao(request: HttpRequest) -> HttpResponse:
    unidade_id = int(request.POST["unidade"])
    delegacao_id = int(request.POST["delegacao"])
    delegacao = get_object_or_404(Delegacao.objects.select_related("acao", "unidade", "delegado"), pk=delegacao_id)
    if delegacao.unidade_id != unidade_id:
        raise PermissionDenied
    _exigir_direcao_para_delegar(delegacao.unidade, _perfil(request))

    encerrar_delegacao(delegacao)
    registrar_ato(
        request,
        operacao="revogar",
        alvo_tipo="acao_servidor",
        alvo_identificador=f"{delegacao.acao.slug}:{delegacao.delegado.rf}",
    )
    return render(
        request,
        TEMPLATE_POCO_CONCESSOES,
        contexto_poco_concessoes(delegacao.unidade, _perfil(request), fechar_modal=True),
    )


def _exigir_direcao_para_delegar(unidade: Unidade, perfil: Perfil) -> None:
    if not (perfil.is_superuser or dirige(perfil, unidade)):
        raise PermissionDenied
```

**`templates/competencias/partials/_card_concessoes.html`** — cartão distinguindo ação estrutural (delegados nominais) de comum (cargos).
```django
<div class="flex-1 min-w-0">
  <div class="flex items-center gap-2">
    <p class="card-atribuicao-nome">{{ item.acao.nome }}</p>
    {% if item.acao.estrutural %}
      <span class="badge badge-success badge-soft badge-sm font-medium">Estrutural</span>
    {% endif %}
  </div>
  <p class="card-atribuicao-descricao">{{ item.acao.tooltip }}</p>
</div>
...
{% if item.acao.estrutural %}
  {% if item.delegacoes %}
    {% for delegacao in item.delegacoes %}
      <tr>
        <td>
          <div class="flex items-center gap-2">
            <span>{{ delegacao.delegado.nome_completo }}</span>
            <span class="text-xs text-base-content/60">({{ delegacao.delegado.unidade.sigla }})</span>
            <span class="badge badge-info badge-soft badge-sm font-medium">Delegada</span>
          </div>
        </td>
        <td class="w-10">
          {% if pode_delegar %}
            <button type="button" class="lata-concessao" hx-post="{% url 'competencias:revogar_delegacao' %}"
                    hx-vals='{"unidade": "{{ unidade_alvo.pk }}", "delegacao": "{{ delegacao.pk }}"}'
                    hx-target="#poco-concessoes" hx-swap="outerHTML">
              <span class="icone-acao icone-acao-pequeno etched etched-deeper"><svg viewBox="0 0 24 24"><use href="#glifo-lixeira"/></svg></span>
            </button>
          {% endif %}
        </td>
      </tr>
    {% endfor %}
  {% else %}
    <span class="card-atribuicao-vazio">Nenhum servidor delegado ainda.</span>
  {% endif %}
{% endif %}
```

## 7 · Caveats
A delegação é nominal a um servidor, e não a um cargo. Delegar competência estrutural é confiar a caneta
da direção a uma pessoa específica, não a todos os ocupantes de um cargo na unidade. O custo é que a saída
do servidor exige revogar a delegação e criar outra para o substituto dele, em vez de herança automática por cargo.

O alcance delegado desce o ramo inteiro a partir da unidade delegada. Quem delega transfere a capacidade
de atuar na sua unidade e nas subordinadas, espelhando a abrangência que o titular possui naquele ato. O custo
é que o delegado não pode ter seu alcance restrito a uma subunidade específica daquele ramo sem nova modelagem
de alcance customizado.

A cadeia de delegação para no primeiro elo e só quem dirige pode delegar. Impedir que quem recebeu uma
delegação a passe para terceiros preserva a hierarquia e evita a proliferação descontrolada de canetas na
instituição. O custo é que um delegado que chefia uma equipe não pode subdelegar a tarefa a seus liderados sem
a assinatura do dirigente da unidade de origem.

Delegação e concessão convivem na mesma tela de competências com modelos distintos. Ação estrutural usa
`Delegacao` (pessoa + período) e ação comum usa `Concessao` (cargo), unificadas no painel da unidade. O custo
é que o template do cartão e os endpoints de gravação se bifurcam entre cargo e servidor dependendo de
`acao.estrutural`.

O histórico registra a operação com o RF do delegado como alvo. O ato de delegar incide sobre uma pessoa
específica e a ação delegada, registrando `delegar` ou `revogar` com `acao.slug:delegado.rf`. O custo é que
consultar o histórico de delegações de um servidor exige buscar pelo RF dele no identificador do alvo.

## 8 · Testes (TDD)

**Comportamento**
- `test_delegacao_nominal_libera_acao_ao_servidor` — servidor que recebe delegação de ação estrutural
  passa a ter `has_perm(acao.slug)` como `True`. *(marker `banco`)*
- `test_delegacao_carrega_alcance_da_unidade_delegante` — o delegado alcança a unidade da delegação e
  todas as suas subordinadas. *(marker `banco`)*
- `test_delegado_pratica_ato_estrutural_no_ramo` — servidor delegado cadastra usuário ou cria unidade
  subordinada no ramo delegado com sucesso. *(marker `banco`)*
- `test_delegado_nao_herda_outras_competencias_nem_direcao` — o delegado não recebe as demais ações
  estruturais do titular e não vira dirigente da unidade. *(marker `banco`)*
- `test_delegado_pode_ser_de_unidade_subordinada` — titular de unidade pai delega para servidor lotado
  em unidade subordinada do seu ramo. *(marker `banco`)*
- `test_candidato_fora_do_alcance_e_recusado` — tentativa de delegar para servidor de outro ramo volta
  como recusa no controle `delegado`. *(marker `banco`)*
- `test_delegacao_com_periodo_futuro_nao_libera_hoje` — delegação com `data_inicio` futura não concede
  competência nem alcance na data corrente. *(marker `banco`)*
- `test_revogar_delegacao_encerra_vigencia_ou_apaga` — revogar delegação em curso fixa `data_fim=hoje`;
  revogar delegação futura apaga o registro. *(marker `banco`)*
- `test_substituto_do_titular_delega_durante_impedimento` — quem cobre o titular impedido responde pela
  direção e pode delegar competência estrutural. *(marker `banco`)*
- `test_delegacao_registra_operacoes_distintas` — grava `operacao="delegar"` na criação e `operacao="revogar"`
  no encerramento, com `acao.slug:delegado.rf` no alvo. *(marker `banco`)*

**Segurança da ação** (skill `acao-administrativa`; fora do teto)
- `test_anonimo_vai_ao_login_sem_registrar` — requisição anônima redireciona ao login e não grava execução.
  *(marker `banco`)*
- `test_sem_competencia_recebe_403_registrado` — servidor sem direção recebe 403 e a tentativa fica registrada.
  *(marker `banco`)*
- `test_delegado_nao_re_delega_estrutural` — servidor que recebeu delegação recebe 403 registrado ao tentar
  delegar a terceiros. *(marker `banco`)*
- `test_delegado_nao_revoga_delegacao_de_outrem` — servidor delegado recebe 403 ao tentar revogar delegações
  da unidade. *(marker `banco`)*
- `test_delegado_fora_do_exercicio_nao_exerce` — delegado impedido recebe 403; delegado exonerado recebe 302
  para o login. *(marker `banco`)*
- `test_delegado_nao_alcanca_unidade_superior` — delegado tenta praticar ato em unidade acima da unidade
  delegante e recebe 403 registrado. *(marker `banco`)*
- `test_delegado_nao_alcanca_ramo_irmao` — delegado tenta praticar ato em unidade de outro ramo e recebe
  403 registrado. *(marker `banco`)*
- `test_acao_inativa_nao_libera_delegado` — delegação de ação desativada não libera permissão.
  *(marker `banco`)*
- `test_cartao_estrutural_bloqueado_para_quem_nao_dirige` — painel renderizado para servidor comum omite
  o botão de delegar e latas de revogação. *(marker `banco`)*
- `test_escrita_so_por_post` — GET em rotas de delegar e revogar é recusado sem alteração de estado.
  *(marker `banco`)*
