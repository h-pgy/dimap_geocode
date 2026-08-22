---
spec: criacao_usuarios/004
versao: v2
atualizado_em: 2026-08-22
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: a recusa passa pelo contrato de erros de formulário, e a constraint do e-mail nomeia o campo
    que violou
---

# SPEC criacao_usuarios/004 — Criar servidor: ato protegido, senha temporária e o e-mail de acesso

## 1 · User story
Quem responde pela direção de uma unidade da DIMAP cadastra um servidor recém-chegado na tela de
criação, para que a pessoa receba por e-mail como entrar no sistema sem ninguém passar senha adiante
por mensagem.

## 2 · Condições de pronto
- [ ] **Criar servidor** é ação **estrutural** inscrita no catálogo, com rota protegida: quem responde
      pela direção da unidade a exerce sem concessão gravada, e quem não dirige unidade alguma recebe
      **403**.
- [ ] O formulário oferece **só as unidades do alcance** — as dirigidas e as abaixo delas, nenhuma para
      quem não dirige nada —, e POST com unidade de **outro ramo** é recusado com 403 mesmo com id
      válido.
- [ ] A listagem de servidores só oferece **"Novo servidor"** a quem pode criar.
- [ ] O **e-mail** integra o cadastro do servidor: obrigatório na criação, único entre os preenchidos e
      exibido no resumo do servidor.
- [ ] Concluído o cadastro, o servidor recebe um e-mail com o **RF e uma senha temporária de oito
      dígitos**, gravada como **provisória** — de uso único —; a senha não aparece em tela alguma, no
      registro do ato nem no banco.
- [ ] Com `ENFORCE_PREFEITURA_EMAIL` ligado, só **e-mail institucional** é aceito na tela —
      `@prefeitura.sp.gov.br` e `@sf.prefeitura.sp.gov.br` —, e o endereço de fora volta recusado no
      formulário; desligado, qualquer endereço passa. **O banco não tem essa regra**: `createsuperuser`,
      shell e management command seguem gravando o que quiserem.
- [ ] **Toda** recusa devolve **o mesmo formulário preenchido**, com o motivo em português na tarja e
      o **controle recusado em realce** — campo obrigatório em branco, e-mail torto, RF ou e-mail
      repetido, domínio não institucional. Nenhuma delas troca o formulário por uma página de erro.
- [ ] Cadastro que não se conclui **não deixa rastro**: RF ou e-mail já cadastrado e falha na entrega
      da senha — servidor SMTP indisponível ou destinatário recusado — devolvem o motivo na tela sem
      gravar servidor algum; envio **desligado por configuração** conclui o cadastro.
- [ ] O comando `enviar_email_teste` passa a morar em `apps/user_admin`, e o app `apps/users` **deixa
      de existir**: nenhuma referência a ele resta no projeto.
- [ ] Criar é **ato registrado** (SPEC [autorizacao/004](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md)):
      a execução fica gravada com a operação e o RF do servidor como alvo, e toda tentativa negada
      deixa linha.
- [ ] O design foi aprovado no **mock**, o **glifo da ação** existe nas duas variantes declaradas — sem
      ele o sistema não sobe (check `competencias.E003`) —, e peça nova foi portada para
      `static/src/tema-dimap.dev.css` e renderizada no styleguide antes de qualquer template usá-la.

## 3 · Domínio
O cadastro do servidor ganha o **e-mail**, que é por onde a credencial chega, e a senha temporária
existe entre a gravação e a caixa de entrada — em lugar nenhum além disso.

**`apps/user_admin/models/user.py`**
```python
class Perfil(AbstractBaseUser, PermissionsMixin):
    # ALTERADO na v2: a mensagem da unicidade, no mesmo tom da do e-mail — o default do Django
    # nomeia o model ("Perfil com este RF já existe"), e quem cadastra pensa em servidor.
    rf = models.CharField(
        max_length=20,
        unique=True,
        error_messages={"unique": "Já existe servidor cadastrado com este RF."},
    )
    ...
    # ALTERADO nesta SPEC: campo novo. Em branco para o cadastro anterior à criação por tela; a
    # unicidade vale só sobre os preenchidos.
    email = models.EmailField(blank=True)
    # ALTERADO nesta SPEC: campo novo. A senha em vigor é a temporária emitida no cadastro, que vale
    # uma vez; quem lê a marca para exigir a troca e derrubá-la é a SPEC de login (§4).
    senha_provisoria = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unidade"],
                condition=Q(e_titular=True),
                name="unidade_tem_um_titular",
            ),
            # ALTERADO nesta SPEC: constraint nova, no molde da sigla opcional do TipoImpedimento —
            # vários sem e-mail convivem, dois com o mesmo não.
            models.UniqueConstraint(
                fields=["email"],
                condition=~Q(email=""),
                name="email_unico_quando_preenchido",
                # ALTERADO na v2: sem o code `unique`, o Django joga a violação em `__all__` e a
                # tela não sabe qual controle realçar; sem a mensagem, quem lê recebe o nome da
                # constraint. Constraint com `condition` não herda nem um nem outro.
                violation_error_code="unique",
                violation_error_message="Já existe servidor cadastrado com este e-mail.",
            ),
        ]
```

