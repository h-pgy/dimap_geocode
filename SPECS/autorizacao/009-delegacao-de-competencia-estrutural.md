---
spec: autorizacao/009
versao: v2
atualizado_em: 2026-08-24
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: delegar e revogar competência estrutural passam a exigir direção — a cadeia de delegação para no primeiro elo
---

# SPEC autorizacao/009 — Delegação: a concessão carrega o alcance

## 1 · User story
Quem dirige uma unidade da DIMAP delega a um cargo dela a execução de uma competência que é sua por
direção, na tela de conceder competência, para que quem recebe possa de fato praticar o ato na
unidade e nas subordinadas — e não apenas passar pela primeira barreira e ser recusado na segunda.
Quem recebe a delegação **exerce** a competência; não a passa adiante, porque a caneta de delegar é
de quem dirige.

## 2 · Condições de pronto
- [ ] **Concessão vigente carrega alcance**: quem a recebe alcança a unidade em que ela foi concedida
      e **todas as que estão abaixo dela**. Quem não recebeu concessão alguma e não dirige unidade
      alguma continua com alcance **vazio**.
- [ ] O delegado **pratica o ato de verdade**: cadastra servidor, cria e edita unidade dentro daquele
      ramo, sem dirigir unidade nenhuma. Fora do ramo, é recusado com **403 registrado**.
- [ ] Perfil **fora de exercício** não alcança nada por delegação, como não exerce competência
      alguma: a delegação não é uma terceira porta ao lado das duas que já existem.
- [ ] Na tela de conceder, competência **estrutural** se apresenta como **delegação**: o botão diz
      **Delegar**, com a aura, e o texto do modal diz o que a delegação significa. Competência não
      estrutural segue exatamente como hoje — botão **Conceder**, sem aura e sem confirmação.
- [ ] **Delegar não grava no primeiro clique**: a confirmação **substitui o corpo do modal**,
      avisando que a pessoa poderá executar o ato **na unidade e em todas as subordinadas a ela**.
      Cancelar não grava nada e devolve o modal com o cargo escolhido intacto.
- [ ] **Delegação não se re-delega**: só quem responde pela direção **delega e revoga** competência
      **estrutural**. Quem recebeu uma estrutural por concessão abre a tela de conceder e distribui as
      **não estruturais** do seu ramo; nas estruturais não vê o botão de conceder nem a lata, e o POST
      forjado é **403 registrado**, sem gravar nada.
- [ ] A delegação é ato registrado com **operação própria** (`delegar`), distinguível de `conceder`
      no histórico.
- [ ] O design foi aprovado no **mock**: as duas faces do **modal** — delegação (com a aura) e
      concessão comum — e as duas do **cartão** — o que oferece e o **bloqueado**, sem botão de
      conceder e sem lata, com a nota de que a competência é de quem dirige.
      **Nenhuma peça nova**: a aura é o átomo `.aura-onsen` da
      SPEC [user_admin/022](../user_admin/022-tornar-administrador.md), e a confirmação no lugar do
      corpo do modal é a coreografia que a SPEC [user_admin/020](../user_admin/020-unidade-como-ato-administrativo.md)
      já usa na transferência de unidade.

## 3 · Domínio
Nenhum model novo e nenhuma coluna nova: **a unidade da concessão já é dado gravado**
(`Concessao → AtribuicaoUnidade → unidade`). O que muda é o que se lê dela — hoje a concessão
responde só *que competência* o perfil tem, e passa a responder também *sobre qual ramo*.

A resposta sai do avaliador, e não de uma consulta nova, porque é **a mesma travessia** que já cruza
canetas contra concessões: separar as duas faria competência e alcance divergirem em silêncio.

A trava da re-delegação também não é campo novo. `Perfil.e_titular` é o **vínculo**, não quem exerce
— no impedimento do titular quem responde pela unidade é o substituto —, e a pergunta certa já tem
resposta em código: `dirige` / `unidades_dirigidas`, a **mesma porta** que o avaliador usa em
`_por_direcao` para liberar as estruturais. Delegar é passar adiante a caneta da direção, e só passa
adiante quem a tem **por direção**; quem a tem por concessão exerce e não redistribui.

