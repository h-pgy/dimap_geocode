---
spec: user_admin/024
versao: v2
atualizado_em: 2026-08-25
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: designação de substituto oferecida também no cartão de direção da página da unidade
---

# SPEC user_admin/024 — Designar substituto como ato administrativo

## 1 · User story
Quem dirige uma unidade da DIMAP designa quem responde pelo cargo de um servidor impedido — e troca
ou encerra essa cobertura —, nos cartões de afastamento da página do servidor, no cartão de direção da
página da unidade ou por um modal de acesso direto, para que a substituição passe a ser ato assinado e
rastreável em vez de diálogo sem destino.

## 2 · Condições de pronto
- [x] **Designar substituto** é ação inscrita no catálogo, **estrutural** e com alcance pela
      **lotação do servidor substituído, lida no banco**: quem dirige a unidade dele — ou uma acima
      dela — pratica o ato **sem concessão gravada**; quem não dirige e não recebeu delegação recebe
      **403 registrado**.
- [x] **Designar grava**: a cobertura entra na agenda e na calha do cartão sem recarregar a página.
      Período que não cabe no afastamento, ou substituto já comprometido, volta como **recusa em
      português no próprio modal**, e nada é gravado.
- [x] **Trocar grava pela mesma competência**: encerra a cobertura anterior **na véspera** do dia em
      que a nova assume e designa a nova na mesma transação; a que saiu continua na lista com o
      período que exerceu.
- [x] **Encerrar grava pela mesma competência**: cobertura em curso termina **hoje** e fica
      registrada; cobertura que ainda não começou é **apagada**.
- [x] O substituto escolhido precisa estar **no alcance de quem assina**: as duas listas do diálogo
      só oferecem quem está, e id de fora volta como **recusa** com realce no controle, sem gravar.
- [x] Os botões de designar, trocar e encerrar — inclusive no cartão de substituto da página da unidade
      sem direção — **só são renderizados** para quem exerce a ação sobre a unidade daquele servidor,
      e o mesmo vale para os modais, que nascem de rota protegida.
- [x] A página da unidade com titular impedido e sem substituto oferece **designar substituto** no
      cartão de substituição e atualiza o painel da unidade ao gravar, sem recarregar a tela.
- [x] O **modal da rota direta** escolhe a unidade — recortada ao alcance de quem abre — e, dentro
      dela, o servidor, e a face **reflete o estado do escolhido**: sem cargo em comissão, sem
      impedimento em aberto, afastamento já coberto, ou o formulário da designação. Com mais de um
      afastamento em aberto, um select escolhe qual, sem recarregar a tela. A ação é **item do
      `MENU_ADMINISTRADOR`**.
- [x] Os atos são **registrados** (SPEC [autorizacao/004](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md)),
      **distinguíveis pela operação** (`designar`, `trocar` e `encerrar`) e com o **RF do
      substituído** como alvo.
- [x] O design foi aprovado no **mock**, e peça nova foi portada para `static/src/tema-dimap.dev.css`
      e renderizada no styleguide antes de qualquer template da aplicação usá-la. **Nenhuma peça
      nova**: os diálogos e o modal direto compõem `.select-onsen`, `.tarja-vinculo`,
      `.campo-realce-erro` e o poço já existentes, e o único artefato novo é o **par de ícones** da
      ação, composto de `#glifo-substituto`.

## 3 · Domínio
Nenhum model novo e nenhuma coluna nova: `Impedimento`, `Substituicao` e os atos
`designar_substituto`, `trocar_substituto` e `encerrar_substituicao` já são domínio gravado pela
SPEC [015](015-exercicio-e-substituicao.md). O que esta SPEC modela é a **competência** que autoriza
esses atos, o **recorte do substituto** ao alcance de quem assina, o **ponto de entrada na página da
unidade** e o **desfecho** pelo qual a recusa do ato volta para a tela.

A substituição passa a ter **módulo próprio**, `apps/user_admin/substituicao.py`: os atos, as
leituras da cobertura e a montagem dos DTOs de designação saem de `exercicio.py`, que fica com o
impedimento e o exercício derivado. Cada ato tem **uma porta pública**, que devolve desfecho e nunca
levanta; a escrita que levanta é privada do módulo, e é o levantar dela, dentro da transação, que faz
a troca desfazer a véspera já gravada quando a designação nova não cola. A dependência é de mão
única: `exercicio.py` chama `substituicao.py` para truncar a cobertura no retorno ao exercício, e
nada em `substituicao.py` conhece o impedimento além do model.