**`services/utils/senha.py`**
```python
class PoliticaSenhaTemporaria(BaseModel):
    """O que a senha emitida tem que ser. Curta e numérica porque vale uma vez só e é digitada à
    mão a partir de um e-mail."""

    model_config = ConfigDict(frozen=True)

    comprimento: int = Field(default=8, ge=6)
    alfabeto: str = DIGITOS
```

O domínio consumido, e a pergunta que esta SPEC faz a cada peça:

- [`acao_protegida` e `registrar_ato`](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md) —
  a rota protegida, o alvo conferido contra o alcance e o rastro do ato.
- [`UnidadesSubordinadas`](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md) — "até onde o
  alvo desta ação pode chegar?", declarado no contrato dela.
- [`alcance_do_perfil`](../autorizacao/004-protecao-de-rota-e-registro-de-execucao.md) — "quais unidades
  este perfil alcança?"; é o conjunto que o formulário oferece e o decorator confere.
- [`has_perm`](../autorizacao/003-avaliador-e-backend-de-autorizacao.md) — "este perfil exerce esta ação
  estrutural?"; quem lê a direção da unidade é o backend, não esta tela.
- [`instanciar_acao`](../autorizacao/001-catalogo-de-acoes-em-codigo.md) — a declaração da ação,
  inscrita no registro em código.
- [`montar_email_acesso` e `EmailAcessoInput`](003-email-de-acesso.md) — "o que a mensagem diz, e com
  que forma?"; esta SPEC monta o pedido e manda entregar.
- [`EnviadorSmtp`, `MensagemEmail` e `SmtpEnvioError`](001-smtp.md) — a entrega, e o que ela levanta
  quando não acontece.

**Mock:** [004-mock-criar-servidor.html](004-mock-criar-servidor.html) — leia a skill `mock`.

## 4 · Fora de escopo
- Editar o cadastro do servidor, com gravação — SPEC `criacao_usuarios/005`.
- Tela de **login**, e o consumo da marca `senha_provisoria`: exigir a troca no primeiro acesso e
  derrubar a senha temporária depois do uso — sem dono ainda.
- **Reenvio** da senha e recuperação de senha esquecida — sem dono ainda.
- Registro em banco dos e-mails enviados (para quem, quando, com que desfecho) — sem dono ainda.
- Exonerar servidor — sem dono ainda.
- Pôr a ação no `MENU_ADMINISTRADOR` e renderizá-lo em tela — sem dono ainda.
- Cadastrar unidade a partir do formulário do servidor: o modal existe e segue sem destino — sem dono
  ainda.
- Separar as unidades de `apps/user_admin` num app próprio — iteração própria.

## 5 · Peças de referência a compor
- `@apps/competencias/protecao.py` → `acao_protegida`, `registrar_ato`: a barreira e o rastro.
- `@apps/competencias/utils.py` → `instanciar_acao`; `@apps/competencias/registro.py` →
  `_construir_registro`: onde a ação nova se inscreve.
- `@apps/competencias/consulta.py` → `alcance_do_perfil`: as unidades alcançadas, já em conjunto de ids.
- `@apps/user_admin/context.py` → `_catalogo_de_unidades` e `_catalogos_de_lotacao`: o catálogo que o
  select da lotação já monta — aqui ele só passa a aceitar recorte.
- `@services/domain/email` (SPEC 003) → `montar_email_acesso`, `EmailAcessoInput` e
  `montar_mensagem`: o conteúdo do e-mail de acesso e a mensagem pronta para o enviador.
- `@services/utils/smtp` → `EnviadorSmtp`, `build_smtp_config`, `build_smtp_retry_policy`,
  `SmtpEnvioError`.
- `@services/utils/erros_formulario` (SPEC [formularios/001](../formularios/001-erros-de-formulario.md))
  → `Formulario`, `CampoDeFormulario`, `RegraDeErro`, `LeitorDeFormulario`, `RecusaDeFormulario`; e
  `@apps/core/erros_formulario.py` → `de_validation_error`: a ponte do `ValidationError` do model.
- `@apps/user_admin/models/impedimentos.py` → `TipoImpedimento.Meta.constraints`: `UniqueConstraint`
  com `condition`.
- `secrets` (biblioteca padrão, sem dependência a instalar) → `choice`: o sorteio criptográfico da
  senha, no lugar de `random`.
- `@static/src/tema-dimap.dev.css` → `.glass-panel`, `.card-well`, `.form-field`, `.upload-well`,
  `.btn-onsen`, `.btn-etched`, `.tarja-vinculo` + `.tarja-vinculo-critica`, `.text-overline`; e os
  `.input-glass` com o halo do seu `:focus`, que o controle em realce reusa trocando só a cor.
