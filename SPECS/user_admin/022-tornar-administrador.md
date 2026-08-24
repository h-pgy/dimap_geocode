---
spec: user_admin/022
versao: v5
atualizado_em: 2026-08-24
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: o "Salvar alterações" volta a ser a última coisa do modal de edição, e a página do servidor
    passa a dizer em leitura quem é administrador
  - v3: no modal de edição a marca deixa de ser ato à parte e vira controle do formulário, gravada
    pelo mesmo ato que grava o cadastro — formulário recusado não torna ninguém administrador
  - v4: o termo da interface passa a ser "Administrador do Sistema" no lugar de "plenos poderes", e
    a célula do resumo só aparece para quem é
  - v5: a placa de confirmação sai de dentro do painel de vidro que a prendia, e passa a ser ligada
    ao controle por `:has()` no documento
---

# SPEC user_admin/022 — Tornar administrador

## 1 · User story
Quem administra o sistema torna outro servidor administrador — e revoga —, na tela de cadastro, no
modal de edição do servidor e num modal de acesso direto, para que a caneta de administrador do
sistema seja passada adiante sem shell nem management command.

## 2 · Condições de pronto
- [ ] **Tornar administrador** é ação inscrita no catálogo e **exclusiva do superusuário**: quem não
      é recebe **403 registrado** e não a vê em tela alguma — **nem com a concessão gravada**.
- [ ] **Ação exclusiva do superusuário não é oferecida para atribuir nem para conceder**: ela não
      aparece no catálogo do modal de atribuir competência à unidade, e por isso nunca chega às telas
      de concessão. Quem a esconde é o registro em código, não uma lista de slugs escrita à mão.
- [ ] Concedida, o servidor passa a ter `is_superuser`: alcança o organograma inteiro e exerce toda
      ação, inclusive criar unidade raiz e cadastrar servidor em qualquer unidade. O `/admin` do
      Django **continua fechado** para ele.
- [ ] O botão tem **dois estados**: em repouso, em relevo com a aura; acionado, afundado no poço.
      Ele aparece no **formulário de criar servidor**, no **modal de editar servidor** e no **modal
      da rota direta** — e **em nenhum deles é renderizado** para quem não exerce a ação, embora as
      duas primeiras telas sejam abertas por quem apenas cadastra e edita servidor: o que decide é o
      mesmo `has_perm` da barreira, e não uma segunda regra escrita na tela.
- [ ] **Nas duas telas de formulário a marca é um controle do formulário**, e não um ato à parte: o
      mesmo partial serve às duas, o estado é local ao navegador até salvar, e quem grava é o ato
      que grava o cadastro. **Formulário recusado não concede nem revoga nada** — RF torto ou e-mail
      inválido derrubam a marca junto com o resto. Só no **modal da rota direta** o botão pratica o
      ato sozinho, com `hx-post` próprio e efeito imediato: lá não há formulário a validar.
- [ ] **A ausência da marca no POST nunca revoga**: quem não exerce a ação não recebe o controle na
      tela e por isso não o envia, e ler esse silêncio como "revogar" tiraria a caneta do editado a
      cada edição feita por quem apenas edita servidor. Sem caneta, o que está gravado é o que fica.
- [ ] **A placa de confirmação é da tela, não do painel em que o botão mora**: ela é irmã do
      `.modal` e do formulário, nunca filha deles. Ancestral com `backdrop-filter` — o
      `.glass-panel` do formulário, o `.modal-box` do modal — vira containing block de descendente
      `fixed`, e a placa presa lá dentro nasce ancorada no topo do conteúdo, fora da vista de quem
      rolou até o botão. Quem religa o controle à placa, através dessa distância, é `:has()` no
      documento — não um combinador de irmão, que a obrigaria a morar ao lado do gatilho.
- [ ] **Nada muda sem confirmação explícita** — Ok e Cancelar, com o aviso de que a pessoa terá
      a condição de administrador do sistema. Cancelar devolve o botão ao estado gravado e não
      grava nada. Onde o gesto já
      acontece dentro de um modal, a confirmação **substitui o corpo dele**: não há modal dentro de
      modal.