**`services/domain/autorizacao/models.py`**
```python
class AvaliacaoCompetenciaOutput(BaseModel):
    slugs_liberados: frozenset[str]
    # ALTERADO nesta SPEC: as unidades em que o perfil recebeu competência por concessão. Delegar é
    # entregar a caneta E o alcance dela — sem isto o delegado passa no `has_perm` e é recusado no
    # `conferir_alvo`, que é a delegação funcionando pela metade.
    unidades_delegadas: frozenset[int] = frozenset()
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`AvaliadorCompetencia`, `Caneta`, `ConcessaoVigente`](003-avaliador-e-backend-de-autorizacao.md) —
  "quais concessões batem com as canetas deste perfil?"; a resposta já existe, e agora ela também diz
  em que unidade cada uma foi concedida.
- [`alcance_do_perfil`, `ramos_do_alcance`, `conferir_alvo`](004-protecao-de-rota-e-registro-de-execucao.md) —
  "de que unidades parte o alcance?"; passa a partir das dirigidas **mais** as delegadas.
- [`conceder`, `ComandoConcessao`, a tela e o modal](008-acao-conceder-competencia.md) — onde o ato
  acontece; o modal ganha a face de delegação e o passo de confirmação.
- [`Acao.estrutural`](001-catalogo-de-acoes-em-codigo.md) — "esta concessão é delegação?"; é o campo
  já projetado no banco que separa as duas faces do modal.
- [`dirige`, `unidades_dirigidas`](004-protecao-de-rota-e-registro-de-execucao.md) — "quem responde
  pela direção?"; a resposta que já libera as estruturais passa a dizer também quem pode delegá-las.
- [`.aura-onsen`](../user_admin/022-tornar-administrador.md) — o átomo do realce do ato de peso.

**Mock:** [009-mock-delegacao.html](009-mock-delegacao.html) — leia a skill `mock`.

## 4 · Fora de escopo
- **Alcance por ação**: o ramo delegado vale para toda ação que o perfil exerça, e não só para a que
  foi concedida — sem dono ainda (Caveats).
- **Revogação distinguível**: tirar uma delegação continua sendo registrado como `revogar`, igual a
  tirar uma concessão comum — sem dono ainda.
- **Delegação com prazo**, que expira sozinha, e **delegação nominal** a uma pessoa em vez de a um
  cargo — sem dono ainda.
- **Avisar o delegado** de que recebeu a competência — sem dono ainda.

## 5 · Peças de referência a compor
- `@services/domain/autorizacao/avaliador.py` → `AvaliadorCompetencia`, `_caneta_bate`: o cruzamento
  caneta × concessão, que passa a devolver duas coisas em vez de uma.
- `@apps/competencias/consulta.py` → `montar_avaliacao`, `unidades_dirigidas`, `ramos_do_alcance`,
  `alcance_do_perfil`: a borda banco → DTO e o cálculo do alcance.
- `@apps/competencias/views.py` → `conceder_cargo`, `revogar_cargo`, `_atribuicao_no_alvo`,
  `_concessao_no_alvo`: as duas rotas que ganham a barreira da direção.
- `@apps/competencias/context.py` → `contexto_modal_conceder`, `contexto_poco_concessoes`,
  `_atribuicoes_com_concessoes`: o contexto do modal e o do poço, que passa a receber o perfil.
- `@templates/competencias/partials/_modal_conceder.html`: o modal que ganha as duas faces.
- `@templates/competencias/partials/_card_concessoes.html`: o cartão de onde o botão de conceder e a
  lata somem quando quem olha não dirige.
- `@templates/unidades/partials/_modal_editar_unidade.html`: a confirmação que volta no lugar, com o
  que foi preenchido preservado — o molde da transferência (SPEC user_admin/020).
- Skills: `acao-administrativa`, `componentes-frontend`, `daisyui`, `htmx`, `mock`,
  `escrever-testes`, `test-django-views`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`services/domain/autorizacao/avaliador.py`** — uma travessia, duas respostas.
```python
def __call__(self, entrada: AvaliacaoCompetenciaInput) -> AvaliacaoCompetenciaOutput:
    if not entrada.perfil.em_exercicio:
        # Vazio nos DOIS campos: fora de exercício não há caneta, e sem caneta não há ramo.
        return AvaliacaoCompetenciaOutput(slugs_liberados=frozenset())
    batidas = self._concessoes_que_batem(entrada)
    return AvaliacaoCompetenciaOutput(
        slugs_liberados=(
            frozenset(concessao.acao_slug for concessao in batidas) | self._por_direcao(entrada)
        )
        - entrada.slugs_exclusivos,
        # A MESMA lista que libera o slug diz em que unidade ele foi concedido. Duas travessias
        # separadas divergiriam no primeiro `if` que uma delas ganhasse e a outra não.
        unidades_delegadas=frozenset(concessao.unidade_id for concessao in batidas),
    )


