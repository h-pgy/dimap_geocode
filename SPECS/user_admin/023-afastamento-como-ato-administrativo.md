---
spec: user_admin/023
versao: v1
atualizado_em: 2026-08-24
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC user_admin/023 — Afastar servidor do exercício

## 1 · User story
Quem dirige uma unidade da DIMAP registra o impedimento que tira um servidor dela do exercício — e o
devolve à cadeira antes do prazo —, na seção de exercício da página do servidor ou por um modal de
acesso direto, para que o afastamento passe a ser ato assinado e rastreável em vez de tela sem
destino.

## 2 · Condições de pronto
- [ ] **Afastar servidor do exercício** é ação inscrita no catálogo, **estrutural** e com alcance pela
      **lotação do servidor-alvo, lida no banco**: quem dirige a unidade do servidor — ou uma acima
      dela — pratica o ato **sem concessão gravada**; quem não dirige e não recebeu delegação recebe
      **403 registrado**.
- [ ] **Registrar impedimento grava**: o servidor sai do exercício na data de início declarada, e o
      cartão do afastamento aparece na seção sem recarregar a página. Servidor de outro ramo é
      recusado com **403 registrado**, com id válido no caminho da rota.
- [ ] **Voltar ao exercício grava pela mesma competência**: encerra os afastamentos que valem hoje e
      acerta as substituições em curso, na mesma transação, e a seção volta atualizada.
- [ ] Os dois botões da seção de exercício **só são renderizados** para quem exerce a ação sobre a
      unidade daquele servidor — e o mesmo vale para os modais, que nascem de rota protegida.
- [ ] **Fim antes do início volta como recusa em português**, com o controle `data_fim` em realce, no
      próprio modal, e **nada é gravado**.
- [ ] O **modal da rota direta** escolhe a unidade — recortada ao alcance de quem abre — e, dentro
      dela, o servidor: trocar a unidade recarrega a lista sem recarregar a tela, e a face do modal
      **reflete o estado do escolhido** — em exercício, o formulário do impedimento; afastado, a
      confirmação do retorno. A ação é **item do `MENU_ADMINISTRADOR`**.
- [ ] Os dois atos são **registrados** (SPEC [autorizacao/004](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md)),
      **distinguíveis pela operação** (`afastar` e `retornar`) e com o **RF** do servidor como alvo.
- [ ] O design foi aprovado no **mock**, e peça nova foi portada para `static/src/tema-dimap.dev.css`
      e renderizada no styleguide antes de qualquer template da aplicação usá-la. **Nenhuma peça
      nova**: o modal direto compõe `.select-onsen`, `.tarja-vinculo` e os campos já existentes, e o
      único artefato novo é o **par de ícones** da ação, composto do calendário de `#glifo-impedimento`.

## 3 · Domínio
Nenhum model novo e nenhuma coluna nova: `Impedimento`, `Substituicao` e o exercício derivado já são
domínio gravado pela SPEC [015](015-exercicio-e-substituicao.md), e os atos `registrar_impedimento` e
`retornar_ao_exercicio` já existem em `apps/user_admin/exercicio.py`. O que esta SPEC modela é a
**competência** que autoriza esses atos e o **alcance** que os limita.

O alcance é a peça que falta: as ações de hoje recebem a unidade-alvo do formulário
(`UnidadesSubordinadas`) ou a leem da lotação **e** do destino de uma transferência
(`LotacaoAtualEDestino`). Aqui o alvo é uma pessoa e não há destino — a unidade a conferir é a
lotação dela, e só ela.

**`services/domain/autorizacao/contratos.py`**
```python
class LotacaoDoServidor(TipoAlcance):
    """O alcance de quem dirige, com um alvo só: a unidade em que o servidor-alvo está lotado, lida
    no banco a partir do id que vem no caminho da rota. O ato incide sobre a pessoa; a unidade é
    consequência dela, e nunca chega pelo corpo da requisição."""

    parametros_alvo: tuple[str, ...] = ("servidor",)
```