- [ ] Clicar o botão **afundado revoga**, e a revogação passa pela mesma confirmação — mas
      **ninguém revoga a si mesmo**: a tentativa volta recusada, com o motivo em português na tela,
      e nada é gravado. É essa recusa que mantém o sistema com pelo menos um administrador.
- [ ] O **modal da rota direta** escolhe a unidade e, dentro dela, o servidor: trocar a unidade
      recarrega a lista de servidores sem recarregar a tela, o botão reflete o estado do escolhido e
      o ato incide sobre ele. A ação é **item do `MENU_ADMINISTRADOR`**.
- [ ] No **formulário de criar servidor** não há alvo ainda: o botão armado faz o servidor **nascer
      administrador**, no mesmo POST do cadastro. A concessão **não some do histórico**: a execução
      registrada do cadastro grava a operação `criar_administrador` no lugar de `criar`, e é por ela
      que se acha quem nasceu administrador e quem assinou. Marca enviada por quem não é
      superusuário volta como **recusa na própria tela**, com o controle em realce, e nada é
      gravado — nem o cadastro.
- [ ] Conceder e revogar são **atos registrados** (SPEC [autorizacao/004](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md)),
      **distinguíveis pela operação** e com o **RF** do servidor como alvo. A edição que mexe na
      marca grava a operação `editar_administrador` no lugar de `editar` — o mesmo desenho do
      `criar_administrador` do cadastro.
- [ ] A **página do servidor diz em leitura** quem é administrador: badge com o glifo ao lado do RF
      no cabeçalho e célula **"Administrador do Sistema"** no `.well` do resumo. Essa célula é
      **afirmativa**, ao contrário das duas ao lado: só existe para quem é — não ser administrador é
      o caso comum, e não notícia. No modal de edição o **"Salvar alterações" é a última coisa da
      tela**, abaixo do poço de administrador: gravar é o que se faz por último.
- [ ] O termo da interface é **"Administrador do Sistema"** — rótulo do controle, título da célula e
      texto dos avisos. "Plenos poderes" não aparece em tela alguma.
- [ ] O design foi aprovado no **mock**, e peça nova foi portada para `static/src/tema-dimap.dev.css`
      e renderizada no styleguide antes de qualquer template da aplicação usá-la. São **duas** peças:
      o átomo da **aura** (`.aura-onsen`) e a molécula do **botão de ato grave** (`.botao-aura`), que
      compõe a aura com as duas faces do controle — `.btn-onsen` em repouso, `.card-well` acionado —,
      as duas **intocadas**. A molécula nasce genérica: ela é a peça de **qualquer ato de peso** do
      sistema, e o styleguide a registra fora do contexto desta ação. Fora delas, só o **par de
      ícones**, composto do escudo com a estrela de `#glifo-titular`.

## 3 · Domínio
Nenhum model novo e nenhum campo novo: **ser administrador já é um atributo do `Perfil`** —
`is_superuser`, do `PermissionsMixin`, que a SPEC [020](020-unidade-como-ato-administrativo.md) já
transformou em regime de competência (`exclusiva_superusuario`) e em alcance total do organograma.
O que esta SPEC modela é o **ato** que escreve esse atributo, e a marca que o cadastro carrega.