- Skills: `componentes-frontend`, `daisyui`, `htmx`, `mock`, `pydantic-validation-errors`,
  `management-commands`, `escrever-testes`, `test-django-views`.

## 6 · Snippets
Os comentários abaixo são didáticos, para a leitura da SPEC — **não são portados**; no código vale o
§7.2 do CLAUDE.md.

**`apps/user_admin/acoes_declaradas.py`** — a ação inscrita.
```python
ACAO_CRIAR_SERVIDOR = instanciar_acao(
    slug="user_admin.criar_servidor",
    nome="Cadastrar servidor",
    nome_curto="Novo servidor",
    tooltip="Cadastra um servidor e entrega a ele a senha de primeiro acesso.",
    url_name="user_admin:criar_perfil",
    # O item genérico da SPEC autorizacao/006: a linha do menu é a mesma para todas as ações.
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Quem a exerce é quem dirige a unidade: não passa por atribuição nem concessão.
    estrutural=True,
    # A unidade-alvo é a que o formulário escolhe, e o parâmetro já é o default do alcance.
    alcance=UnidadesSubordinadas(),
)
```

**`static/src/acoes/user_admin/criar_servidor/icones/pequeno.svg`** e **`grande.svg`** — o glifo, um
arquivo por variante declarada. Silhueta e sinal, na mesma família dos glifos de titular e substituto
da página do servidor.
```html
<!-- Sem cor, sem espessura, sem `fill`: quem os aplica é o átomo `.icone-acao` do tema (SPEC
     autorizacao/006), e escrevê-los aqui venceria a pele por cascata. -->
<svg viewBox="0 0 24 24">
  <circle cx="9" cy="8" r="3.2"/>
  <path d="M3.5 20c0-3.2 2.5-5.4 5.5-5.4s5.5 2.2 5.5 5.4"/>
  <path d="M18.5 6.5v5"/>
  <path d="M16 9h5"/>
</svg>
```

**`apps/user_admin/urls.py`** — a tela e a escrita em rotas separadas.
```python
urlpatterns = [
    ...,
    path("servidores/novo/", views.criar_perfil, name="criar_perfil"),
    # Rota de escrita apartada da que mostra o formulário: é essa separação que faz "abrir a tela
    # não cadastra ninguém" ser estrutural, e não uma flag no formulário.
    path("servidores/novo/gravar/", views.gravar_servidor, name="gravar_servidor"),
]
```

**`apps/user_admin/schemas.py`** — o DTO do ato, ao lado do `NovoImpedimento` e sobre o
`_vazio_para_nulo` que já mora ali.
```python
# O select do cargo em comissão manda "" na opção vazia; para o cadastro, isso é ausência de cargo.
CargoOpcional = Annotated[int | None, BeforeValidator(_vazio_para_nulo)]


class NovoServidor(BaseModel):
    """ALTERADO na v2: quem o constrói é o `LeitorDeFormulario` da SPEC formularios/001, e não a view
    — e-mail torto e id não-numérico morrem aqui, antes de virar consulta, e a recusa volta como o
    próprio formulário."""

    model_config = ConfigDict(frozen=True)

    rf: str = Field(min_length=1, max_length=20)
    nome: str = Field(min_length=1, max_length=100)
    sobrenome: str = Field(min_length=1, max_length=150)
    email: EmailStr
    unidade_id: int
    cargo_base_id: int
    cargo_comissao_id: CargoOpcional = None
    # Resolvida na orquestração a partir do request: nem o domínio nem o cadastro sabem em que host
    # o sistema roda.
    url_acesso: HttpUrl
```

**`services/utils/senha.py`** — a credencial emitida.
```python
# `secrets` é da BIBLIOTECA PADRÃO: nada a instalar, nenhuma dependência nova no pyproject. É o
# módulo do CPython para material criptográfico — senha, token, identificador.
import secrets

# Só dígito: o alfabeto misto obriga a distinguir caixa e pares ambíguos (O/0, l/1) numa senha que
# alguém vai copiar de um e-mail, às vezes do celular. A brevidade é paga pelo uso único.
DIGITOS = "0123456789"


class GeradorSenhaTemporaria:
    """Callable: `secrets.choice`, nunca `random` — o gerador do `random` é previsível, e uma senha
    emitida deixaria as seguintes adivinháveis."""

    def __call__(self, politica: PoliticaSenhaTemporaria | None = None) -> SecretStr:
        escolhida = politica or PoliticaSenhaTemporaria()
        return SecretStr(
            "".join(secrets.choice(escolhida.alfabeto) for _ in range(escolhida.comprimento))
        )


gerar_senha_temporaria = GeradorSenhaTemporaria()
```