**`apps/user_admin/schemas.py`**
```python
class NovoImpedimento(BaseModel):
    """ALTERADO nesta SPEC: ganha o `frozen` dos demais DTOs de formulário e a conferência do
    período, que antes só existia como `CheckConstraint`."""

    model_config = ConfigDict(frozen=True)

    tipo: int
    data_inicio: date
    data_fim: DataOpcional = None

    @model_validator(mode="after")
    def _fim_nao_antecede_inicio(self) -> "NovoImpedimento":
        ...
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`registrar_impedimento`, `retornar_ao_exercicio`, `impedimentos_em_aberto`](015-exercicio-e-substituicao.md) —
  os dois atos e a leitura da seção; nada muda neles, só passam a ter quem os chame.
- [`Acao`, `estrutural`, `instanciar_acao`](../autorizacao/001-catalogo-de-acoes-em-codigo.md) —
  "quem exerce esta ação?"; a resposta é a mesma de cadastrar e editar servidor: quem responde pela
  direção da unidade, sem atribuição nem concessão.
- [`acao_protegida`, `conferir_alvo`, `registrar_ato`, `pode_executar`](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md) —
  a barreira, a conferência do alvo e o rastro; `conferir_alvo` ganha o ramo do alcance novo.
- [`AvaliadorCompetencia` e `em_exercicio`](../autorizacao/003-avaliador-e-backend-de-autorizacao.md) —
  "quem está fora do exercício exerce alguma competência?"; não, e é isso que impede o afastado de
  assinar o próprio retorno.
- [a delegação da competência estrutural](../autorizacao/009-delegacao-de-competencia-estrutural.md) —
  "como o titular passa esta caneta adiante?"; nada a escrever aqui: a ação nasce estrutural e a
  delegação alcança toda estrutural pelo mesmo caminho.
- [`ContratoMenu`, `ItemDeMenu`, `MENU_ADMINISTRADOR`](../autorizacao/005-contrato-de-menu-e-router.md) —
  "onde esta ação se oferece?"; é o menu que a pinça.
- [`Formulario`, `LeitorDeFormulario`, `TradutorDeRecusa`](../formularios/001-erros-de-formulario.md) —
  "como esta recusa se diz, e qual controle ela realça?"; o afastamento ganha catálogo próprio, com
  três controles.
- [`.select-onsen`](011-design-select-de-vidro.md) e
  [o poço do modal e o swap fora de banda](../criacao_usuarios/005-editar-servidor.md) — os selects do
  modal direto e a coreografia de abrir por rota, recusar no lugar e fechar esvaziando o poço.

**Mock:** [023-mock-afastamento.html](023-mock-afastamento.html) — leia a skill `mock`.

## 4 · Fora de escopo
- **Designar, trocar e encerrar substituição** como ato administrativo: os três diálogos continuam
  sem destino — SPEC seguinte do épico.
- **Exonerar servidor** (`is_active`), que é a outra causa de sair do exercício — sem dono ainda.
- **Encerrar um afastamento específico**: o retorno encerra todos os que valem hoje, e não há caminho
  para escolher um — sem dono ainda.
- **Anexar documento comprobatório** ao impedimento — sem dono ainda.
- **Avisar o servidor afastado e o substituto** de que o ato foi praticado — sem dono ainda.
- **Renderizar o `MENU_ADMINISTRADOR`** em alguma tela: o item é inscrito, mas nenhuma tela desenha o
  menu ainda — sem dono ainda (herdado da SPEC [022](022-tornar-administrador.md)).

## 5 · Peças de referência a compor
- `@apps/user_admin/exercicio.py` → `registrar_impedimento`, `retornar_ao_exercicio`,
  `impedimentos_em_aberto`: os atos e a leitura, prontos e em transação.
- `@apps/competencias/utils.py` → `instanciar_acao`; `@apps/competencias/registro.py` →
  `_construir_registro`: onde a ação nova se inscreve.
- `@apps/competencias/protecao.py` → `acao_protegida`, `registrar_ato`, `pode_executar`,
  `_lotacao_de`: a barreira, o rastro e a leitura da lotação no banco, que o alcance novo reusa.
- `@apps/competencias/menus_declarados.py` → `MENU_ADMINISTRADOR`: o menu que pinça a ação.
- `@apps/user_admin/formularios.py` → `FORMULARIO_SERVIDOR`, `ler_novo_servidor`, `traduzir_recusa`:
  o molde do catálogo de recusa e do leitor.
- `@apps/user_admin/context.py` → `contexto_exercicio`, `contexto_opcoes_administrador`,
  `_catalogos_de_lotacao`: a seção inteira e a lista de servidores de uma unidade.
- `@apps/unidades/context.py` → `catalogo_de_unidades`: o select de unidades recortado por ids.
- `@templates/user_admin/partials/_modal_impedimento.html`, `_modal_retorno.html`,
  `_secao_exercicio.html`, `_modais_exercicio.html`: os diálogos e a seção que ganham destino.
- `@templates/user_admin/partials/_edicao_concluida.html` e `@templates/user_admin/perfil.html` →
  `#poco-modal`: o molde de fechar o modal esvaziando o poço e atualizar a página fora de banda.