**`apps/user_admin/schemas.py`**
```python
class MudancaDeAdministrador(BaseModel):
    """O ato sobre um servidor que JÁ existe — o das duas telas de servidor e o do modal direto."""

    model_config = ConfigDict(frozen=True)

    servidor_id: int
    # Explícito, e não alternância lida do estado atual: dois cliques concorrentes sobre o mesmo
    # servidor decidiriam coisas diferentes, e a operação registrada é o que se quer inequívoco.
    tornar: bool
    # O autor resolvido pela orquestração (§3.3), nunca o `request`: é contra ele que a recusa de
    # revogar a si mesmo é escrita.
    autor_id: int


class EdicaoServidor(BaseModel):
    """ALTERADO na v3: a edição passa a carregar a marca, e é isso que amarra a concessão à
    validação do resto do formulário."""

    model_config = ConfigDict(frozen=True)

    servidor_id: int
    rf: RegistroFuncional
    nome: NomeDePessoa
    sobrenome: SobrenomeDePessoa
    email: EmailDeServidor
    unidade_id: int
    cargo_base_id: int
    cargo_comissao_id: CargoOpcional = None
    # Mesmo default e mesmo motivo do `NovoServidor`.
    administrador: bool = False


class NovoServidor(BaseModel):
    """ALTERADO nesta SPEC: o cadastro passa a carregar a marca de administrador."""

    model_config = ConfigDict(frozen=True)

    rf: RegistroFuncional
    nome: NomeDePessoa
    sobrenome: SobrenomeDePessoa
    email: EmailDeServidor
    unidade_id: int
    cargo_base_id: int
    cargo_comissao_id: CargoOpcional = None
    url_acesso: HttpUrl
    # ALTERADO nesta SPEC. Default `False` porque o controle é um botão de dois estados: em repouso
    # ele não manda nada, e ausência é "não". Quem pode armá-lo é conferido no ato, não aqui — o
    # DTO não conhece quem assina.
    administrador: bool = False
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`Acao`, `exclusiva_superusuario` e o avaliador](020-unidade-como-ato-administrativo.md) — "quem
  exerce esta ação?"; a resposta é a mesma de criar unidade raiz, e ela responde de uma vez à
  barreira, ao botão e ao menu, porque os três perguntam pelo mesmo `has_perm`.
- [`acao_protegida` e `registrar_ato`](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md) —
  a rota protegida e o rastro do ato, com a operação que separa conceder de revogar.
- [`ContratoMenu` e `ItemDeMenu`](../autorizacao/005-contrato-de-menu-e-router.md) — "onde esta ação
  se oferece?"; é o menu que a pinça, e o `MENU_ADMINISTRADOR` já existe declarado.
- [`criar_servidor` e `DesfechoCadastro`](../criacao_usuarios/004-criar-servidor.md) — o ato de
  cadastro que passa a gravar a marca e a recusá-la de quem não pode armá-la.
- [`editar_servidor` e o modal do lápis](../criacao_usuarios/005-editar-servidor.md) — a tela em que
  o botão convive com os campos, sem virar mais um deles.
- [`FORMULARIO_SERVIDOR` e `TradutorDeRecusa`](../formularios/001-erros-de-formulario.md) — "como
  esta recusa se diz, e qual controle ela realça?"; o catálogo do servidor ganha mais um controle.
- [`.select-onsen`](011-design-select-de-vidro.md) — os dois campos do modal direto, unidade e
  servidor, no mesmo componente das demais telas.

**Mock:** [022-mock-tornar-administrador.html](022-mock-tornar-administrador.html) — leia a skill `mock`.

## 4 · Fora de escopo
- **Renderizar o `MENU_ADMINISTRADOR`** em alguma tela: o item é inscrito, mas nenhuma tela desenha
  o menu ainda — sem dono ainda.
- **Dizer na listagem de servidores quem é administrador** (coluna, filtro ou marca na linha) — sem
  dono ainda.
- **Abrir o `/admin` do Django** (`is_staff`) a quem for tornado administrador — sem dono ainda.
- **Concessão com prazo**, que expira sozinha, e **dupla assinatura** para conceder — sem dono ainda.
- **Página que lista os administradores em vigor** e o histórico de quem concedeu a quem: o que fica
  é a execução registrada (SPEC [autorizacao/004](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md)) — sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/competencias/utils.py` → `instanciar_acao`; `@apps/competencias/registro.py` →
  `_construir_registro`: onde a ação nova se inscreve, com `exclusiva_superusuario=True`.
- `@apps/competencias/menus_declarados.py` → `MENU_ADMINISTRADOR`: o menu que pinça a ação.
- `@apps/competencias/catalogo.py` → `acoes_oferecidas`: o que o modal de atribuir oferece a uma
  unidade; `@apps/competencias/consulta.py` → `_slugs_exclusivos`: o conjunto que o recorta.
- `@apps/competencias/protecao.py` → `acao_protegida`, `registrar_ato`, `pode_executar`: a barreira,
  o rastro e a resposta de que o botão precisa.
- `@apps/user_admin/cadastro.py` → `criar_servidor`, `DesfechoCadastro`, `_gravar`: o ato de cadastro
  que passa a gravar a marca, e o molde do desfecho que o ato novo repete.