**`apps/user_admin/formularios.py`** — o catálogo do formulário, no contrato de `formularios/001`.
```python
FORMULARIO_SERVIDOR = Formulario(
    campos=(
        CampoDeFormulario(controle="rf", rotulo="RF"),
        CampoDeFormulario(controle="nome", rotulo="Nome"),
        CampoDeFormulario(controle="sobrenome", rotulo="Sobrenome"),
        CampoDeFormulario(
            controle="email",
            rotulo="E-mail",
            # A única regra particular desta tela: as demais recusas se dizem bem com as padrão.
            regras={"value_error": RegraDeErro(mensagem="E-mail inválido: confira o endereço.")},
        ),
        CampoDeFormulario(controle="unidade", rotulo="Unidade"),
        CampoDeFormulario(controle="cargo_base", rotulo="Cargo base"),
        CampoDeFormulario(controle="cargo_comissao", rotulo="Cargo em comissão"),
    )
)

ler_novo_servidor = LeitorDeFormulario(NovoServidor, FORMULARIO_SERVIDOR)
traduzir_recusa = TradutorDeRecusa(FORMULARIO_SERVIDOR)
```

**`apps/user_admin/cadastro.py`** — o ato: ler o formulário, gravar e entregar a senha.
```python
ERRO_ENVIO = "Cadastro não concluído: não foi possível entregar a senha temporária em {email}."


@dataclass(frozen=True)
class DesfechoCadastro:
    """Recado do ato para a view. Não é DTO de domínio: não cruza fronteira de serviço e carrega o
    próprio model gravado — mesma natureza do `_RegistroAto` da SPEC autorizacao/004."""

    perfil: Perfil | None
    # ALTERADO na v2: a recusa deixa de ser tupla de frases e passa a ser a da SPEC formularios/001,
    # que já sabe qual controle realçar.
    recusa: RecusaDeFormulario | None = None


def criar_servidor(
    valores: Mapping[str, Any],
    foto: UploadedFile | None = None,
) -> DesfechoCadastro:
    """Quem fica cadastrado é quem recebeu como entrar: o envio acontece dentro da transação, e a
    falha dele derruba a gravação junto.

    ALTERADO na v2: recebe o formulário cru e delega a leitura ao `LeitorDeFormulario`. Construir o
    DTO na view entregaria a recusa ao `PydanticValidationMiddleware`, cuja resposta, no alvo do
    form, apaga o formulário inteiro (SPEC formularios/001, Caveats). O `try` do banco e do SMTP
    segue aqui pelo mesmo motivo de sempre: é este módulo que sabe o que cada falha significa para o
    cadastro."""
    leitura = ler_novo_servidor(valores)
    if leitura.recusa is not None:
        return DesfechoCadastro(perfil=None, recusa=leitura.recusa)
    novo = leitura.dto
    if _dominio_recusado(novo.email):
        return DesfechoCadastro(perfil=None, recusa=_recusa_do_dominio())
    senha = gerar_senha_temporaria()
    try:
        with transaction.atomic():
            perfil = _gravar(novo, senha, foto)
            _entregar_senha(perfil, senha, novo.url_acesso)
    except ValidationError as recusa:
        # RF e e-mail repetidos chegam aqui pelo full_clean: conferir antes com um SELECT abriria
        # janela entre a consulta e o INSERT, e a unicidade é do banco. A ponte de `apps/core`
        # preserva o `code`, que é o que faz a mensagem do model chegar realçada no campo certo.
        return DesfechoCadastro(perfil=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    except SmtpEnvioError:
        return DesfechoCadastro(perfil=None, recusa=_recusa_da_entrega(novo.email))
    return DesfechoCadastro(perfil=perfil)


def _recusa_do_dominio() -> RecusaDeFormulario:
    # Recusa que não vem de fonte nenhuma: é política desta rota, e o controle a realçar é o e-mail,
    # porque é o endereço que precisa mudar.
    return traduzir_recusa((ErroBruto(controle="email", tipo="dominio", mensagem=ERRO_DOMINIO),))


def _recusa_da_entrega(email: str) -> RecusaDeFormulario:
    return traduzir_recusa(
        (ErroBruto(controle="email", tipo="entrega", mensagem=ERRO_ENVIO.format(email=email)),)
    )


def _gravar(novo: NovoServidor, senha: SecretStr, foto: UploadedFile | None) -> Perfil:
    perfil = Perfil(
        rf=novo.rf,
        nome=novo.nome,
        sobrenome=novo.sobrenome,
        email=novo.email,
        unidade_id=novo.unidade_id,
        cargo_base_id=novo.cargo_base_id,
        cargo_comissao_id=novo.cargo_comissao_id,
        foto=foto,
    )
    # A senha nasce hasheada: nem o banco, nem o log, nem um traceback guardam o texto claro.
    perfil.set_password(senha.get_secret_value())
    perfil.senha_provisoria = True
    perfil.full_clean(exclude=["password"])
    perfil.save()
    return perfil


def _entregar_senha(perfil: Perfil, senha: SecretStr, url_acesso: HttpUrl) -> None:
    """Recusa do destinatário e queda do servidor são o mesmo desfecho para o cadastro — a senha
    não chegou —, e por isso viram a mesma exceção. Envio DESLIGADO por configuração não entra
    aqui: a mensagem foi montada e impressa, e o cadastro de desenvolvimento segue."""
    conteudo = montar_email_acesso(
        EmailAcessoInput(
            nome=perfil.nome,
            rf=perfil.rf,
            destinatario=perfil.email,
            senha_temporaria=senha,
            url_acesso=url_acesso,
        )
    )
    mensagem = montar_mensagem(conteudo, destinatarios=(perfil.email,))
    enviador = EnviadorSmtp(build_smtp_config(settings), build_smtp_retry_policy(settings))
    resultado = enviador(mensagem)
    if resultado.destinatarios_recusados:
        raise SmtpEnvioError(f"Destinatário recusado: {perfil.email}.")
```