O alcance é o mesmo do impedimento: o ato incide sobre uma **pessoa** — o substituído —, e a unidade
a conferir é a lotação dela. Na página da unidade sem direção (`direcao == "sem_direcao"`), a unidade
aponta o `titular` e o respectivo `titular_impedimento` vigente para abrir o mesmo `modal_designar`,
garantindo que a designação ocorra sobre o afastamento ativo da chefia sem criar rotas nem formulários
paralelos.

Os DTOs de designação ganham o `frozen` e a conferência de período dos demais DTOs de formulário —
é ela que aponta o controle que a tela precisa realçar.

**`apps/user_admin/schemas.py`**
```python
class NovaSubstituicao(BaseModel):
    """ALTERADO nesta SPEC: ganha o `frozen` e a conferência do período."""

    model_config = ConfigDict(frozen=True)

    substituto: int
    # Em branco continua valendo: é assim que a designação pede "o primeiro pedaço descoberto".
    data_inicio: DataOpcional = None
    data_fim: DataOpcional = None

    @field_validator("data_fim")
    @classmethod
    def _fim_nao_antecede_inicio(cls, fim: date | None, info: ValidationInfo) -> date | None:
        ...


class TrocaDeSubstituto(BaseModel):
    """ALTERADO nesta SPEC: mesmo `frozen` e mesma conferência."""

    model_config = ConfigDict(frozen=True)

    substituto: int
    # "Assume em" — obrigatório, porque é a véspera dela que encerra a substituição que sai.
    data_inicio: date
    data_fim: DataOpcional = None

    @field_validator("data_fim")
    @classmethod
    def _fim_nao_antecede_inicio(cls, fim: date | None, info: ValidationInfo) -> date | None:
        ...
```