- `@apps/unidades/views.py` → `gravar_unidade` com `raiz_permitida=autor.is_superuser`: o precedente
  de como a orquestração entrega ao ato o que ela já resolveu sobre quem assina.
- `@services/utils/erros_formulario` → `RecusaDeFormulario`, `ErroBruto`, `RegraDeErro`,
  `TomDeRealce`; e `@apps/user_admin/formularios.py` → `FORMULARIO_SERVIDOR`, `traduzir_recusa`.
- `@apps/user_admin/context.py` → `contexto_modal_perfil`, `contexto_cadastro_recusado`,
  `_catalogos_de_lotacao`: os contextos das duas telas em que o botão entra.
- `@templates/user_admin/partials/_modal_editar_perfil.html` e `@templates/user_admin/perfil.html` →
  o poço do modal e a coreografia de abrir por rota, recusar no lugar e fechar esvaziando.
- `@templates/unidades/partials/_modal_definir_titular.html`: o molde do modal curto com select e
  confirmação, que o modal da rota direta repete.
- `@static/src/acoes/unidades/criar_unidade_raiz/icones/`: o molde da pasta cobrada no boot
  (`competencias.E003`); `@templates/unidades/partials/_glifos_unidade.html` → `#glifo-titular`, de
  onde sai a estrela do escudo.
- Skills: `acao-administrativa`, `erros-de-formulario`, `componentes-frontend`, `daisyui`, `htmx`,
  `mock`, `escrever-testes`, `test-django-views`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`apps/user_admin/acoes_declaradas.py`** — a ação nova, ao lado das duas que já moram aqui.
```python
ACAO_TORNAR_ADMINISTRADOR = instanciar_acao(
    slug="user_admin.tornar_administrador",
    nome="Tornar administrador",
    nome_curto="Administrador",
    tooltip="Torna um servidor administrador do sistema — e desfaz.",
    # Precisa reverter sem argumento (`competencias.E004`): é a rota do modal direto, e não a de
    # gravação, que recebe o servidor no caminho.
    url_name="user_admin:modal_administrador",
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Mesmo regime de criar unidade raiz: dirigir unidade não dá esta caneta, e conceder também
    # não. Só quem já a tem a passa adiante.
    estrutural=False,
    exclusiva_superusuario=True,
    # Sem alcance: o ato não incide sobre unidade, e o superusuário alcança o organograma inteiro.
    # Declarar alcance que nunca barra ninguém seria conferência de mentira.
    alcance=None,
)
```

**`apps/user_admin/administrador.py`** — o ato, no molde do `cadastro.py`: recusa em vez de exceção,
porque ela volta na própria tela.
```python
ERRO_AUTO_REVOGACAO = (
    "Você não pode retirar de si mesmo a condição de administrador do sistema: "
    "peça a outro administrador."
)


def mudar_administrador(mudanca: MudancaDeAdministrador) -> DesfechoAdministrador:
    """Uma regra só, e é ela que garante que sempre reste um administrador: quem assina não se
    desfaz da própria caneta. Como só administrador chega aqui, recusar a auto-revogação já implica
    que o conjunto nunca esvazia."""
    if not mudanca.tornar and mudanca.servidor_id == mudanca.autor_id:
        return DesfechoAdministrador(
            perfil=None,
            recusa=traduzir_recusa(
                (ErroBruto(controle="administrador", tipo="auto_revogacao", mensagem=ERRO_AUTO_REVOGACAO),)
            ),
        )
    perfil = get_object_or_404(Perfil, pk=mudanca.servidor_id)
    perfil.is_superuser = mudanca.tornar
    # Campo só, e não `save()` inteiro: o ato escreve a caneta e nada mais do cadastro — e
    # `is_staff` fica de fora de propósito, o /admin do Django não abre por aqui (§4).
    perfil.save(update_fields=["is_superuser"])
    return DesfechoAdministrador(perfil=perfil)
```