**`apps/user_admin/context.py`** — o catálogo do select **já existe**; o que ele ganha é o recorte.
```python
def _catalogo_de_unidades(ids_permitidos: Collection[int] | None = None) -> dict[str, Any]:
    """ALTERADO nesta SPEC: `ids_permitidos` recorta o catálogo ao alcance de quem abre a tela.
    Sem ele, todas — que é o que o formulário de unidade e o modal de edição continuam pedindo.

    Recebe ids, e não o perfil: `context.py` não pode importar `apps.competencias`, que já importa
    este módulo. Quem resolve o alcance é a view."""
    unidades = Unidade.objects.select_related("tipo").order_by("sigla")
    if ids_permitidos is not None:
        unidades = unidades.filter(pk__in=ids_permitidos)
    return {"unidades": unidades}


def contexto_criar_perfil(ids_permitidos: Collection[int]) -> dict[str, Any]:
    # O recorte desce por `_catalogos_de_lotacao` até o catálogo acima — nenhuma consulta nova.
    return (
        contexto_fundo_admin()
        | _catalogos_de_lotacao(ids_permitidos)
        | _contexto_do_modal_de_unidade()
    )


def contexto_cadastro_recusado(
    valores: Mapping[str, Any],
    desfecho: DesfechoCadastro,
    ids_permitidos: Collection[int],
) -> dict[str, Any]:
    """O que volta é o mesmo formulário: o digitado permanece, a foto não — arquivo de upload não se
    reconstrói de uma resposta de servidor.

    ALTERADO na v2: repopula do formulário cru, e não do DTO — na recusa do próprio DTO não existe
    DTO algum para repopular."""
    return contexto_criar_perfil(ids_permitidos) | {
        "perfil": _valores_do_formulario(valores),
        # `mensagens` alimenta a tarja; `realce`, a classe de cada controle — os dois já prontos
        # pela SPEC formularios/001, sem o template precisar de condicional.
        "erros": desfecho.recusa.mensagens,
        "realce": desfecho.recusa.realce,
    }


CAMPOS_DE_ID = ("unidade_id", "cargo_base_id", "cargo_comissao_id")


def _valores_do_formulario(valores: Mapping[str, Any]) -> dict[str, Any]:
    """O `selected` do select compara com `unidade.pk`: id que voltasse como texto não seria
    reconhecido, e o campo perderia a escolha justamente na tela que pede para corrigi-la. Só os
    ids são convertidos — RF com zero à esquerda não sobreviveria a um `int()`."""
    lidos = dict(valores)
    for campo in CAMPOS_DE_ID:
        bruto = lidos.get(campo)
        if not isinstance(bruto, str) or not bruto.isdigit():
            continue
        lidos[campo] = int(bruto)
    return lidos
```

**`config/settings.py`** e **`.env.example`** — a chave da política, no molde das demais.
```python
enforce_prefeitura_email: bool = Field(default=True, alias="ENFORCE_PREFEITURA_EMAIL")
```
```sh
# Fecha o cadastro pela tela aos domínios institucionais. Desligue só em ambiente de teste.
ENFORCE_PREFEITURA_EMAIL=1
```

**`apps/user_admin/cadastro.py`** — a política do endereço, conferida no ato e em lugar nenhum mais.
```python
DOMINIOS_INSTITUCIONAIS = ("prefeitura.sp.gov.br", "sf.prefeitura.sp.gov.br")
ERRO_DOMINIO = "O e-mail precisa ser institucional: @" + ", @".join(DOMINIOS_INSTITUCIONAIS) + "."


def _dominio_recusado(email: str) -> bool:
    """Igualdade sobre o domínio, e não `endswith`: `sp.gov.br.exemplo.com` e
    `falsaprefeitura.sp.gov.br` terminam parecido e não são a prefeitura.

    Lê `settings` porque este módulo é a camada de aplicação e já lê para o SMTP — o que ele NÃO faz
    é levar a regra para o model: gravar direto pelo shell, pelo `createsuperuser` ou por um comando
    continua livre, e é para isso que a regra mora aqui (§7)."""
    if not settings.ENFORCE_PREFEITURA_EMAIL:
        return False
    _, _, dominio = email.rpartition("@")
    return dominio.lower() not in DOMINIOS_INSTITUCIONAIS
```