- `@templates/user_admin/partials/_modal_administrador.html` e `_opcoes_servidor.html`: o molde do
  modal de rota direta com os dois selects encadeados.
- `@templates/user_admin/partials/_glifos_servidor.html` → `#glifo-impedimento`, `#glifo-retorno`: de
  onde sai o desenho do par de ícones.
- Skills: `acao-administrativa`, `erros-de-formulario`, `componentes-frontend`, `daisyui`, `htmx`,
  `mock`, `escrever-testes`, `test-django-views`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`apps/user_admin/acoes_declaradas.py`** — a ação nova, ao lado das três que já moram aqui.
```python
ACAO_AFASTAR_SERVIDOR = instanciar_acao(
    slug="user_admin.afastar_servidor",
    nome="Afastar servidor do exercício",
    nome_curto="Afastamento",
    tooltip="Registra o impedimento que tira um servidor do exercício — e o devolve antes do prazo.",
    # Precisa reverter sem argumento (`competencias.E004`): é a rota do modal direto, e não as de
    # gravação, que recebem o servidor no caminho.
    url_name="user_admin:modal_afastamento",
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Titular da área a exerce por dirigir, sem concessão gravada — e é justamente por ser
    # estrutural que ela é delegável (SPEC autorizacao/009).
    estrutural=True,
    # Um alvo só, e ele é uma PESSOA: a unidade sai da lotação dela, lida no banco.
    alcance=LotacaoDoServidor(),
)
```

**`apps/competencias/protecao.py`** — o ramo novo do despacho por alcance. O `else` que estoura já
existe e é o ponto de extensão; a regra de pertencimento continua escrita uma vez só, em
`conferir_alvo`.
```python
def _unidades_alvo(alcance: TipoAlcance, valores: Mapping[str, int]) -> tuple[int, ...]:
    if isinstance(alcance, UnidadesSubordinadas):
        ...
    if isinstance(alcance, LotacaoDoServidor):
        # A MESMA leitura de `LotacaoAtualEDestino`, sem destino: o ato incide sobre a pessoa, e
        # aceitar a unidade dela do cliente abriria a ação inteira — bastaria mandar a própria.
        return (_lotacao_de(valores["servidor"]),)
    if isinstance(alcance, LotacaoAtualEDestino):
        ...
    raise NotImplementedError(f"alcance sem conferência: {type(alcance).__name__}")
```

**`apps/user_admin/schemas.py`** — a conferência do período sobe do banco para o DTO, porque é ela
que precisa apontar um controle da tela.
```python
ERRO_FIM_ANTES_DO_INICIO = "Fim: não pode ser anterior ao início do afastamento."


class NovoImpedimento(BaseModel):
    ...

    @model_validator(mode="after")
    def _fim_nao_antecede_inicio(self) -> "NovoImpedimento":
        # `data_fim` e não `__all__`: erro sem controle não realça campo nenhum, e quem preencheu
        # fica sem saber qual das duas datas consertar. O `CheckConstraint` do model continua de
        # pé — este validador é a frase, não a garantia.
        if self.data_fim is not None and self.data_fim < self.data_inicio:
            raise PydanticCustomError("fim_antes_do_inicio", ERRO_FIM_ANTES_DO_INICIO)
        return self
```

**`apps/user_admin/formularios.py`** — o catálogo do afastamento, irmão do do servidor.
```python
FORMULARIO_AFASTAMENTO = Formulario(
    campos=(
        CampoDeFormulario(controle="tipo", rotulo="Tipo"),
        CampoDeFormulario(controle="data_inicio", rotulo="Início"),
        CampoDeFormulario(
            controle="data_fim",
            rotulo="Fim",
            # A frase já vem escrita da fonte; o catálogo existe para o controle ser reconhecido e
            # o realce cair no campo certo (mesmo desenho do controle `administrador`).
            regras={"fim_antes_do_inicio": RegraDeErro(mensagem=ERRO_FIM_ANTES_DO_INICIO)},
        ),
    ),
)

ler_novo_impedimento = LeitorDeFormulario(NovoImpedimento, FORMULARIO_AFASTAMENTO)
```