**`apps/user_admin/substituicao.py`**
```python
@dataclass(frozen=True)
class DesfechoSubstituicao:
    """Recado do ato para a view — mesma natureza do `DesfechoAdministrador` de `administrador.py`.
    Ou a cobertura gravada, ou a recusa que a tela mostra: nunca as duas, nunca nenhuma."""

    substituicao: Substituicao | None
    recusa: RecusaDeFormulario = RecusaDeFormulario()
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`designar_substituto`, `trocar_substituto`, `encerrar_substituicao`, `lacuna_proposta`,
  `candidatos_a_substituto`](015-exercicio-e-substituicao.md) — as escritas em transação e a
  proposta de período; nada muda nelas, só passam a ter quem as chame.
- [`estado_da_direcao`, `avaliar_direcao`](016-pagina-da-unidade.md) — "a unidade está sem direção?";
  se estiver (`sem_direcao`), o cartão de substituição oferece o botão de designar.
- [`Acao`, `estrutural`, `instanciar_acao`](../autorizacao/001-catalogo-de-acoes-em-codigo.md) —
  "quem exerce esta ação?"; a mesma resposta de registrar impedimento: quem responde pela direção da
  unidade do substituído, sem atribuição nem concessão.
- [`LotacaoDoServidor`, `acao_protegida`, `conferir_alvo`, `registrar_ato`, `pode_executar`](023-impedimento-como-ato-administrativo.md) —
  a barreira, a conferência do alvo pela lotação e o rastro; o alcance é reusado como está.
- [`alcance_do_perfil`](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md) — "quais
  unidades quem assina alcança?"; é esse conjunto que recorta tanto o select de unidades quanto o
  universo de candidatos.
- [a delegação da competência estrutural](../autorizacao/009-delegacao-de-competencia-estrutural.md) —
  "como o titular passa esta caneta adiante?"; nada a escrever: a ação nasce estrutural e a
  delegação alcança toda estrutural pelo mesmo caminho.
- [`ContratoMenu`, `ItemDeMenu`, `MENU_ADMINISTRADOR`](../autorizacao/005-contrato-de-menu-e-router.md) —
  "onde esta ação se oferece?"; é o menu que a pinça.
- [`Formulario`, `LeitorDeFormulario`, `TradutorDeRecusa`](../formularios/001-erros-de-formulario.md) —
  "como esta recusa se diz, e qual controle ela realça?"; a substituição ganha catálogo próprio, com
  três controles.
- [o poço do modal e o swap fora de banda](../criacao_usuarios/005-editar-servidor.md) — a
  coreografia de abrir por rota, recusar no lugar e fechar esvaziando o poço.

**Mock:** [024-mock-substituicao.html](024-mock-substituicao.html) — leia a skill `mock`.

## 4 · Fora de escopo
- **Trocar e encerrar pela rota direta**: o modal direto oferece só designar — sem dono ainda.
- **Trocar e encerrar na página da unidade**: a página da unidade oferece apenas designar quando a
  unidade está sem direção; a troca e o encerramento ocorrem na agenda da página do servidor — sem dono
  ainda.
- **Exonerar servidor** (`is_active`), a outra causa de sair do exercício — sem dono ainda.
- **Avisar o substituto** de que foi designado, e o substituído de que a cobertura mudou — sem dono
  ainda (herdado da SPEC [023](023-impedimento-como-ato-administrativo.md)).
- **Anexar documento comprobatório** à designação — sem dono ainda.
- **Renderizar o `MENU_ADMINISTRADOR`** em alguma tela: o item é inscrito, mas nenhuma tela desenha
  o menu ainda — sem dono ainda (herdado da SPEC 023).

## 5 · Peças de referência a compor
- `@apps/user_admin/exercicio.py` → `designar_substituto`, `trocar_substituto`,
  `encerrar_substituicao`, `lacuna_proposta`, `candidatos_a_substituto`, `designacao_de`,
  `periodo_de`: os atos em transação, a proposta de período e as leituras da cobertura, que mudam de
  módulo sem mudar de regra.
- `@apps/user_admin/administrador.py` → `DesfechoAdministrador`, `recusa_de_auto_revogacao`: o molde
  do ato que devolve recusa em vez de levantar.
- `@apps/core/erros_formulario.py` → `de_validation_error`: a ponte do `ValidationError` do model.
- `@apps/competencias/protecao.py` → `acao_protegida`, `registrar_ato`, `pode_executar`; `@apps/competencias/consulta.py` → `alcance_do_perfil`.
- `@apps/unidades/context.py` → `contexto_unidade`; `@templates/unidades/partials/_secao_direcao.html`: a seção de direção da página da unidade.
- `@apps/user_admin/views.py` → `_secao_atualizada`, `_autor`, `_perfil`; `@templates/user_admin/partials/_impedimento_concluido.html`: a resposta que fecha o modal e devolve a seção.
- `@apps/user_admin/context.py` → `contexto_exercicio`, `_universos_de_candidatos`, `_candidatos`,
  `_opcoes_de_servidor`, `_icone_impedimento`: a seção inteira, os candidatos e o segundo select.
- `@templates/user_admin/partials/_modal_designar.html`, `_modal_encerrar.html`: os diálogos que
  ganham destino.
- `@templates/user_admin/partials/_modal_registrar_impedimento.html`, `_opcoes_servidor.html`,
  `_form_impedimento.html`: o molde do modal de rota direta, dos selects encadeados e da face.
- `@templates/unidades/partials/_glifos_unidade.html`, `@templates/user_admin/partials/_glifos_exercicio.html` → `#glifo-substituto`: de onde sai o desenho do par de ícones.
- Skills: `acao-administrativa`, `erros-de-formulario`, `componentes-frontend`, `daisyui`, `htmx`,
  `mock`, `escrever-testes`, `test-django-views`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`apps/user_admin/acoes_declaradas.py`** — a ação nova, ao lado das quatro que já moram aqui.
```python
ACAO_DESIGNAR_SUBSTITUTO = instanciar_acao(
    slug="user_admin.designar_substituto",
    nome="Designar substituto",
    nome_curto="Substituto",
    tooltip="Designa quem responde pelo cargo de um servidor impedido — troca e encerra a cobertura.",
    # A rota do modal direto, e não as de gravação, que recebem o servidor no caminho.
    url_name="user_admin:modal_designar_substituto",
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Titular da área a exerce por dirigir, sem concessão gravada — e é por ser estrutural que ela é
    # delegável (SPEC autorizacao/009).
    estrutural=True,
    # O MESMO alcance do impedimento, sem subtipo novo: o ato incide sobre o substituído, e o
    # impedimento e a substituição descem no caminho ABAIXO dele, lidos escopados por ele.
    alcance=LotacaoDoServidor(),
)
```

