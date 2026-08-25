---
spec: user_admin/024
versao: v1
atualizado_em: 2026-08-24
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC user_admin/024 — Designar substituto como ato administrativo

## 1 · User story
Quem dirige uma unidade da DIMAP designa quem responde pelo cargo de um servidor impedido — e troca
ou encerra essa cobertura —, nos cartões de afastamento da página do servidor ou por um modal de
acesso direto, para que a substituição passe a ser ato assinado e rastreável em vez de diálogo sem
destino.

## 2 · Condições de pronto
- [ ] **Designar substituto** é ação inscrita no catálogo, **estrutural** e com alcance pela
      **lotação do servidor substituído, lida no banco**: quem dirige a unidade dele — ou uma acima
      dela — pratica o ato **sem concessão gravada**; quem não dirige e não recebeu delegação recebe
      **403 registrado**.
- [ ] **Designar grava**: a cobertura entra na agenda e na calha do cartão sem recarregar a página.
      Período que não cabe no afastamento, ou substituto já comprometido, volta como **recusa em
      português no próprio modal**, e nada é gravado.
- [ ] **Trocar grava pela mesma competência**: encerra a cobertura anterior **na véspera** do dia em
      que a nova assume e designa a nova na mesma transação; a que saiu continua na lista com o
      período que exerceu.
- [ ] **Encerrar grava pela mesma competência**: cobertura em curso termina **hoje** e fica
      registrada; cobertura que ainda não começou é **apagada**.
- [ ] O substituto escolhido precisa estar **no alcance de quem assina**: as duas listas do diálogo
      só oferecem quem está, e id de fora volta como **recusa** com realce no controle, sem gravar.
- [ ] Os três botões — designar, trocar e encerrar — **só são renderizados** para quem exerce a ação
      sobre a unidade daquele servidor, e o mesmo vale para os três modais, que nascem de rota
      protegida.
- [ ] O **modal da rota direta** escolhe a unidade — recortada ao alcance de quem abre — e, dentro
      dela, o servidor, e a face **reflete o estado do escolhido**: sem cargo em comissão, sem
      impedimento em aberto, afastamento já coberto, ou o formulário da designação. Com mais de um
      afastamento em aberto, um select escolhe qual, sem recarregar a tela. A ação é **item do
      `MENU_ADMINISTRADOR`**.
- [ ] Os atos são **registrados** (SPEC [autorizacao/004](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md)),
      **distinguíveis pela operação** (`designar`, `trocar` e `encerrar`) e com o **RF do
      substituído** como alvo.
- [ ] O design foi aprovado no **mock**, e peça nova foi portada para `static/src/tema-dimap.dev.css`
      e renderizada no styleguide antes de qualquer template da aplicação usá-la. **Nenhuma peça
      nova**: os três diálogos e o modal direto compõem `.select-onsen`, `.tarja-vinculo`,
      `.campo-realce-erro` e o poço já existentes, e o único artefato novo é o **par de ícones** da
      ação, composto de `#glifo-substituto`.

## 3 · Domínio
Nenhum model novo e nenhuma coluna nova: `Impedimento`, `Substituicao` e os atos
`designar_substituto`, `trocar_substituto` e `encerrar_substituicao` já são domínio gravado pela
SPEC [015](015-exercicio-e-substituicao.md). O que esta SPEC modela é a **competência** que autoriza
esses atos, o **recorte do substituto** ao alcance de quem assina, e o **desfecho** pelo qual a
recusa do ato volta para a tela.

A substituição passa a ter **módulo próprio**, `apps/user_admin/substituicao.py`: os atos, as
leituras da cobertura e a montagem dos DTOs de designação saem de `exercicio.py`, que fica com o
impedimento e o exercício derivado. Cada ato tem **uma porta pública**, que devolve desfecho e nunca
levanta; a escrita que levanta é privada do módulo, e é o levantar dela, dentro da transação, que faz
a troca desfazer a véspera já gravada quando a designação nova não cola. A dependência é de mão
única: `exercicio.py` chama `substituicao.py` para truncar a cobertura no retorno ao exercício, e
nada em `substituicao.py` conhece o impedimento além do model.