**`apps/user_admin/views.py`** — as duas rotas de escrita, cada uma com sua operação. O `servidor`
vem do caminho da rota, que é o único id que o cliente não forja, e é o mesmo que o decorator já
conferiu contra o alcance.
```python
@acao_protegida(ACAO_AFASTAR_SERVIDOR)
@require_POST
def gravar_impedimento(request: HttpRequest, servidor: int) -> HttpResponse:
    # A view lê o formulário e NÃO constrói o DTO na mão: a recusa dele volta como o próprio modal,
    # e é por isso que ela não passa pelo PydanticValidationMiddleware (SPEC formularios/001).
    leitura = ler_novo_impedimento(request.POST.dict())
    perfil = _perfil(servidor)
    if leitura.dto is None:
        return render(
            request,
            TEMPLATE_MODAL_IMPEDIMENTO,
            contexto_impedimento_recusado(perfil, request.POST.dict(), leitura.recusa),
            status=422,
        )
    registrar_impedimento(perfil, leitura.dto)
    registrar_ato(
        request,
        operacao="afastar",
        alvo_tipo="servidor",
        alvo_identificador=perfil.rf,
    )
    # O poço volta vazio — é assim que o modal fecha — e a seção se atualiza pelo swap fora de
    # banda que o partial carrega, no molde de `_edicao_concluida.html`.
    return render(request, TEMPLATE_AFASTAMENTO_CONCLUIDO, contexto_exercicio(perfil))


@acao_protegida(ACAO_AFASTAR_SERVIDOR)
@require_POST
def gravar_retorno(request: HttpRequest, servidor: int) -> HttpResponse:
    perfil = _perfil(servidor)
    retornar_ao_exercicio(perfil)
    registrar_ato(
        request,
        # Duas operações, uma ação: afastar e devolver são as duas pontas do mesmo fato, e é a
        # operação que as separa no histórico.
        operacao="retornar",
        alvo_tipo="servidor",
        alvo_identificador=perfil.rf,
    )
    return render(request, TEMPLATE_AFASTAMENTO_CONCLUIDO, contexto_exercicio(perfil))
```

**`apps/user_admin/views.py`** — o modal direto e a face que reflete o estado de quem foi escolhido.
```python
@acao_protegida(ACAO_AFASTAR_SERVIDOR)
def modal_afastamento(request: HttpRequest) -> HttpResponse:
    # Oferecer unidade que o decorator vai recusar no POST é convidar ao 403, que o HTMX não troca
    # na tela: o select sai do MESMO alcance que a barreira confere (molde de `criar_perfil`).
    return render(
        request,
        TEMPLATE_MODAL_AFASTAMENTO,
        catalogo_de_unidades(alcance_do_perfil(_autor(request))),
    )


@acao_protegida(ACAO_AFASTAR_SERVIDOR)
def face_afastamento(request: HttpRequest) -> HttpResponse:
    """A segunda metade do gesto de escolher: qual das duas caras o modal mostra é o estado gravado
    do servidor, não uma escolha de quem abriu — quem está afastado se devolve, quem não está se
    afasta. Leitura protegida pela mesma ação e sem registro: é navegação dentro da tela do ato."""
    servidor = request.GET.get("servidor", "")
    if not servidor.isdigit():
        return HttpResponse("")
    # O `servidor` da query string passou pelo `conferir_alvo` do decorator como qualquer outro:
    # escolher alguém de outro ramo neste select é 403, não uma tela que abre e falha no POST.
    perfil = _perfil(int(servidor))
    template = TEMPLATE_AVISO_RETORNO if perfil.esta_impedido else TEMPLATE_FORM_IMPEDIMENTO
    return render(request, template, contexto_exercicio(perfil) | {"perfil": perfil})
```