**`apps/user_admin/schemas.py`** — a conferência de período escrita uma vez para os três formulários
de data do app.
```python
def conferir_fim(fim: date | None, inicio: date | None, mensagem: str) -> date | None:
    # Um predicado só para impedimento, designação e troca: três cópias da mesma comparação
    # divergiriam na primeira mudança. A frase vem de fora porque cada tela nomeia seus controles.
    if fim is not None and inicio is not None and fim < inicio:
        raise PydanticCustomError("fim_antes_do_inicio", mensagem)
    return fim


ERRO_FIM_ANTES_DO_INICIO_SUBSTITUICAO = (
    "Substitui até: não pode ser anterior ao início da substituição."
)


class NovaSubstituicao(BaseModel):
    ...

    @field_validator("data_fim")
    @classmethod
    def _fim_nao_antecede_inicio(cls, fim: date | None, info: ValidationInfo) -> date | None:
        # Validador de CAMPO, e não de model: o de model nasce com `loc` vazio, e recusa sem
        # controle não realça campo algum. `data_inicio` é declarado antes e já está em `info.data`.
        return conferir_fim(fim, info.data.get("data_inicio"), ERRO_FIM_ANTES_DO_INICIO_SUBSTITUICAO)
```

**`apps/user_admin/formularios.py`** — o catálogo da substituição, irmão do do impedimento.
```python
FORMULARIO_SUBSTITUICAO = Formulario(
    campos=(
        # `substituto` é o `name=` dos DOIS selects do diálogo — o da unidade e o ampliado: o
        # realce precisa cair no que estiver visível, e os dois se chamam igual.
        CampoDeFormulario(controle="substituto", rotulo="Servidor"),
        CampoDeFormulario(controle="data_inicio", rotulo="Início da substituição"),
        CampoDeFormulario(
            controle="data_fim",
            rotulo="Fim da substituição",
            regras={
                "fim_antes_do_inicio": RegraDeErro(mensagem=ERRO_FIM_ANTES_DO_INICIO_SUBSTITUICAO)
            },
        ),
    ),
)

ler_nova_substituicao = LeitorDeFormulario(NovaSubstituicao, FORMULARIO_SUBSTITUICAO)
ler_troca_de_substituto = LeitorDeFormulario(TrocaDeSubstituto, FORMULARIO_SUBSTITUICAO)
traduzir_recusa_substituicao = TradutorDeRecusa(FORMULARIO_SUBSTITUICAO)
```