**`apps/user_admin/views.py`** — a rota de escrita, apartada da que mostra o modal.
```python
@acao_protegida(ACAO_TORNAR_ADMINISTRADOR)
@require_POST
def gravar_administrador(request: HttpRequest, servidor: int) -> HttpResponse:
    # DTO na fronteira; malformado morre no PydanticValidationMiddleware. `servidor` vem do caminho
    # da rota, e o autor do request — nenhum dos dois do corpo, que o cliente escreve.
    mudanca = MudancaDeAdministrador(
        servidor_id=servidor,
        tornar=request.POST.get("tornar") == "1",
        autor_id=_autor(request).pk,
    )
    desfecho = mudar_administrador(mudanca)
    if desfecho.perfil is None:
        return render(request, TEMPLATE_BOTAO_ADMINISTRADOR, contexto_administrador_recusado(...), status=422)
    # Duas operações, uma ação: é o que torna conceder e revogar distinguíveis no histórico.
    registrar_ato(
        request,
        operacao="tornar" if mudanca.tornar else "revogar",
        alvo_tipo="servidor",
        alvo_identificador=desfecho.perfil.rf,
    )
    return render(request, TEMPLATE_BOTAO_ADMINISTRADOR, contexto_botao_administrador(desfecho.perfil))
```

**`apps/user_admin/cadastro.py`** — no cadastro não há alvo ainda, e a marca vai junto: quem pode
armá-la é resolvido na orquestração e desce como dado, no molde do `raiz_permitida` da SPEC 020.
```python
ERRO_SEM_CANETA = "Só um administrador pode cadastrar outro administrador."


def criar_servidor(
    valores: Mapping[str, Any],
    foto: UploadedFile | None = None,
    administrador_permitido: bool = False,
) -> DesfechoCadastro:
    ...
    if novo.administrador and not administrador_permitido:
        # Recusa, e não 403: o controle existe na tela e a marca veio de um formulário — quem
        # preencheu tem que ver o motivo no lugar em que ele nasceu. Nada é gravado, nem o cadastro.
        return DesfechoCadastro(
            perfil=None,
            recusa=traduzir_recusa(
                (ErroBruto(controle="administrador", tipo="sem_caneta", mensagem=ERRO_SEM_CANETA),)
            ),
        )
    ...


def _gravar(novo: NovoServidor, senha: SecretStr, foto: UploadedFile | None) -> Perfil:
    perfil = Perfil(
        ...
        is_superuser=novo.administrador,
    )
```

**`apps/user_admin/views.py`** — e o cadastro registra a concessão como operação própria, sem
esconder atrás de "criar".
```python
    registrar_ato(
        request,
        # A operação é o que diz o que foi praticado: cadastrar alguém já administrador não é
        # o mesmo ato que cadastrar um servidor comum, e o histórico precisa separá-los.
        operacao="criar_administrador" if desfecho.perfil.is_superuser else "criar",
        alvo_tipo="servidor",
        alvo_identificador=desfecho.perfil.rf,
    )
```

**`apps/user_admin/cadastro.py`** (v3) — a edição escreve a marca no fim, na mesma transação do
resto: é a ordem que faz o formulário recusado não conceder nada.
```python
def editar_servidor(
    valores: Mapping[str, Any],
    autor_id: int,
    foto: UploadedFile | None = None,
    administrador_permitido: bool = False,
) -> DesfechoCadastro:
    ...
    perfil = get_object_or_404(Perfil, pk=edicao.servidor_id)
    if edicao.administrador and not administrador_permitido:
        return DesfechoCadastro(perfil=None, recusa=_recusa_sem_caneta(ERRO_SEM_CANETA_EDICAO))
    # Sem o controle na tela o POST não manda a marca, e ler essa ausência como "revogar" tiraria a
    # caneta do editado a cada edição feita por quem apenas edita servidor.
    marca = edicao.administrador if administrador_permitido else perfil.is_superuser
    alterou_marca = marca != perfil.is_superuser
    if alterou_marca:
        # A MESMA regra do ato da rota direta, importada de `administrador.py`: escrita duas vezes,
        # ela divergiria na primeira mudança.
        recusa_da_marca = recusa_de_auto_revogacao(edicao.servidor_id, autor_id, marca)
        if recusa_da_marca is not None:
            return DesfechoCadastro(perfil=None, recusa=recusa_da_marca)
    _aplicar(perfil, edicao, foto)
    perfil.is_superuser = marca
    try:
        # A caneta só é escrita se o cadastro inteiro passar: `full_clean` recusando derruba os dois.
        perfil.full_clean(exclude=["password"])
        perfil.save()
    except ValidationError as recusa:
        return DesfechoCadastro(perfil=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    return DesfechoCadastro(perfil=perfil, marca_alterada=alterou_marca)
```