O `criar_servidor` a confere **depois de ler o formulário e antes de abrir a transação** — endereço de
fora não chega a gerar senha nem a abrir conversa com o SMTP, e volta realçando o controle do e-mail.

**`apps/user_admin/views.py`** — a view chega com competência e alvo conferidos, e resolve na
orquestração o que a autorização recorta.
```python
@acao_protegida(ACAO_CRIAR_SERVIDOR)
def criar_perfil(request: HttpRequest) -> HttpResponse:
    # Oferecer o que o decorator vai recusar no POST é convidar ao 403: a lista sai do mesmo alcance
    # que a barreira confere.
    return render(request, TEMPLATE_FORMULARIO, contexto_criar_perfil(alcance_do_perfil(request.user)))


@acao_protegida(ACAO_CRIAR_SERVIDOR)
@require_POST
def gravar_servidor(request: HttpRequest) -> HttpResponse:
    # ALTERADO na v2: a view traduz nome de controle em nome de campo e para de construir o DTO.
    # Quem o constrói é o ato — a recusa dele volta como formulário, não como página de erro.
    valores = {
        "rf": request.POST["rf"],
        "nome": request.POST["nome"],
        "sobrenome": request.POST["sobrenome"],
        "email": request.POST["email"],
        "unidade_id": request.POST["unidade"],
        "cargo_base_id": request.POST["cargo_base"],
        "cargo_comissao_id": request.POST["cargo_comissao"],
        # O host de onde o convite parte é da orquestração, não do formulário.
        "url_acesso": request.build_absolute_uri("/"),
    }
    desfecho = criar_servidor(valores, foto=request.FILES.get("foto"))
    if desfecho.perfil is None:
        return render(
            request,
            TEMPLATE_FORMULARIO_RECUSADO,
            contexto_cadastro_recusado(valores, desfecho, alcance_do_perfil(request.user)),
            status=422,
        )
    # A view NUNCA grava a execução: deixa o recado e quem persiste é o decorator, depois do return.
    registrar_ato(
        request,
        operacao="criar",
        alvo_tipo="servidor",
        alvo_identificador=desfecho.perfil.rf,
    )
    return render(request, TEMPLATE_CADASTRO_CONCLUIDO, contexto_cadastro_concluido(desfecho.perfil))
```

**`templates/user_admin/perfil_form.html`** — o formulário passa a ter destino, e o alvo do swap é ele
mesmo: a recusa devolve o formulário preenchido, o sucesso devolve o painel de conclusão.
```html
{# hx-encoding: sem isto a foto não sobe — o HTMX manda urlencoded por padrão. #}
<form id="form-servidor"
      hx-post="{% url 'user_admin:gravar_servidor' %}"
      hx-encoding="multipart/form-data"
      hx-target="#form-servidor"
      hx-swap="outerHTML">
```

**`static/src/tema-dimap.dev.css`** — o átomo do controle em realce, nas quatro tonalidades
semânticas. Só a de erro tem consumidor nesta SPEC; as outras três nascem para a próxima tela não
inventar a sua. Quem escolhe qual tonalidade vestir é o `TomDeRealce` da SPEC
[formularios/001](../formularios/001-erros-de-formulario.md).
```css
/* O halo é do CONTROLE, não do campo: rótulo fora do realce mantém a linha alinhada com os vizinhos
   da grade. A receita é a do `.input-glass:focus`, com a cor do estado no lugar do ciano. */
.campo-realce-erro    { @apply border-error/60;   --halo-realce: 220, 38, 38; }
.campo-realce-alerta  { @apply border-warning/60; --halo-realce: 180, 83, 9; }
.campo-realce-info    { @apply border-info/60;    --halo-realce: 2, 132, 199; }
.campo-realce-sucesso { @apply border-success/60; --halo-realce: 5, 150, 105; }
.campo-realce-erro, .campo-realce-alerta, .campo-realce-info, .campo-realce-sucesso {
  box-shadow: var(--sombra-poco), 0 0 0 3px rgba(var(--halo-realce), 0.18), 0 0 20px rgba(var(--halo-realce), 0.35);
}
```

**`templates/user_admin/partials/_secao_identificacao.html`** e **`_secao_lotacao.html`** — quem
*aplica* o átomo. Cada controle pergunta pelo próprio nome, e nada mais.
```html
{# O realce é do CONTROLE, não do `.form-field`: o rótulo fora dele mantém a linha alinhada com os #}
{# vizinhos da grade. Controle sem recusa devolve string vazia e a classe some.                    #}
<input type="text" name="rf" value="{{ perfil.rf|default:'' }}"
       class="input input-glass {{ realce.rf }}" />
<select name="unidade" class="select select-glass {{ realce.unidade }}" data-select-onsen>
```