O alcance é o mesmo do impedimento: o ato incide sobre uma **pessoa** — o substituído —, e a unidade
a conferir é a lotação dela. Impedimento e substituição não chegam por parâmetro próprio de alcance:
descem no caminho da rota **abaixo** do servidor, e são lidos escopados por ele.

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
- `@apps/user_admin/views.py` → `_secao_atualizada`, `_autor`, `_perfil`; `@templates/user_admin/partials/_impedimento_concluido.html`: a resposta que fecha o modal e devolve a seção.
- `@apps/user_admin/context.py` → `contexto_exercicio`, `_universos_de_candidatos`, `_candidatos`,
  `_opcoes_de_servidor`, `_icone_impedimento`: a seção inteira, os candidatos e o segundo select.
- `@templates/user_admin/partials/_modal_designar.html`, `_modal_encerrar.html`: os diálogos que
  ganham destino.
- `@templates/user_admin/partials/_modal_registrar_impedimento.html`, `_opcoes_servidor.html`,
  `_form_impedimento.html`: o molde do modal de rota direta, dos selects encadeados e da face.
- `@templates/user_admin/partials/_glifos_exercicio.html` → `#glifo-substituto`: de onde sai o
  desenho do par de ícones.
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
    alcance: Collection[int],
) -> DesfechoSubstituicao:
    """ALTERADO nesta SPEC: devolve desfecho em vez de levantar, e recebe o alcance de quem assina.
    Porta única — quem grava uma designação passa por aqui, e por aqui passa a conferência."""
    recusa = recusa_de_substituto_fora_do_alcance(dados.substituto, alcance)
    if recusa is not None:
        return DesfechoSubstituicao(substituicao=None, recusa=recusa)
    return _desfecho(lambda: _gravar_designacao(impedimento, dados))


def trocar_substituto(
    atual: Substituicao,
    dados: TrocaDeSubstituto,
    alcance: Collection[int],
) -> DesfechoSubstituicao:
    """ALTERADO nesta SPEC: mesmo desfecho e mesma conferência."""
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

**`apps/user_admin/views.py`** — as três rotas de escrita, cada uma com sua operação. O `servidor`
vem do caminho e é o que o decorator já conferiu contra o alcance; o impedimento e a substituição
vêm **escopados por ele**, e não confiados.
```python
@acao_protegida(ACAO_DESIGNAR_SUBSTITUTO)
@require_POST
def gravar_designacao(request: HttpRequest, servidor: int, impedimento: int) -> HttpResponse:
    # A view lê o formulário e NÃO constrói o DTO: a recusa dele volta como o próprio modal, e é por
    # isso que ela não passa pelo PydanticValidationMiddleware (SPEC formularios/001).
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


@acao_protegida(ACAO_DESIGNAR_SUBSTITUTO)
@require_POST
def gravar_troca(request: HttpRequest, servidor: int, substituicao: int) -> HttpResponse:
    atual = _substituicao_do_servidor(servidor, substituicao)
    leitura = ler_troca_de_substituto(request.POST.dict())
    ...
    registrar_ato(request, operacao="trocar", alvo_tipo="servidor", alvo_identificador=...)
    return _secao_atualizada(request, atual.impedimento.perfil)


@acao_protegida(ACAO_DESIGNAR_SUBSTITUTO)
@require_POST
def gravar_encerramento(request: HttpRequest, servidor: int, substituicao: int) -> HttpResponse:
    # Sem leitor e sem desfecho: encerrar não tem formulário e não tem como ser recusado — a
    # cobertura em curso termina hoje, a que não começou é apagada.
    atual = _substituicao_do_servidor(servidor, substituicao)
    substituido = atual.impedimento.perfil
    encerrar_substituicao(atual)
    registrar_ato(
        request,
        # Três operações, uma ação: designar, trocar e encerrar são fatos diferentes, e é a operação
        # que os separa no histórico.
        operacao="encerrar",
        alvo_tipo="servidor",
        alvo_identificador=substituido.rf,
    )
    return _secao_atualizada(request, substituido)


def _impedimento_do_servidor(servidor: int, impedimento: int) -> Impedimento:
    # Escopado pelo servidor do caminho: par forjado (um servidor que eu alcanço + um impedimento
    # que não é dele) é 404, e não uma porta para outro ramo.
    return get_object_or_404(
        Impedimento.objects.select_related("perfil", "tipo"),
        pk=impedimento,
        perfil_id=servidor,
    )


def _substituicao_do_servidor(servidor: int, substituicao: int) -> Substituicao:
    return get_object_or_404(
        Substituicao.objects.select_related("impedimento__perfil", "impedimento__tipo", "substituto"),
        pk=substituicao,
        impedimento__perfil_id=servidor,
    )
```