**`apps/user_admin/substituicao.py`** — o módulo da substituição, que recebe de `exercicio.py` os
três atos, as leituras da cobertura (`substituicao_vigente`, `substituicao_que_exerce`,
`substituicoes_do_impedimento`, `trechos_do_impedimento`, `lacuna_proposta`,
`candidatos_a_substituto`, `designacao_de`) e a conversão de período (`periodo_de`, `TemPeriodo`).
Uma porta pública por ato: ela confere o alcance, chama a escrita privada e traduz a recusa.
```python
def designar_substituto(
    impedimento: Impedimento,
    dados: NovaSubstituicao,
    alcance: Collection[int] | None = None,
) -> DesfechoSubstituicao:
    """ALTERADO nesta SPEC: devolve desfecho em vez de levantar, e recebe o alcance de quem assina.
    Porta única — quem grava uma designação passa por aqui, e por aqui passa a conferência."""
    if alcance is not None:
        recusa = recusa_de_substituto_fora_do_alcance(dados.substituto, alcance)
        if recusa is not None:
            return DesfechoSubstituicao(substituicao=None, recusa=recusa)
    return _desfecho(lambda: _gravar_designacao(impedimento, dados))


def trocar_substituto(
    atual: Substituicao,
    dados: TrocaDeSubstituto,
    alcance: Collection[int] | None = None,
) -> DesfechoSubstituicao:
    """ALTERADO nesta SPEC: mesmo desfecho e mesma conferência."""
    if alcance is not None:
        recusa = recusa_de_substituto_fora_do_alcance(dados.substituto, alcance)
        if recusa is not None:
            return DesfechoSubstituicao(substituicao=None, recusa=recusa)
    return _desfecho(lambda: _gravar_troca(atual, dados))


def _gravar_designacao(impedimento: Impedimento, dados: NovaSubstituicao) -> Substituicao:
    """A escrita que LEVANTA, privada do módulo. É o `full_clean` que recusa a designação inválida,
    e é o levantar dele que a troca usa para abortar a transação."""
    with transaction.atomic():
        periodo = _periodo_da_designacao(impedimento, dados)
        substituicao = Substituicao(...)
        substituicao.full_clean()
        substituicao.save()
        return substituicao


def _gravar_troca(atual: Substituicao, dados: TrocaDeSubstituto) -> Substituicao:
    with transaction.atomic():
        # A véspera primeiro, e a designação depois: se a nova não colar, o `full_clean` levanta
        # daqui de dentro e o `atomic` desfaz a véspera. É por isso que a escrita privada não pode
        # devolver desfecho — desfecho comitaria a anterior encurtada e nenhuma nova no lugar.
        encerrar_substituicao_em(atual, dados.data_inicio - DIA)
        return _gravar_designacao(atual.impedimento, NovaSubstituicao(...))


def encerrar_substituicao_em(substituicao: Substituicao, dia: date) -> None:
    """Público porque `retornar_ao_exercicio` trunca por aqui as coberturas em curso — é a única
    coisa que `exercicio.py` pede a este módulo, e o que mantém a dependência de mão única."""
    ...


ERRO_SUBSTITUTO_FORA_DO_ALCANCE = (
    "Servidor: fora do seu alcance — só quem está no seu ramo pode ser designado."
)


def recusa_de_substituto_fora_do_alcance(
    substituto_id: int,
    alcance: Collection[int],
) -> RecusaDeFormulario | None:
    """A regra que prende a designação ao ramo de quem assina. Mora aqui, e não em cada ato: designar
    e trocar escrevem o mesmo vínculo, e a regra escrita duas vezes divergiria na primeira mudança."""
    lotacao = Perfil.objects.filter(pk=substituto_id).values_list("unidade_id", flat=True).first()
    if lotacao is not None and lotacao in alcance:
        return None
    return traduzir_recusa_substituicao(
        (
            ErroBruto(
                controle="substituto",
                tipo="fora_do_alcance",
                mensagem=ERRO_SUBSTITUTO_FORA_DO_ALCANCE,
            ),
        )
    )


def _desfecho(escrever: Callable[[], Substituicao]) -> DesfechoSubstituicao:
    # O `try/except` de REGRA mora no módulo do ato, nunca na view (skill acao-administrativa). A
    # recusa do `clean()` chega em `__all__`, sem controle: vira tarja geral, não realce.
    try:
        return DesfechoSubstituicao(substituicao=escrever())
    except DjangoValidationError as erro:
        return DesfechoSubstituicao(
            substituicao=None,
            recusa=traduzir_recusa_substituicao(de_validation_error(erro)),
        )
```

**`apps/unidades/context.py`** — a página da unidade identifica o afastamento do titular quando a unidade está sem direção.
```python
def contexto_unidade(unidade: Unidade) -> dict[str, Any]:
    titular = unidade.titular
    substituicao = substituicao_vigente(titular) if titular else None
    substituto = substituicao.substituto if substituicao else None
    direcao = avaliar_direcao(estado_da_direcao(titular, substituto))
    titular_impedimento = (
        titular.impedimentos.filter(q_vigente_em(timezone.localdate())).first()
        if titular and direcao == "sem_direcao"
        else None
    )
    return (
        contexto_fundo_admin()
        | _catalogos_de_unidade()
        | contexto_organograma(unidade)
        | {
            "unidade": unidade,
            "titular": titular,
            "titular_impedimento": titular_impedimento,
            "substituto": substituto,
            "direcao": direcao,
            "alarme_sem_titular": alarme_sem_titular(unidade),
            "alarme_sem_direcao": alarme_sem_direcao(unidade, titular) if titular else "",
            "candidatos": candidatos_a_titular(unidade),
            "cargo_minimo": rotulo_do_minimo(unidade.tipo),
            "total_lotados": unidade.perfis.count(),
        }
    )
```