**`apps/user_admin/urls.py`** — três rotas: a tela, a lista que ela recarrega e a gravação.
```python
    path("servidores/administrador/", views.modal_administrador, name="modal_administrador"),
    # A lista de servidores da unidade escolhida, recarregada por HTMX quando o primeiro select
    # muda. Leitura protegida pela mesma ação, e sem registro: é navegação dentro da tela do ato.
    path("servidores/administrador/opcoes/", views.opcoes_administrador, name="opcoes_administrador"),
    path("servidores/<int:servidor>/administrador/", views.gravar_administrador, name="gravar_administrador"),
```

**`apps/competencias/catalogo.py`** — o catálogo de atribuir para de oferecer o que não se atribui.
```python
# `_slugs_exclusivos` deixa de ser privado e passa a ser importável — é o MESMO conjunto que o
# avaliador subtrai, lido do registro em código. Um segundo lugar computando "quais são as
# exclusivas" seria a divergência esperando para acontecer, e uma lista escrita à mão aqui seria a
# configuração em runtime que o §3.5 recusa.
def acoes_oferecidas(unidade: Unidade) -> QuerySet[Acao]:
    return (
        Acao.objects.exclude(atribuicoes__unidade=unidade)
        .exclude(slug__in=slugs_exclusivos())
        .filter(ativa=True)
    )
```

**`apps/competencias/menus_declarados.py`** — o caminho direto para a ação.
```python
MENU_ADMINISTRADOR = ContratoMenu(
    slug="competencias.administrador",
    nome="Administração",
    itens=(
        ...,
        ItemDeMenu(
            acao_implementada=ACAO_TORNAR_ADMINISTRADOR,
            variante_icone=VarianteIcone.PEQUENO,
            forma=FormaItem.LINHA,
        ),
    ),
)
```

**`static/src/tema-dimap.dev.css`** — o átomo da aura e a molécula do botão que a veste.
```css
/* ÁTOMO. A `aura` do daisyUI fica empilhada no HTML — `@apply` de classe daisyUI derruba a folha
   inteira (skill componentes-frontend, §2.1). Aqui vai só a pele: a água da escala do DS e o tempo
   da volta. */
.aura-onsen {
  @apply text-agua-500 bg-agua-200 duration-3000;
}

/* MOLÉCULA. O botão de ato grave, reusável por qualquer ação de peso: a aura veste o controle, e o
   controle tem DUAS faces no DOM — quem escolhe é o estado no invólucro. Duas faces, e não uma que
   troca de classe, porque cada uma manda uma coisa diferente (`tornar=1` e `tornar=0`) e porque é o
   que permite ao estado vir tanto do servidor quanto de um controle local, sem o CSS saber a
   diferença. Nenhuma face é redeclarada aqui: `.btn-onsen` e `.card-well` entram empilhados no HTML,
   intocados. */
.botao-aura > .botao-aura-acionado { @apply hidden; }
.botao-aura-ligado > .botao-aura-repouso { @apply hidden; }
.botao-aura-ligado > .botao-aura-acionado { @apply inline-flex; }
/* Acionado é estado consumado: a aura para de chamar quem já entrou. */
.botao-aura-ligado { @apply bg-transparent text-transparent; }
```

## 7 · Caveats
A ação mora em `apps/user_admin`, e não em app próprio como manda o §3.5. A exceção é a mesma já
declarada para cadastrar e editar servidor: administrar o cadastro de servidores não é processo da
DIMAP, e o ato escreve um campo do `Perfil`, que é model deste app. O custo é um app que acumula
quatro ações em vez de as distribuir, e ele já estava pago.

Nas **duas telas de formulário** a concessão **não é praticada pela ação** — ela é gravada pelo ato de
cadastrar, que registra a operação `criar_administrador` no lugar de `criar`, com o mesmo autor,
cargo, unidade e RF do alvo de qualquer outra linha. A alternativa seria praticar dois atos no mesmo
request, o que exigiria estender `protecao.py` para registrar em lista e conferir a competência do
ato acessório. O custo não é perder a informação, e sim que ela mora em **três** ações: levantar **todas**
as concessões da condição é ler `user_admin.tornar_administrador` mais as linhas de
`user_admin.criar_servidor` cuja operação é `criar_administrador` e as de
`user_admin.editar_servidor` cuja operação é `editar_administrador`.