def _concessoes_que_batem(self, entrada: AvaliacaoCompetenciaInput) -> tuple[ConcessaoVigente, ...]:
    """O que era `_por_concessao`, devolvendo as concessões em vez dos slugs delas: o slug continua
    saindo daqui, e o alcance passa a sair também."""
    return tuple(
        concessao
        for concessao in entrada.concessoes
        if concessao.acao_ativa
        and any(self._caneta_bate(caneta, concessao) for caneta in entrada.perfil.canetas)
    )
```

**`apps/competencias/consulta.py`** — o alcance passa a ter duas nascentes, e o resto do cálculo é o
mesmo: o descarte do ramo contido já cuida de sobreposição entre elas.
```python
def unidades_delegadas(perfil: Perfil) -> frozenset[int]:
    """As unidades em que este perfil recebeu competência por concessão. Sai do avaliador, e não de
    uma consulta própria, porque quem sabe se a concessão vale para ESTA caneta é ele."""
    return avaliar_competencia(montar_avaliacao(perfil)).unidades_delegadas


def ramos_do_alcance(perfil: Perfil) -> tuple[NoHierarquia, ...]:
    if perfil.is_superuser:
        return tuple(posicao_de(raiz.pk).ego for raiz in Unidade.objects.filter(pai__isnull=True))
    # ALTERADO nesta SPEC: dirigir e receber por delegação são duas portas para o mesmo alcance.
    partidas = unidades_dirigidas(perfil) | unidades_delegadas(perfil)
    arvores = {partida: posicao_de(partida).ego for partida in partidas}
    return tuple(
        arvore
        for partida, arvore in arvores.items()
        if not any(outra != partida and partida in arvores[outra].ids for outra in arvores)
    )


def responde_por_direcao(perfil: Perfil) -> bool:
    """Delegar é passar adiante a caneta de quem dirige — quem a recebeu por concessão não a passa.
    `e_titular` não responde isto: é o vínculo, e no impedimento quem dirige é o substituto."""
    # `is_superuser` aqui dentro, e não em cada chamador, pelo mesmo motivo de `ramos_do_alcance`.
    return perfil.is_superuser or bool(unidades_dirigidas(perfil))
```

**`apps/competencias/context.py`** — a face do modal sai do campo já projetado, não de uma lista.
```python
def contexto_modal_conceder(
    atribuicao: AtribuicaoUnidade,
    valores: Mapping[str, str] | None = None,
    confirmando: bool = False,
) -> dict[str, Any]:
    return {
        "atribuicao": atribuicao,
        "unidade_alvo": atribuicao.unidade,
        "cargos_base": CargoBase.objects.order_by("nome"),
        "cargos_comissao": CargoComissao.objects.order_by("nome"),
        # Estrutural é a competência que quem dirige já tem: concedê-la a outro cargo é delegar a
        # execução dela. Nenhuma lista de slugs — o contrato já respondeu isso no boot.
        "delegacao": atribuicao.acao.estrutural,
        "confirmando": confirmando,
        "valores": valores or {},
    }


def contexto_poco_concessoes(
    unidade_alvo: Unidade | None,
    perfil: Perfil,
    *,
    fechar_modal: bool = False,
) -> dict[str, Any]:
    return {
        "unidade_alvo": unidade_alvo,
        # ALTERADO nesta SPEC: o poço passa a receber o perfil, porque o que cada cartão oferece
        # deixou de depender só da unidade. Filtrar aqui é UX — a recusa de verdade é da rota.
        "atribuicoes": _atribuicoes_com_concessoes(unidade_alvo, responde_por_direcao(perfil)),
        "fechar_modal": fechar_modal,
    }


def _atribuicoes_com_concessoes(
    unidade: Unidade | None,
    pode_delegar: bool,
) -> list[dict[str, Any]]:
    ...
    return [
        {
            ...,
            # Um booleano por cartão, e não dois no contexto: o template pergunta uma coisa só.
            "bloqueada": atribuicao.acao.estrutural and not pode_delegar,
        }
        for atribuicao in atribuicoes
    ]