**`apps/unidades/views.py`** — a permissão da ação declarada desce para o template da unidade.
```python
def pagina_unidade(request: HttpRequest, pk: int) -> HttpResponse:
    unidade = get_object_or_404(Unidade.objects.select_related("tipo", "pai"), pk=pk)
    return render(
        request,
        TEMPLATE_PAGINA_UNIDADE,
        contexto_unidade(unidade)
        | {
            "pode_editar": pode_executar(request.user, ACAO_EDITAR_UNIDADE, unidade.pk),
            "pode_designar_substituto": pode_executar(
                request.user, ACAO_DESIGNAR_SUBSTITUTO, unidade.pk
            ),
        },
    )
```

**`apps/user_admin/views.py`** — as três rotas de escrita, cada uma com sua operação. `_secao_atualizada` inclui o contexto da unidade para atualizar tanto a página do servidor quanto a da unidade via swap OOB.
```python
@acao_protegida(ACAO_DESIGNAR_SUBSTITUTO)
@require_POST
def gravar_designacao(request: HttpRequest, servidor: int, impedimento: int) -> HttpResponse:
    afastamento = _impedimento_do_servidor(servidor, impedimento)
    leitura = ler_nova_substituicao(request.POST.dict())
    alcance = alcance_do_perfil(_autor(request))
    if leitura.dto is None:
        return _designacao_recusada(request, afastamento, leitura.recusa or RecusaDeFormulario())
    desfecho = designar_substituto(afastamento, leitura.dto, alcance)
    if desfecho.substituicao is None:
        return _designacao_recusada(request, afastamento, desfecho.recusa)
    registrar_ato(
        request,
        operacao="designar",
        alvo_tipo="servidor",
        # O RF do SUBSTITUÍDO: é a cadeira dele que o ato cobre, e é a unidade dele que autorizou.
        alvo_identificador=afastamento.perfil.rf,
    )
    return _secao_atualizada(request, afastamento.perfil)


def _secao_atualizada(request: HttpRequest, perfil: Perfil) -> HttpResponse:
    contexto = contexto_secao_exercicio(
        perfil,
        _pode_registrar_impedimento(request, perfil),
        pode_designar_substituto=_pode_designar_substituto(request, perfil),
    )
    if perfil.unidade_id:
        contexto |= contexto_unidade(perfil.unidade) | {
            "pode_editar": pode_executar(request.user, ACAO_EDITAR_UNIDADE, perfil.unidade_id),
            "pode_designar_substituto": _pode_designar_substituto(request, perfil),
        }
    return render(
        request,
        TEMPLATE_IMPEDIMENTO_CONCLUIDO,
        contexto,
    )
```

**`templates/unidades/partials/_secao_direcao.html`** — o cartão de substituição ganha o botão quando a unidade está sem direção.
```django
    <div class="stat {% if not substituto %}stat-vaga{% endif %} card-well">
      <div class="stat-figure{% if not substituto %} text-error/70!{% endif %}">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><use href="#glifo-substituto"/></svg>
      </div>
      <div class="stat-title">Substituto</div>
      {% if substituto %}
        <div class="stat-value">
          <div class="linha-pessoa">
            {% include "user_admin/partials/_imagem_perfil.html" with perfil=substituto imagem=substituto_imagem cor_unidade_hex=substituto_cor_unidade_hex tamanho="w-11 h-11" %}
            <div class="min-w-0 flex-1">
              <p class="linha-pessoa-nome">{{ substituto.nome }} {{ substituto.sobrenome }}</p>
              <p class="linha-pessoa-meta">RF {{ substituto.rf }}{% if substituto.cargo_comissao %} · {{ substituto.cargo_comissao.padrao }} · {{ substituto.cargo_comissao.nome }}{% endif %}</p>
            </div>
            <a href="{% url 'user_admin:pagina_perfil' substituto.pk %}" class="btn btn-ghost btn-glass btn-xs btn-circle shrink-0" title="Abrir a página de {{ substituto.nome }} {{ substituto.sobrenome }}">
              <span class="etched icon-etched">↗</span>
            </a>
          </div>
        </div>
      {% elif titular %}
        <div class="stat-value text-base-content/40!">—</div>
        <div class="stat-desc">Não há substituição vigente.</div>
        {% if direcao == "sem_direcao" and titular_impedimento and pode_designar_substituto %}
          <div class="pt-2">
            <button type="button"
                    hx-get="{% url 'user_admin:modal_designar' titular.pk titular_impedimento.pk %}"
                    hx-target="#poco-modal"
                    hx-swap="innerHTML settle:150ms"
                    class="btn btn-onsen btn-sm gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><use href="#glifo-substituto"/></svg>
              Designar substituto
            </button>
          </div>
        {% endif %}
      {% else %}
        <div class="stat-value">—</div>
        <div class="stat-desc">Sem titular não há quem substituir: substitui-se uma pessoa, não uma vaga.</div>
      {% endif %}
    </div>
```