**`apps/user_admin/views.py`** — o modal direto e a face que reflete o estado de quem foi escolhido.
```python
@acao_protegida(ACAO_DESIGNAR_SUBSTITUTO)
def modal_designar_substituto(request: HttpRequest) -> HttpResponse:
    # Oferecer unidade que o decorator vai recusar no POST é convidar ao 403, que o HTMX não troca
    # na tela: o select sai do MESMO alcance que a barreira confere (molde de `criar_perfil`).
    return render(
        request,
        TEMPLATE_MODAL_DESIGNAR_SUBSTITUTO,
        contexto_modal_designar_substituto(alcance_do_perfil(_autor(request))),
    )


@acao_protegida(ACAO_DESIGNAR_SUBSTITUTO)
def face_substituicao(request: HttpRequest) -> HttpResponse:
    """A segunda metade do gesto de escolher, e também a terceira: `servidor` traz a face, e o
    `impedimento` opcional escolhe qual afastamento ela mostra quando há mais de um em aberto — uma
    rota só, e por isso o alcance é conferido pelo `servidor` nas duas passagens.

    O afastamento nunca é confiado: sai da lista de em-aberto do próprio servidor, então id de outro
    ramo simplesmente não está lá."""
    servidor = request.GET.get("servidor", "")
    if not servidor.isdigit():
        return HttpResponse("")
    perfil = _perfil(int(servidor))
    escolhido = request.GET.get("impedimento", "")
    return render(
        request,
        TEMPLATE_FACE_SUBSTITUICAO,
        contexto_face_substituicao(
            perfil,
            int(escolhido) if escolhido.isdigit() else None,
            alcance_do_perfil(_autor(request)),
        ),
    )
```

**`apps/user_admin/urls.py`** — nove rotas: os três modais e as três gravações da página do servidor,
e a tela direta com as duas leituras que ela encadeia.
```python
    # A ação "designar substituto" (SPEC user_admin/024). O impedimento e a substituição descem
    # ABAIXO do servidor no caminho: é o servidor que o alcance confere, e são eles que a consulta
    # escopa por ele.
    path("servidores/<int:servidor>/impedimentos/<int:impedimento>/substituto/modal/", views.modal_designar, name="modal_designar"),
    path("servidores/<int:servidor>/impedimentos/<int:impedimento>/substituto/", views.gravar_designacao, name="gravar_designacao"),
    path("servidores/<int:servidor>/substituicoes/<int:substituicao>/trocar/modal/", views.modal_trocar, name="modal_trocar"),
    path("servidores/<int:servidor>/substituicoes/<int:substituicao>/trocar/", views.gravar_troca, name="gravar_troca"),
    path("servidores/<int:servidor>/substituicoes/<int:substituicao>/encerrar/modal/", views.modal_encerrar, name="modal_encerrar"),
    path("servidores/<int:servidor>/substituicoes/<int:substituicao>/encerrar/", views.gravar_encerramento, name="gravar_encerramento"),
    path("servidores/substituicoes/", views.modal_designar_substituto, name="modal_designar_substituto"),
    # Mesma lista de servidores por unidade dos outros dois modais diretos, servida por rota
    # própria: o partial e o contexto se reusam, a competência que protege a rota é que muda.
    path("servidores/substituicoes/opcoes/", views.opcoes_substituicao, name="opcoes_substituicao"),
    path("servidores/substituicoes/face/", views.face_substituicao, name="face_substituicao"),
```