**`apps/user_admin/urls.py`** — cinco rotas: as duas de escrita, a do modal direto e as duas leituras
que ele encadeia.
```python
    path("servidores/<int:servidor>/impedimento/", views.gravar_impedimento, name="gravar_impedimento"),
    path("servidores/<int:servidor>/retorno/", views.gravar_retorno, name="gravar_retorno"),
    path("servidores/afastamento/", views.modal_afastamento, name="modal_afastamento"),
    # Mesma lista de servidores por unidade do modal de plenos poderes, servida por rota própria:
    # o partial e o contexto se reusam, a competência que protege a rota é que muda.
    path("servidores/afastamento/opcoes/", views.opcoes_afastamento, name="opcoes_afastamento"),
    path("servidores/afastamento/face/", views.face_afastamento, name="face_afastamento"),
```

**`apps/user_admin/views.py`** — e a página do servidor resolve, uma vez, se os botões existem.
```python
def pagina_perfil(request: HttpRequest, pk: int) -> HttpResponse:
    perfil = _perfil(pk)
    return render(
        request,
        TEMPLATE_PAGINA_PERFIL,
        contexto_pagina_perfil(perfil)
        | {
            "pode_editar": pode_executar(request.user, ACAO_EDITAR_SERVIDOR, perfil.unidade_id),
            # Esconder o botão é UX; a barreira é o `acao_protegida` das rotas. O `pode_executar`
            # responde às duas conferências de uma vez — competência e alcance —, e por isso recebe
            # a unidade do servidor da página.
            "pode_afastar": pode_executar(request.user, ACAO_AFASTAR_SERVIDOR, perfil.unidade_id),
        },
    )
```

**`templates/user_admin/partials/_secao_exercicio.html`** — os dois botões passam a abrir rota, e não
um checkbox: é a rota protegida que monta o modal, e ela não monta para quem não exerce.
```django
{% if pode_afastar %}
  <button type="button"
          hx-get="{% url 'user_admin:modal_impedimento' perfil.pk %}"
          hx-target="#poco-modal"
          hx-swap="innerHTML settle:150ms"
          class="btn btn-glass btn-sm gap-2">…</button>
  {% if exercicio.afastado %}
    <button type="button" hx-get="{% url 'user_admin:modal_retorno' perfil.pk %}" …>…</button>
  {% endif %}
{% endif %}
```

**`templates/user_admin/partials/_afastamento_concluido.html`** — o poço esvazia e a seção volta no
lugar dela, fora de banda.
```django
{# Vazio de propósito: o poço do modal recebe isto, e é assim que o modal fecha. #}
<div id="secao-exercicio" hx-swap-oob="outerHTML">
  {% include "user_admin/partials/_secao_exercicio.html" %}
</div>
```

## 7 · Caveats
A ação mora em `apps/user_admin`, e não em app próprio como manda o §3.5. A exceção é a mesma já
declarada para cadastrar, editar e tornar administrador: administrar o quadro de servidores não é
processo da DIMAP, e o ato escreve models deste app. O custo é um app que acumula quatro ações em vez
de as distribuir, e ele já estava pago.

Afastar e devolver ao exercício são **uma competência só**, com duas operações, e não duas ações
inscritas. Separá-las permitiria delegar o afastamento sem o retorno, deixando alguém afastado por
quem não pode devolvê-lo à cadeira. O custo é que o histórico só as distingue pela operação gravada,
e uma futura política que queira conceder só uma das duas terá de quebrar a ação em duas.

O ato de retorno encerra **todos** os afastamentos que valem hoje e grava **uma** linha de execução,
com o servidor como alvo. A alternativa seria registrar um ato por impedimento encerrado, o que
exigiria `protecao.py` gravar em lista. O custo é que o histórico diz *que* a pessoa voltou e não
*quais* afastamentos foram encerrados — isso só se lê nas datas de fim dos próprios impedimentos.

`LotacaoDoServidor` é o terceiro subtipo de `TipoAlcance` e o terceiro ramo do `isinstance` de
`_unidades_alvo`. A regra fica ali, e não num método do subtipo, porque o contrato Pydantic mora em
`services/domain/` e não pode depender de `apps/` (§3.3). O custo é uma função que cresce um ramo por
alcance novo — contido pelo `NotImplementedError` do `else`, que não deixa alcance sem conferência
passar batido.

A recusa de período existe em **dois lugares**: o `model_validator` do `NovoImpedimento`, que escreve
a frase e aponta o controle, e o `CheckConstraint` do model, que é a garantia. Unificar exigiria
traduzir o `ValidationError` do `full_clean` — que chega em `__all__`, sem controle — de volta para um
campo da tela. O custo é a invariante escrita duas vezes, livre para divergir se uma delas mudar.