```

**`apps/competencias/views.py`** — a confirmação é um desvio da mesma rota, no molde da transferência
de unidade: nada é gravado antes dela, e a rota de confirmação não altera estado.
```python
@acao_protegida(ACAO_CONCEDER)
@require_POST
def conceder_cargo(request: HttpRequest) -> HttpResponse:
    comando = ComandoConcessao(...)
    atribuicao = _atribuicao_no_alvo(comando.atribuicao_id, comando.unidade_alvo_id)
    # Barreira que o decorator não tem como cumprir, pela mesma razão de `_atribuicao_no_alvo`:
    # qual ação a atribuição carrega só se sabe depois de resolvê-la. O `raise` vira 403 registrado.
    _exigir_direcao_se_estrutural(atribuicao.acao, _perfil(request))
    if atribuicao.acao.estrutural and not request.POST.get("confirmado"):
        # Volta o MODAL, não uma página de aviso: o alvo do hx-post é o poço das concessões, e o
        # que se devolve tem que caber nele. Nada gravado, e o cargo escolhido preservado.
        return render(
            request,
            TEMPLATE_MODAL_CONCEDER,
            contexto_modal_conceder(atribuicao, valores=request.POST.dict(), confirmando=True),
        )
    concessao = conceder_cargo_dominio(comando, concedida_por_id=_perfil(request).pk)
    registrar_ato(
        request,
        # Duas operações para o mesmo ato, pelo mesmo motivo de sempre: delegar a caneta de quem
        # dirige não é o mesmo que conceder uma competência comum, e o histórico separa os dois.
        operacao="delegar" if atribuicao.acao.estrutural else "conceder",
        alvo_tipo="acao_cargo",
        alvo_identificador=f"{atribuicao.acao.slug}:{identificador_cargo(concessao)}",
    )
    return render(
        request,
        TEMPLATE_POCO_CONCESSOES,
        contexto_poco_concessoes(atribuicao.unidade, _perfil(request), fechar_modal=True),
    )


@acao_protegida(ACAO_CONCEDER)
@require_POST
def revogar_cargo(request: HttpRequest) -> HttpResponse:
    comando = ComandoRevogacao(...)
    concessao = _concessao_no_alvo(comando.concessao_id, comando.unidade_alvo_id)
    # Simétrico ao conceder: quem não pôde entregar a caneta também não tira a que outro recebeu.
    _exigir_direcao_se_estrutural(concessao.atribuicao.acao, _perfil(request))
    ...


def _exigir_direcao_se_estrutural(acao: Acao, perfil: Perfil) -> None:
    """A competência estrutural é de quem dirige: concedê-la é delegar, e delegação não se
    re-delega. A não estrutural segue como hoje — quem tem a caneta de conceder distribui."""
    if acao.estrutural and not responde_por_direcao(perfil):
        raise PermissionDenied