**`templates/user_admin/servidores_list.html`** — a porta de entrada da tela, aberta a quem pode.
```html
{# `perms` vem do context processor do auth e é servido pelo backend de competência (SPEC          #}
{# autorizacao/003): esconder o botão não custa nada ao contexto da view, e quem barra de verdade  #}
{# é o `acao_protegida` da rota.                                                                   #}
{% if perms.user_admin.criar_servidor %}
  <a href="{% url 'user_admin:criar_perfil' %}" class="btn btn-onsen btn-sm">Novo servidor</a>
{% endif %}
```

## 7 · Caveats
**A ação mora em `apps/user_admin`, exceção declarada ao §3.5.** A regra existe para que um processo
novo da DIMAP não engorde o núcleo, e administrar o próprio cadastro de servidores não é processo:
opera sobre os models deste app e não existe sem eles — a mesma exceção da SPEC `autorizacao/007`.
Custo: `user_admin` deixa de ser só cadastro e passa a declarar ação, ganhando mais um eixo antes de
as unidades saírem dele para app próprio.

**O app `users` é dissolvido e o comando de e-mail de teste passa a `user_admin`.** Ele existia para
ser a casa da criação de usuário, que nasce aqui dentro do app que já tem o `Perfil`, as telas e o
cadastro — e um app sem rota, model nem ação, guardando um comando só, seria um segundo nome parecido
para a mesma coisa. Custo: o `apps/users` some do histórico de import de quem o conhecia, e os testes
dele mudam de pasta.

**Cadastro e envio vivem na mesma transação: falha na entrega desfaz o cadastro, e envio desligado por
configuração o conclui.** Servidor gravado sem receber a senha é conta que ninguém usa e que ninguém
sabe existir; o desligamento, por sua vez, é o modo de desenvolvimento, onde a mensagem sai no stdout.
Custo: o `INSERT` fica aberto durante a conversa SMTP, uma indisponibilidade do Gmail impede cadastrar
qualquer pessoa, e num ambiente desligado sem querer cria-se servidor cuja senha só existe no log do
processo.

**A senha é de uso único por declaração, e quem a invalidará é a SPEC de login.** Ela nasce, vai no
e-mail e sobra o hash com a marca `senha_provisoria` — marcar agora é o que impede que o servidor
cadastrado nesta janela fique sem a marca quando o login chegar. Custo: a marca nasce sem consumidor,
oito dígitos valem enquanto ninguém os derruba, e perdido o e-mail não há reenvio — a única saída é o
admin do Django.

**O `try/except` mora em `cadastro.py`, não na view.** Recusa do model e falha de envio são desfechos
do ato, e é este módulo que sabe o que cada um significa para o cadastro. Custo: `criar_servidor`
acumula gravar, entregar e traduzir falha, e uma exceção nova precisa ser lembrada aqui.

**`criar_servidor` recebe o formulário cru, e não o DTO pronto.** Quem monta o `NovoServidor` é o
`LeitorDeFormulario`, porque construí-lo na view entregaria a recusa ao `PydanticValidationMiddleware`
— cuja resposta, no alvo do form, apaga a tela (SPEC formularios/001). Custo: a assinatura do ato
deixa de ser tipada na entrada, e a tradução de nome de controle para nome de campo do DTO passa a
morar na view.

**Falha de entrega e e-mail fora do domínio realçam o campo do e-mail.** Nenhuma das duas vem de uma
recusa de campo, mas as duas se resolvem trocando o endereço. Custo: a causa real — SMTP fora do ar —
fica apontando para um controle que pode estar correto.

**`DesfechoCadastro` é dataclass, não DTO Pydantic.** Ele carrega o `Perfil` gravado e não cruza
fronteira de serviço — passa de uma função para a view do mesmo app, como o `_RegistroAto` da SPEC
`autorizacao/004`. Custo: uma estrutura de retorno fora do padrão Pydantic das fronteiras.

**POST recusado pela validação também gera linha de execução autorizada, sem operação.** O decorator
grava toda requisição que altera estado, e a recusa acontece depois dele. Custo: o histórico mistura
ato praticado com tentativa que não produziu efeito, e distingui-los exige reparar na operação vazia.

**A política de domínio vive na rota, e o banco não a conhece.** Ela é decisão institucional sujeita
a exceção — o estagiário com e-mail de outro órgão, a carga de teste — e gravá-la como constraint
transformaria cada exceção em migração. Custo: o cadastro criado por shell, por `createsuperuser` ou
por management command entra com qualquer endereço, e nada no banco denuncia o que a tela teria
recusado.

**O e-mail é único só entre os preenchidos.** O cadastro anterior à criação por tela não tem endereço,
e exigi-lo agora pediria migração de dados inventados. Custo: convivem servidores sem e-mail, que não
têm por onde receber senha nenhuma.