A seção de exercício fica com **regime misto**: impedimento e retorno abrem por rota protegida e
gravam; designar, trocar e encerrar substituição continuam como diálogos de checkbox sem destino, e
seus botões seguem visíveis para qualquer visitante da página. O custo é uma tela que oferece três
gestos que não acontecem, até a SPEC seguinte do épico — e nenhuma barreira falta, porque não há rota
por trás deles.

## 8 · Testes (TDD)

**Comportamento do ato**
- `test_registrar_impedimento_tira_do_exercicio` — o POST grava o impedimento e o servidor deixa de
  estar em exercício na data de início declarada. *(marker `banco`)*
- `test_retorno_devolve_a_cadeira_hoje` — o POST de retorno encerra os afastamentos vigentes e a
  substituição em curso, na mesma resposta. *(marker `banco`)*
- `test_titular_afasta_sem_concessao_gravada` — quem dirige a unidade do servidor pratica o ato sem
  atribuição nem concessão, inclusive numa unidade subordinada. *(marker `banco`)*
- `test_fim_antes_do_inicio_volta_como_recusa` — a resposta é o modal com a frase em português e o
  realce no controle `data_fim`, e nenhum impedimento é gravado. *(marker `banco`)*
- `test_secao_esconde_os_botoes_de_quem_nao_exerce` — o GET da página do servidor traz os dois botões
  para quem dirige a unidade dele e **não** os traz para servidor comum. *(marker `banco`)*
- `test_gravacao_devolve_secao_atualizada` — a resposta do POST traz a seção com o cartão novo e o
  poço do modal vazio. *(marker `banco`)*
- `test_modal_direto_recorta_unidades_ao_alcance` — o select do modal direto lista só as unidades do
  ramo de quem o abre. *(marker `banco`)*
- `test_face_reflete_o_estado_do_escolhido` — servidor em exercício devolve o formulário do
  impedimento; servidor afastado devolve a confirmação do retorno. *(marker `banco`)*
- `test_opcoes_lista_servidores_da_unidade_escolhida` — a rota de opções devolve só os servidores
  lotados na unidade recebida. *(marker `banco`)*

**Segurança da ação** (skill `acao-administrativa`; fora do teto)
- `test_anonimo_vai_ao_login_sem_registrar` — POST anônimo redireciona e não deixa linha.
  *(marker `banco`)*
- `test_sem_competencia_recebe_403_registrado` — servidor comum recebe 403 e a tentativa fica
  registrada. *(marker `banco`)*
- `test_alvo_de_outro_ramo_e_recusado` — titular de um ramo recebe 403 registrado ao afastar servidor
  de outro, com id válido no caminho, e nada é gravado. *(marker `banco`)*
- `test_unidade_do_alvo_vem_do_banco` — mandar a própria unidade no corpo do POST não abre servidor de
  outro ramo. *(marker `banco`)*
- `test_direcao_em_outra_unidade_nao_alcanca` — quem dirige unidade irmã não afasta servidor da
  primeira. *(marker `banco`)*
- `test_impedido_recebe_403_e_exonerado_302` — titular com impedimento vigente recebe 403 ao praticar
  o ato; titular exonerado (`is_active=False`) chega como anônimo e recebe 302 para o login, sem linha
  de negativa. *(marker `banco`)*
- `test_substituto_afasta_durante_a_cobertura` — quem cobre o titular impedido responde pela direção e
  pratica o ato; o registro grava o cargo e a unidade dele no momento. *(marker `banco`)*
- `test_ato_grava_quem_cargo_unidade_operacao_e_alvo` — a execução autorizada registra o autor com
  cargo e unidade do momento, a operação e o RF do alvo; mudar a lotação depois não altera a linha.
  *(marker `banco`)*
- `test_afastar_e_retornar_sao_distinguiveis_no_historico` — as duas operações gravam valores
  diferentes sob a mesma ação. *(marker `banco`)*
- `test_leitura_autorizada_nao_vira_linha` — os GET do modal, das opções e da face não registram nada;
  o mesmo GET negado, sim. *(marker `banco`)*
- `test_escrita_so_por_post` — GET nas duas rotas de gravação é recusado e nada muda.
  *(marker `banco`)*