```

**`templates/competencias/partials/_modal_conceder.html`** — as duas faces do mesmo modal.
```django
{% if delegacao %}
  <div class="aura aura-onsen">
    <button type="submit" class="btn btn-onsen btn-sm">Delegar</button>
  </div>
{% else %}
  <button type="submit" class="btn btn-onsen btn-sm">Conceder</button>
{% endif %}
```

**`templates/competencias/partials/_card_concessoes.html`** — o cartão que só oferece o que a rota
aceitaria. Nada de `disabled`: botão apagado convida a tentar e a resposta é 403 registrado. A aura
fica no botão do modal, onde o ato acontece — no cartão ela marcaria hoje quase todos.
```django
{% if not item.bloqueada %}
  <label for="modal-conceder" class="btn btn-glass btn-sm btn-circle" ...>…</label>
{% endif %}
…
{% if item.bloqueada %}
  <span class="card-atribuicao-vazio">Competência de quem dirige a unidade.</span>
{% endif %}
```

## 7 · Caveats
O ramo delegado vale para **toda** ação que o perfil exerça, e não só para a que foi concedida: o
alcance é um conjunto de unidades, calculado uma vez, e não uma resposta por ação. Torná-lo por ação
mudaria a assinatura de `conferir_alvo`, de `pode_executar` e de todos os selects que hoje recortam
listas por `alcance_do_perfil`. O custo é que quem recebe duas concessões distintas passa a alcançar
a união dos dois ramos para as duas — na prática, o mesmo ramo, porque a concessão só bate na unidade
em que a pessoa está lotada.

`alcance_do_perfil` passa a chamar o avaliador, e o backend de autorização já o chamou no mesmo
request para responder ao `has_perm`. São duas montagens da mesma entrada por requisição, cada uma
com sua consulta de concessões. Para dezenas de usuários internos isso não se mede, e memorizar a
avaliação por request custaria um cache de ciclo de vida que hoje não existe em lugar nenhum.

A cadeia de delegação para no primeiro elo — e o preço é que delegar `competencias.conceder` entrega
hoje quase nada: **toda** ação inscrita é estrutural, salvo `unidades.criar_unidade_raiz`, que é
exclusiva do superusuário. Quem recebe essa delegação abre a tela, vê o ramo inteiro e não tem o que
conceder enquanto não existir ação não estrutural. É a trava funcionando, não efeito colateral: a
alternativa a cortar a cadeia é uma lista de ações indelegáveis, que é a configuração em runtime que
o §3.5 recusa.

A trava mora na view, e não no contrato da ação nem no decorator, pela mesma razão de
`_atribuicao_no_alvo` (Caveats da SPEC 008): qual ação a atribuição-alvo carrega só se sabe depois de
resolvê-la. O contrato de `ACAO_CONCEDER` continua um só — não há ação `delegar` separada, porque
delegar e conceder são o mesmo ato sobre objetos de natureza diferente.

Nada impede o delegado de conceder a si mesmo uma competência **não estrutural** do próprio ramo — a
tela distribui por cargo, e o cargo dele está lá. Recusar exigiria comparar cargo do concedente com
cargo concedido, regra que nenhuma SPEC pediu; o que responde é o registro, que guarda quem assinou.

Uma concessão de ação **sem alcance declarado** também amplia o alcance de quem a recebeu, porque a
nascente é a concessão e não a ação. Distinguir exigiria justamente o alcance por ação do primeiro
caveat. O custo é uma ampliação que nenhuma ação de hoje usa — as sem alcance não conferem alvo.

## 8 · Testes (TDD)

**Comportamento**
- `test_concessao_traz_a_unidade_para_o_alcance` — perfil que não dirige nada e tem concessão vigente
  na sua unidade alcança essa unidade. *(marker `banco`)*
- `test_alcance_delegado_desce_o_ramo` — o mesmo perfil alcança as unidades abaixo dela, e **não** as
  de outro ramo. *(marker `banco`)*
- `test_sem_concessao_e_sem_direcao_alcance_vazio` — o alcance segue vazio para quem não tem nenhuma
  das duas portas. *(marker `banco`)*
- `test_delegado_cadastra_servidor_no_ramo` — com a competência estrutural concedida, o POST de
  cadastrar servidor numa unidade do ramo grava; numa de outro ramo, é **403 registrado**.
  *(marker `banco`)*
- `test_delegar_pede_confirmacao_antes_de_gravar` — o primeiro POST de uma atribuição estrutural
  devolve o modal em confirmação, com o cargo escolhido preservado, e **não grava concessão alguma**.
  *(marker `banco`)*
- `test_conceder_nao_estrutural_grava_de_primeira` — atribuição não estrutural não passa pela
  confirmação e grava no primeiro POST. *(marker `banco`)*
- `test_delegado_concede_nao_estrutural` — quem tem `competencias.conceder` por concessão concede uma
  atribuição **não estrutural** do ramo, e grava. A ação não estrutural é montada no banco pelo
  próprio teste: no registro de hoje a única é a raiz, exclusiva do superusuário (Caveats).
  *(marker `banco`)*
- `test_substituto_delega_durante_a_cobertura` — quem cobre o titular impedido responde pela direção
  e delega; o titular impedido, não. *(marker `banco`)*
- `test_delegacao_registra_operacao_propria` — a execução gravada tem operação `delegar`; a concessão
  comum, `conceder`. *(marker `banco`)*

**Segurança da ação** (skill `acao-administrativa`; fora do teto)
- `test_fora_de_exercicio_nao_alcanca_por_delegacao` — impedido vigente com concessão gravada tem
  alcance vazio e recebe 403 no ato. *(marker `banco`)*
- `test_concessao_de_outra_unidade_nao_amplia_alcance` — concessão gravada em unidade que não é a da
  caneta do perfil não entra no alcance dele. *(marker `banco`)*
- `test_confirmacao_nao_altera_estado` — a resposta de confirmação não cria concessão, e repeti-la
  não cria nenhuma. *(marker `banco`)*
- `test_delegado_nao_alcanca_acima` — o delegado não alcança a unidade superior à que recebeu, nem a
  raiz. *(marker `banco`)*
- `test_delegado_nao_delega_de_novo` — quem tem `competencias.conceder` por concessão recebe **403
  registrado** ao conceder atribuição estrutural, e nenhuma concessão é criada. *(marker `banco`)*
- `test_delegado_nao_revoga_estrutural` — o mesmo perfil recebe 403 registrado ao revogar concessão de
  ação estrutural, e a concessão continua de pé. *(marker `banco`)*
- `test_cartao_estrutural_nao_oferece_botao_ao_delegado` — o poço renderizado para ele não traz o
  botão de conceder nem a lata nos cartões estruturais, e traz nos da ação não estrutural do teste.
  *(marker `banco`)*