**`apps/user_admin/context.py`** — os candidatos saem da seção e passam a nascer só no diálogo, já
recortados. A página do servidor deixa de montar o universo inteiro a cada visita, e o recorte fica
onde há quem assina para recortá-lo.
```python
def contexto_exercicio(perfil: Perfil) -> dict[str, Any]:
    """ALTERADO nesta SPEC: sem `candidatos` e sem os ids de checkbox dos modais. Os diálogos agora
    chegam por rota protegida, e é a rota que sabe quem os abriu."""
    ...


def _universos_de_candidatos(
    perfil: Perfil,
    ids_permitidos: Collection[int],
) -> dict[str, list[Perfil]]:
    """ALTERADO nesta SPEC: o universo nasce recortado ao alcance de quem assina. A unidade do
    substituído está sempre nele — foi ela que autorizou o ato."""
    servidores = list(
        Perfil.objects.filter(unidade_id__in=ids_permitidos)
        .exclude(pk=perfil.pk)
        .select_related("unidade", "cargo_comissao")
        .prefetch_related("impedimentos", "substituicoes_exercidas")
        .order_by("nome", "sobrenome")
    )
    ...


def contexto_face_substituicao(
    perfil: Perfil,
    impedimento_id: int | None,
    ids_permitidos: Collection[int],
) -> dict[str, Any]:
    """As quatro faces da rota direta, e é o estado GRAVADO do escolhido que decide qual: sem cargo
    em comissão não há competência a cobrir; sem impedimento em aberto não há o que substituir; sem
    lacuna o afastamento já está coberto; e só então o formulário."""
    abertos = list(impedimentos_em_aberto(perfil))
    escolhido = next((i for i in abertos if i.pk == impedimento_id), None) or (
        abertos[0] if abertos else None
    )
    ...
```

**`templates/user_admin/partials/_linha_substituicao.html`** — os dois gestos da linha passam a abrir
rota, e não um checkbox: é a rota protegida que monta o modal, e ela não monta para quem não exerce.
```django
{% if not item.encerrada and pode_designar_substituto %}
  <div class="flex gap-2 shrink-0">
    <button type="button"
            hx-get="{% url 'user_admin:modal_trocar' perfil.pk item.substituicao.pk %}"
            hx-target="#poco-modal"
            hx-swap="innerHTML settle:150ms"
            class="btn btn-glass btn-xs">Trocar</button>
    <button type="button"
            hx-get="{% url 'user_admin:modal_encerrar' perfil.pk item.substituicao.pk %}"
            hx-target="#poco-modal"
            hx-swap="innerHTML settle:150ms"
            class="btn btn-glass btn-xs">Encerrar</button>
  </div>
{% endif %}
```

**`templates/user_admin/partials/_modal_designar.html`** — o diálogo que já existe ganha destino: o
alvo do submit é o poço, a recusa o remonta aberto e o sucesso o esvazia, que é como o modal fecha.
```django
<form hx-post="{% if troca %}{% url 'user_admin:gravar_troca' perfil.pk troca.substituicao.pk %}{% else %}{% url 'user_admin:gravar_designacao' perfil.pk cartao.impedimento.pk %}{% endif %}"
      hx-target="#poco-modal"
      hx-swap="innerHTML"
      class="flex flex-col gap-6">

  {% include "partials/_tarja_recusa.html" with titulo="A substituição não foi gravada" %}
  ...
  <select name="substituto" class="select select-glass {{ realce.substituto }}" data-select-onsen>
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
que `designar_substituto` e `trocar_substituto` mudam de assinatura e de retorno, e os **dez arquivos
de teste** que as usam como construtor de cenário passam a passar o alcance e a ler
`desfecho.substituicao`.

A ação mora em `apps/user_admin`, e não em app próprio como manda o §3.5. A exceção é a mesma já
declarada para cadastrar, editar, tornar administrador e registrar impedimento: administrar o quadro
de servidores não é processo da DIMAP, e o ato escreve models deste app. O custo é um app que acumula
cinco ações em vez de as distribuir, e ele já estava pago.

O modal da rota direta oferece **só designar**: trocar e encerrar incidem sobre uma substituição
específica da agenda, e escolhê-la ali exigiria um quarto select encadeado. O custo é um caminho
direto assimétrico em relação ao do impedimento, que cobre as duas faces do seu ato.

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
- `test_face_direta_reflete_o_estado_do_escolhido` — as quatro faces: sem cargo em comissão, sem
  impedimento em aberto, afastamento já coberto e o formulário da designação. *(marker `banco`)*
- `test_face_direta_escolhe_entre_afastamentos` — com dois impedimentos em aberto, o `impedimento`
  da query string troca o formulário, e sem ele vem o primeiro. *(marker `banco`)*
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