**`templates/user_admin/partials/_impedimento_concluido.html`** — o swap OOB fecha o modal e atualiza tanto o painel da unidade quanto a seção de exercício.
```django
<div id="secao-exercicio" hx-swap-oob="outerHTML">
  {% include "user_admin/partials/_secao_exercicio.html" %}
</div>
{% if unidade %}
  <div id="painel-unidade" hx-swap-oob="outerHTML">
    {% include "unidades/partials/_identidade_unidade.html" %}
    {% include "unidades/partials/_secao_resumo_unidade.html" %}
    {% include "unidades/partials/_secao_direcao.html" %}
    {% include "unidades/partials/_secao_hierarquia.html" %}
  </div>
{% endif %}
```

## 7 · Caveats
Designar, trocar e encerrar são **uma competência só**, com três operações, e não três ações
inscritas. Separá-las permitiria delegar a designação sem o encerramento, deixando alguém
respondendo por um cargo sem que quem o pôs lá possa tirá-lo. O custo é que o histórico só as
distingue pela operação gravada, e uma futura política que queira conceder só uma delas terá de
quebrar a ação em três.

O substituto precisa estar no alcance de quem assina, e isso **fecha o caminho mais comum de
cobertura**: quem dirige uma unidade subordinada não pode mais chamar alguém da unidade superior
para cobrir seu servidor. A conferência é o que impede entregar a competência do cargo coberto a
alguém de fora do próprio ramo. O custo é que, nesses casos, a designação sobe um nível — precisa
ser praticada por quem dirige a unidade que contém as duas pontas.

Essa mesma conferência é **recusa de formulário, e não negativa registrada**. O decorator confere
alcance sobre os parâmetros que o contrato declara, e o substituto viaja no corpo do formulário —
declará-lo como alvo obrigaria o encerramento, que não tem substituto, a mandar um. O custo é que a
tentativa de designar alguém de fora do ramo não deixa linha no histórico, só a tela de recusa.

O impedimento e a substituição descem no caminho **abaixo** do servidor, e o par pode ser forjado. O
que o contém é o **escopo da consulta** — `perfil_id=servidor` e `impedimento__perfil_id=servidor` —,
que devolve 404 para o par que não existe junto, e não uma segunda barreira. O custo é uma
invariante que vive na consulta de cada view, e que uma view nova pode esquecer.

Os atos de substituição saem de `exercicio.py` para módulo próprio, e cada um passa a ter **uma
porta pública** — a que confere o alcance e devolve desfecho —, com a escrita que levanta privada do
módulo. A escrita precisa continuar levantando porque é o levantar que aborta a transação da troca e
desfaz a véspera já gravada; privada, ela não é caminho para ninguém pular a conferência. O custo é
que `designar_substituto` e `trocar_substituto` mudam de assinatura e de retorno, e os testes que as
usam como construtor de cenário passam a passar o alcance e a ler `desfecho.substituicao`.

A ação mora em `apps/user_admin`, e não em app próprio como manda o §3.5. A exceção é a mesma já
declarada para cadastrar, editar, tornar administrador e registrar impedimento: administrar o quadro
de servidores não é processo da DIMAP, e o ato escreve models deste app. O custo é um app que acumula
cinco ações em vez de as distribuir, e ele já estava pago.

O modal da rota direta oferece **só designar**: trocar e encerrar incidem sobre uma substituição
específica da agenda, e escolhê-la ali exigiria um quarto select encadeado. O custo é um caminho
direto assimétrico em relação ao do impedimento, que cobre as duas faces do seu ato.

A resposta da gravação inclui os swaps OOB de `#secao-exercicio` e `#painel-unidade` no mesmo partial.
A razão é permitir que a escrita atenda transparentemente a página do servidor e a da unidade sem
duplicar rotas de submissão. O custo é montar o contexto da unidade sempre que o servidor possuir
lotação, mesmo quando a requisição parte da tela de perfil.