Amarrar a marca ao formulário de edição (v3) tem preço: **conceder e revogar pela tela do servidor
passam a exigir o cadastro inteiro válido e salvo**. Cadastro herdado — RF fora do formato, sem
e-mail — precisa ser regularizado antes de receber a caneta, e a mesma gravação que dá os plenos
poderes também grava o que estiver digitado no resto do formulário. Quem precisa do ato isolado tem
o **modal da rota direta**, que continua praticando a ação sozinha e sem tocar no cadastro. A
alternativa — manter o `hx-post` próprio no modal de edição — é o que produzia a concessão efetiva
com o formulário recusado na mesma tela, e o gesto único que o usuário vê ali não comporta dois
desfechos opostos.

A conferência de quem pode armar a marca no cadastro acontece **dentro do ato**, e não no decorator,
que só conhece a ação que protege a rota. É o mesmo desenho de `raiz_permitida` na SPEC 020: a
orquestração resolve `is_superuser` e desce o booleano como dado. O custo é que a barreira dessa
concessão específica não está no mesmo lugar das outras, e um `criar_servidor` chamado de um script
novo sem passar o parâmetro concede silenciosamente — o default `False` é o que segura isso.

O estado do botão na tela de **criar servidor** é local ao navegador: não há alvo para consultar, e
a confirmação precisa armar um controle e fechar o aviso no mesmo gesto. Resolver isso só em CSS
custa duas ou três caixas de seleção encadeadas com `:has()`, e o §7.2 do CLAUDE.md manda perguntar
em vez de fazer malabarismo. A escolha entre o encadeamento e um punhado de JS de estado visual
**fica para o mock**, com aprovação explícita.

O recorte do catálogo é da **oferta**, e não da listagem: atribuição de ação exclusiva já gravada
antes do recorte continua aparecendo na tela da unidade até alguém removê-la. Ela é inócua — o
avaliador subtrai o slug do conjunto liberado, então a linha não habilita ninguém —, e apagá-la
sozinho seria a tela mexendo em dado que o usuário gravou. O custo é uma linha órfã possível na
tela de atribuições, que só some por ato de quem administra.

O administrador **impedido continua exercendo** esta ação e todas as outras: o
`PermissionsMixin.has_perm` responde `True` para superusuário ativo antes de consultar backend
algum, e o avaliador — que é quem conhece `em_exercicio` — nunca roda. A propriedade é herdada da
SPEC [020](020-unidade-como-ato-administrativo.md), que criou o regime, e não se conserta sem
sobrescrever o `has_perm` do Django. O custo é que afastamento não suspende a caneta de quem a tem,
e o que resta contendo isso é o ato registrado.

A placa do **modal da rota direta** continua dentro do `.modal-box` (v5): ela é parte do partial
que o `hx-post` da ação troca inteiro, e depende do servidor escolhido — tirá-la de lá exigiria um
segundo alvo de swap para mantê-la em dia. Aquele modal é curto e não rola, então a placa fica
centrada nele em vez da tela; o custo é o escurecimento cobrir só a caixa, e ele só vira defeito se
o modal crescer.

`is_superuser` é booleano no `Perfil` e não tem data, autor nem motivo. Quem concedeu e quando vive
apenas na execução registrada, que é tabela de outro app e não se junta ao cadastro em consulta
alguma. O custo é que a tela do servidor sabe *que* ele é administrador e nunca *desde quando* nem
*por quem* — e a resposta existe, mas só no histórico.

## 8 · Testes (TDD)

**Comportamento do ato**
- `test_tornar_administrador_grava_is_superuser` — o servidor passa a ter `is_superuser`, e
  `is_staff` permanece como estava. *(marker `banco`)*
- `test_revogar_administrador_tira_is_superuser` — a mesma ação no sentido inverso deixa o campo em
  `False`. *(marker `banco`)*