## 8 · Testes (TDD)
Dois grupos. O **comportamento** obedece ao teto de 10; a **bateria de segurança** da skill
`acao-administrativa` vem além dele — cortar um dos seus itens para caber na conta é escolher não
testar uma porta. Quase todos exigem `Perfil` gravado e carregam o marker `banco`.

**Comportamento**

- `test_formulario_oferece_so_as_unidades_do_alcance` — a unidade dirigida e as de baixo aparecem no
  select; a de outro ramo e a de cima não, e quem não dirige nada não recebe nenhuma. *(marker `banco`)*
- `test_cadastro_grava_o_servidor` — o POST válido cria o `Perfil` com e-mail e com a senha emitida
  utilizável e marcada como provisória. *(marker `banco`)*
- `test_senha_temporaria_sai_no_email_do_servidor` — a mensagem entregue vai para o endereço
  cadastrado e carrega o RF e a senha, no bloco de OTP. *(marker `banco`)*
- `test_falha_na_entrega_desfaz_o_cadastro` — enviador que levanta e destinatário recusado não deixam
  `Perfil` gravado e devolvem o motivo na tela; com o envio desligado por configuração, o cadastro é
  concluído. *(marker `banco`)*
- `test_email_fora_do_dominio_e_recusado_com_a_politica_ligada` — endereço de outro domínio volta
  recusado no formulário e não gera senha nem envio; com `ENFORCE_PREFEITURA_EMAIL` desligado, o mesmo
  endereço é aceito. *(marker `banco`)*
- `test_rf_ou_email_repetido_e_recusado_sem_gravar` — os dois casos devolvem o formulário com o motivo
  e com o **controle repetido realçado**, e o cadastro existente segue intocado. *(marker `banco`)*
- `test_campo_invalido_devolve_o_formulario_realcado` — nome em branco e e-mail torto voltam no mesmo
  formulário, com o motivo em português e `campo-realce-erro` no controle recusado; o que já estava
  digitado permanece, o select mantém a escolha e nenhum servidor é gravado. *(marker `banco`)*
- `test_listagem_so_oferece_novo_servidor_a_quem_pode` — quem dirige vê o botão; quem não exerce a ação
  não o recebe no HTML. *(marker `banco`)*
- `test_senha_temporaria_respeita_a_politica` — a senha sai com os oito dígitos da política, sem
  caractere fora do alfabeto dela, e duas gerações seguidas não coincidem.

**Segurança da ação** — bateria da skill `acao-administrativa`, fora do teto.

- `test_anonimo_vai_para_o_login_sem_deixar_linha` — o anônimo é redirecionado, não recebe 403 e não
  gera execução. *(marker `banco`)*
- `test_autenticado_sem_competencia_recebe_403_registrado` — perfil logado sem a ação recebe 403, e a
  tentativa fica gravada como não autorizada. *(marker `banco`)*
- `test_estrutural_libera_quem_dirige_sem_concessao` — o titular em exercício entra sem concessão
  gravada, e o substituto dele entra enquanto ele está afastado. *(marker `banco`)*
- `test_concessao_em_outra_unidade_nao_libera` — a mesma ação concedida ao cargo noutra unidade,
  inclusive na superior, não abre a tela. *(marker `banco`)*
- `test_perfil_fora_de_exercicio_nao_exerce` — impedido e exonerado recebem 403, ainda que dirijam a
  unidade no papel. *(marker `banco`)*
- `test_gravar_recusa_unidade_fora_do_alcance` — POST com unidade existente de outro ramo é recusado
  com 403 sem a view conferir nada, e nenhum servidor é gravado. *(marker `banco`)*
- `test_gravar_sem_o_parametro_do_alvo_e_400` — POST que omite `unidade` é recusado antes de a view
  rodar, e a recusa não vira linha de negativa. *(marker `banco`)*
- `test_acao_inativa_nao_libera_ninguem` — com a projeção marcada inativa, a concessão gravada deixa de
  abrir a rota. *(marker `banco`)*
- `test_execucao_registrada_com_a_lotacao_do_momento` — o POST autorizado grava unidade e cargos
  vigentes no ato, com a operação `criar` e o RF como alvo; mudar a lotação depois não altera a linha.
  *(marker `banco`)*
- `test_ato_em_substituicao_diz_por_quem_responde` — o substituto que age pela competência do afastado
  deixa gravado quem cobria; quem age por competência própria deixa o campo vazio. *(marker `banco`)*
- `test_leitura_autorizada_nao_vira_registro` — o GET da tela não gera linha; o mesmo GET negado gera.
  *(marker `banco`)*
- `test_senha_nao_aparece_na_resposta_nem_no_registro` — o HTML devolvido no sucesso e a linha de
  execução não contêm a senha emitida. *(marker `banco`)*
- `test_gravacao_so_por_post` — GET na rota de escrita é recusado, e nenhum servidor é criado.
  *(marker `banco`)*