## 8 · Testes (TDD)

**Comportamento do ato**
- `test_designar_grava_e_devolve_a_secao` — o POST grava a cobertura, e a resposta traz a agenda do
  cartão com ela e o poço do modal vazio. *(marker `banco`)*
- `test_designacao_invalida_volta_como_recusa` — período que não cabe no afastamento volta como o
  próprio modal, com a frase em português, e nada é gravado. *(marker `banco`)*
- `test_trocar_encerra_a_anterior_na_vespera` — o POST de troca encerra a anterior na véspera do dia
  em que a nova assume, grava a nova, e a que saiu continua na lista. *(marker `banco`)*
- `test_encerrar_registra_ou_apaga` — cobertura em curso termina hoje e continua na lista; cobertura
  que não começou é apagada. *(marker `banco`)*
- `test_substituto_fora_do_alcance_volta_como_recusa` — id de servidor de outro ramo não grava e
  volta com a frase e o realce no controle `substituto`. *(marker `banco`)*
- `test_candidatos_recortados_ao_alcance` — o modal de designar só lista candidatos de unidades do
  alcance de quem o abre, nas duas listas. *(marker `banco`)*
- `test_secao_esconde_os_gestos_de_quem_nao_exerce` — o GET da página do servidor traz designar,
  trocar e encerrar para quem dirige a unidade dele e **não** os traz para servidor comum.
  *(marker `banco`)*
- `test_pagina_unidade_sem_direcao_oferece_designar_a_quem_exerce` — a página da unidade sem direção
  traz o botão "Designar substituto" para quem a dirige e esconde o botão para servidor comum.
  *(marker `banco`)*
- `test_face_direta_reflete_o_estado_do_escolhido` — as quatro faces: sem cargo em comissão, sem
  impedimento em aberto, afastamento já coberto e o formulário da designação. *(marker `banco`)*
- `test_modal_direto_recorta_unidades_ao_alcance` — o select do modal direto lista só as unidades do
  ramo de quem o abre. *(marker `banco`)*

**Segurança da ação** (skill `acao-administrativa`; fora do teto)
- `test_anonimo_vai_ao_login_sem_registrar` — POST anônimo redireciona e não deixa linha.
  *(marker `banco`)*
- `test_sem_competencia_recebe_403_registrado` — servidor comum recebe 403 e a tentativa fica
  registrada. *(marker `banco`)*
- `test_titular_designa_sem_concessao_gravada` — quem dirige a unidade do substituído pratica o ato
  sem atribuição nem concessão, inclusive numa unidade subordinada. *(marker `banco`)*
- `test_alvo_de_outro_ramo_e_recusado` — titular de um ramo recebe 403 registrado ao designar para
  servidor de outro, com id válido no caminho, e nada é gravado. *(marker `banco`)*
- `test_direcao_em_outra_unidade_nao_alcanca` — quem dirige unidade irmã não designa para servidor da
  primeira. *(marker `banco`)*
- `test_substituicao_de_outro_servidor_da_404` — par forjado (servidor do meu alcance + substituição
  de outro) é 404, e nada é gravado. *(marker `banco`)*
- `test_impedido_recebe_403_e_exonerado_302` — titular com impedimento vigente recebe 403 ao praticar
  o ato; titular exonerado (`is_active=False`) chega como anônimo e recebe 302 para o login, sem
  linha de negativa. *(marker `banco`)*
- `test_substituto_designa_durante_a_cobertura` — quem cobre o titular impedido responde pela direção
  e pratica o ato; o registro grava o cargo e a unidade dele no momento. *(marker `banco`)*
- `test_ato_grava_quem_cargo_unidade_operacao_e_alvo` — a execução autorizada registra o autor com
  cargo e unidade do momento, a operação e o RF do substituído; mudar a lotação depois não altera a
  linha. *(marker `banco`)*
- `test_designar_trocar_e_encerrar_sao_distinguiveis_no_historico` — as três operações gravam valores
  diferentes sob a mesma ação. *(marker `banco`)*
- `test_leitura_autorizada_nao_vira_linha` — os GET dos três modais, das opções e da face não
  registram nada; o mesmo GET negado, sim. *(marker `banco`)*
- `test_escrita_so_por_post` — GET nas três rotas de gravação é recusado e nada muda.
  *(marker `banco`)*