- `test_nao_revoga_a_si_mesmo` — autor e alvo iguais devolvem recusa com a mensagem em português no
  controle `administrador`, e o campo do banco não muda. *(marker `banco`)*
- `test_administrador_alcanca_organograma_inteiro` — tornado administrador, o perfil passa no
  `has_perm` de uma ação estrutural e alcança unidade de outro ramo, sem concessão gravada.
  *(marker `banco`)*
- `test_cadastro_com_marca_nasce_administrador` — `criar_servidor` com `administrador=True` e
  `administrador_permitido=True` grava o `Perfil` já com `is_superuser`. *(marker `banco`)*
- `test_cadastro_com_marca_registra_operacao_propria` — a execução gravada pelo cadastro que concede
  a condição tem operação `criar_administrador`, e a do cadastro comum tem `criar`.
  *(marker `banco`)*
- `test_cadastro_com_marca_sem_caneta_recusa_tudo` — a mesma marca com
  `administrador_permitido=False` volta recusa e **não grava servidor algum**. *(marker `banco`)*
- `test_poco_de_plenos_poderes_so_aparece_para_administrador` — o GET do formulário de cadastro e o
  do modal de edição trazem o controle para o superusuário e **não** o trazem para quem exerce
  cadastrar/editar servidor sem ser administrador. *(marker `banco`)*
- `test_modal_direto_lista_servidores_da_unidade_escolhida` — a rota de opções devolve só os
  servidores lotados na unidade recebida. *(marker `banco`)*
- `test_botao_reflete_o_estado_gravado` — a rota de gravação devolve o partial do botão no estado
  novo, afundado ao conceder e em relevo ao revogar. *(marker `banco`)*

**A marca no formulário de edição** (v3)
- `test_edicao_recusada_nao_torna_administrador` — POST de edição com a marca armada e RF inválido
  volta 422 e o alvo **não** fica com `is_superuser`. *(marker `banco`)*
- `test_edicao_valida_grava_a_marca_e_registra_operacao_propria` — POST válido com a marca armada
  grava `is_superuser` e registra a operação `editar_administrador`. *(marker `banco`)*
- `test_edicao_de_quem_nao_tem_caneta_nao_revoga_a_marca` — quem apenas edita servidor não recebe o
  controle e não o envia; o alvo administrador **continua** administrador. *(marker `banco`)*
- `test_edicao_nao_revoga_a_si_mesmo` — o superusuário editando a si mesmo com a marca desarmada
  volta recusado, e **nada** da edição é gravado. *(marker `banco`)*

- `test_aviso_de_confirmacao_nasce_fora_do_modal_box` — a placa da confirmação não é descendente
  do `.modal-box`, que a prenderia pelo `backdrop-filter`. *(marker `banco`)*

**Segurança da ação** (skill `acao-administrativa`; fora do teto)
- `test_anonimo_vai_ao_login_sem_registrar` — POST anônimo redireciona e não deixa linha. *(marker `banco`)*
- `test_nao_superusuario_recebe_403_registrado` — autenticado comum recebe 403 e a tentativa fica
  registrada. *(marker `banco`)*
- `test_catalogo_de_atribuir_nao_oferece_acao_exclusiva` — o modal de atribuir competência a uma
  unidade não lista `user_admin.tornar_administrador` nem `unidades.criar_unidade_raiz`, para
  administrador nenhum. *(marker `banco`)*
- `test_concessao_gravada_nao_libera_acao_exclusiva` — competência concedida para o cargo na unidade
  não abre a ação: só `is_superuser` abre. *(marker `banco`)*
- `test_exonerado_chega_como_anonimo` — administrador com `is_active=False` já não autentica:
  recebe 302 para o login, sem linha de negativa. *(marker `banco`)*
- `test_ato_grava_quem_cargo_unidade_operacao_e_alvo` — a execução autorizada registra o autor com
  cargo e unidade do momento, a operação e o RF do alvo; mudar a lotação depois não altera a linha.
  *(marker `banco`)*
- `test_conceder_e_revogar_sao_distinguiveis_no_historico` — as duas operações gravam valores
  diferentes sob a mesma ação. *(marker `banco`)*
- `test_escrita_so_por_post` — GET na rota de gravação é recusado e nada muda. *(marker `banco`)*
