---
spec: criacao_usuarios/006
versao: v2
atualizado_em: 2026-08-22
testes_tdd: true
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: o painel de nova unidade das duas telas passa a oferecer só unidades do alcance
---

# SPEC criacao_usuarios/006 — Enforcement do cadastro de servidor: a mesma regra nas duas telas

## 1 · User story
Quem responde pela direção de uma unidade da DIMAP preenche o formulário de criação e o modal de
edição de servidor para obter um cadastro cujo RF, nome, e-mail e foto obedecem à mesma regra nas
duas telas, recusada na própria tela quando não obedecem.

## 2 · Condições de pronto
- [ ] **RF é sete dígitos**: a pontuação da digitação é aceita e descartada, e `812.345-6` grava
      `8123456`. RF fora do formato é recusado nas duas telas, com o controle em realce e nada
      gravado.
- [ ] **Nome e sobrenome aceitam letra, espaço, hífen e apóstrofo**: `Ana d'Ávila` e `Silva-Santos`
      passam, `12345`, `Ana2` e `Nogueira Jr.` são recusados nas duas telas. Espaço das pontas cai e
      espaço interno repetido colapsa.
- [ ] **E-mail fora dos domínios institucionais é recusado também na edição**, com a mesma frase e o
      mesmo desligamento por configuração que a criação já tem.
- [ ] **E-mail é gravado em caixa baixa**: `ANA@Prefeitura.SP.gov.BR` e `ana@prefeitura.sp.gov.br`
      não convivem como dois cadastros.
- [ ] **Foto que não é imagem, ou acima de 2 MB, é recusada** nas duas telas, com o motivo no
      controle da foto e nenhum outro campo do cadastro gravado.
- [ ] **Campo em branco continua dizendo "preencha"**: recusa de obrigatoriedade não se confunde com
      recusa de formato em nenhum dos controles.
- [ ] **Todo select de unidade das duas telas só oferece unidades do alcance** de quem preenche: o de
      lotação e o de unidade superior do painel de nova unidade.
- [ ] O **painel de nova unidade não oferece criar unidade raiz**: unidade sem pai não cai no alcance
      de ninguém, e quem a criasse não a teria de volta na lista. A página de cadastro de unidade
      continua oferecendo.
- [ ] **Criar superusuário pela linha de comando produz servidor gravável**: com lotação, cargo base,
      cargo em comissão e, quando pedido, titularidade da unidade.
- [ ] O **banco de desenvolvimento não tem servidor com RF fora do formato**: a faixa fictícia ocupa
      sete dígitos e o superusuário é titular da DIMAP.

## 3 · Domínio
Nenhum model novo. O que esta SPEC modela são os **tipos dos campos de identificação** — o RF, o
nome de pessoa e o e-mail deixam de ser `str` com limite de tamanho e passam a ser tipos que sabem a
própria forma, compartilhados pelos DTOs das duas telas e pelo do superusuário.

**`apps/user_admin/schemas.py`**
```python
PADRAO_RF = r"^\d{7}$"
# Letra unicode dos dois lados de cada separador: sem isso "Ana " e "-Ana" passariam.
PADRAO_NOME = r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)*$"


def _so_digitos(valor: object) -> object:
    return re.sub(r"\D", "", valor) if isinstance(valor, str) else valor


def _espacos_colapsados(valor: object) -> object:
    return " ".join(valor.split()) if isinstance(valor, str) else valor


def _caixa_baixa(valor: object) -> object:
    return valor.strip().lower() if isinstance(valor, str) else valor


# O RF é o USERNAME_FIELD: a forma guardada é a única que o login vai poder pedir.
RegistroFuncional = Annotated[
    str,
    BeforeValidator(_so_digitos),
    Field(min_length=1, pattern=PADRAO_RF),
]
NomeDePessoa = Annotated[
    str,
    BeforeValidator(_espacos_colapsados),
    Field(min_length=1, max_length=100, pattern=PADRAO_NOME),
]
SobrenomeDePessoa = Annotated[
    str,
    BeforeValidator(_espacos_colapsados),
    Field(min_length=1, max_length=150, pattern=PADRAO_NOME),
]
EmailDeServidor = Annotated[EmailStr, BeforeValidator(_caixa_baixa)]
```

Os dois DTOs do cadastro, inteiros, com o que mudou marcado — a partir daqui é esta a forma vigente:

```python
class NovoServidor(BaseModel):
    model_config = ConfigDict(frozen=True)

    rf: RegistroFuncional              # ALTERADO nesta SPEC: era str com max_length=20
    nome: NomeDePessoa                 # ALTERADO nesta SPEC
    sobrenome: SobrenomeDePessoa       # ALTERADO nesta SPEC
    email: EmailDeServidor             # ALTERADO nesta SPEC: era EmailStr
    unidade_id: int
    cargo_base_id: int
    cargo_comissao_id: CargoOpcional = None
    url_acesso: HttpUrl


class EdicaoServidor(BaseModel):
    model_config = ConfigDict(frozen=True)

    servidor_id: int
    rf: RegistroFuncional              # ALTERADO nesta SPEC
    nome: NomeDePessoa                 # ALTERADO nesta SPEC
    sobrenome: SobrenomeDePessoa       # ALTERADO nesta SPEC
    email: EmailDeServidor             # ALTERADO nesta SPEC
    unidade_id: int
    cargo_base_id: int
    cargo_comissao_id: CargoOpcional = None
```

O superusuário entra pelos mesmos tipos, e nomeia unidade e cargos por sigla porque quem digita na
linha de comando não tem id em mãos:

```python
class NovoSuperusuario(BaseModel):
    model_config = ConfigDict(frozen=True)

    rf: RegistroFuncional
    nome: NomeDePessoa
    sobrenome: SobrenomeDePessoa
    email: EmailDeServidor
    unidade_sigla: str
    cargo_base_sigla: str
    cargo_comissao_nome: str
    e_titular: bool = False
```

## 4 · Fora de escopo
- Conferência aritmética do dígito verificador do RF — sem dono ainda.
- Normalização do RF digitado na tela de entrada — SPEC de autenticação.
- Formato de RF exigido no model, no `createsuperuser` e no shell — sem dono; gravar por fora das
  telas segue livre.
- Lista de domínios institucionais variável por unidade — sem dono ainda.
- **Recusar no servidor** a unidade cujo pai está fora do alcance de quem a cria: aqui o painel deixa
  de oferecê-la, e nada confere o que chega — SPEC de criação de unidade.

## 5 · Peças de referência a compor
- `@services/utils/erros_formulario` → `LeitorDeFormulario` e `TradutorDeRecusa`: POST cru vira DTO
  ou recusa já traduzida por controle.
- `@apps/user_admin/formularios.py` → `FORMULARIO_SERVIDOR`: catálogo único dos controles das duas
  telas.
- `@apps/competencias/consulta.py` → `alcance_do_perfil`: as unidades que o perfil alcança.
- `@apps/user_admin/context.py` → `_catalogo_de_unidades`: recorte do select por ids permitidos.
- `@apps/user_admin/ficticios.py` → `remover_servidores_ficticios`: remoção pela faixa de RF reservada.
- `@apps/user_admin/titularidade.py` → `definir_titular`: marca o titular da unidade.
- `@apps/user_admin/management/commands/servidores_ficticios.py` → o formato de comando fino do app.
- Skills: `erros-de-formulario`, `escrever-testes`, `management-commands`.

## 6 · Snippets

O comentário abaixo é didático e **não é portado**: no código de produção vale o §7.2 do CLAUDE.md.

### O catálogo de recusas precisa conhecer dois tipos novos

**`services/utils/erros_formulario/regras.py`**
```python
REGRAS_PADRAO: Mapping[str, RegraDeErro] = {
    "missing": RegraDeErro(mensagem="Preencha o campo {rotulo}."),
    "string_too_short": RegraDeErro(
        mensagem="Preencha o campo {rotulo} com a quantidade mínima de caracteres."
    ),
    "string_too_long": RegraDeErro(mensagem="{rotulo}: texto longo demais."),
    # Campo com BeforeValidator sai da validação de string do Pydantic e erra por comprimento
    # GENÉRICO: sem estes dois, "preencha o RF" vira "valor inválido" no dia em que o campo ganha
    # normalização.
    "too_short": RegraDeErro(mensagem="Preencha o campo {rotulo}."),
    "too_long": RegraDeErro(mensagem="{rotulo}: texto longo demais."),
    "int_parsing": RegraDeErro(mensagem="{rotulo}: escolha uma opção da lista."),
    "value_error": RegraDeErro(mensagem="{rotulo}: valor inválido."),
}
```

### Cada formato erra com a frase do seu campo

**`apps/user_admin/formularios.py`**
```python
FORMULARIO_SERVIDOR = Formulario(
    campos=(
        CampoDeFormulario(
            controle="rf",
            rotulo="RF",
            # string_pattern_mismatch é UM tipo para todos os campos com formato: é aqui, por
            # controle, que ele vira a frase que ensina o formato daquele campo.
            regras={
                "string_pattern_mismatch": RegraDeErro(
                    mensagem="RF: sete dígitos, com ou sem pontuação (812.345-6)."
                )
            },
        ),
        CampoDeFormulario(
            controle="nome",
            rotulo="Nome",
            regras={
                "string_pattern_mismatch": RegraDeErro(
                    mensagem="Nome: só letras, espaço, hífen e apóstrofo."
                )
            },
        ),
        CampoDeFormulario(
            controle="sobrenome",
            rotulo="Sobrenome",
            regras={
                "string_pattern_mismatch": RegraDeErro(
                    mensagem="Sobrenome: só letras, espaço, hífen e apóstrofo."
                )
            },
        ),
        CampoDeFormulario(
            controle="email",
            rotulo="E-mail",
            regras={"value_error": RegraDeErro(mensagem="E-mail inválido: confira o endereço.")},
        ),
        CampoDeFormulario(controle="unidade", rotulo="Unidade"),
        CampoDeFormulario(controle="cargo_base", rotulo="Cargo base"),
        CampoDeFormulario(controle="cargo_comissao", rotulo="Cargo em comissão"),
        # A foto não vinha no catálogo porque nada a recusava; agora duas coisas recusam.
        CampoDeFormulario(controle="foto", rotulo="Foto"),
    )
)
```

### A foto é conferida antes de virar arquivo no disco

**`apps/user_admin/foto.py`**
```python
LIMITE_BYTES = 2 * 1024 * 1024
ERRO_TAMANHO = "Foto acima de 2 MB: envie uma imagem menor."
ERRO_FORMATO = "O arquivo enviado não é uma imagem."


def conferir_foto(foto: UploadedFile | None) -> ErroBruto | None:
    """Sem foto nova não há nada a conferir — é o caso mais comum da edição.

    O ImageField do model NÃO confere conteúdo: quem confere no Django é o field de FORMULÁRIO, que
    este projeto não usa. Sem esta função, um arquivo de texto chamado `retrato.png` é gravado."""
    if foto is None:
        return None
    if foto.size > LIMITE_BYTES:
        return ErroBruto(controle="foto", tipo="tamanho", mensagem=ERRO_TAMANHO)
    if not _e_imagem(foto):
        return ErroBruto(controle="foto", tipo="formato", mensagem=ERRO_FORMATO)
    return None


def _e_imagem(foto: UploadedFile) -> bool:
    """`verify()` lê o cabeçalho e deixa o arquivo consumido: o seek devolve o ponteiro para quem
    vai gravar depois."""
    try:
        Image.open(foto).verify()
    except (UnidentifiedImageError, OSError):
        return False
    finally:
        foto.seek(0)
    return True
```

### A política do ato é uma só, e os dois atos a aplicam

**`apps/user_admin/cadastro.py`**
```python
def _recusa_de_politica(email: str, foto: UploadedFile | None) -> RecusaDeFormulario | None:
    """O que o DTO não pode conferir: o domínio institucional depende de settings, e a foto é um
    objeto de upload do Django. Nenhum dos dois desce para o model — gravar pelo shell, pelo
    createsuperuser ou por um comando continua livre."""
    erros = tuple(
        erro
        for erro in (_erro_de_dominio(email), conferir_foto(foto))
        if erro is not None
    )
    return traduzir_recusa(erros) if erros else None


def _erro_de_dominio(email: str) -> ErroBruto | None:
    # `tipo` fora de REGRAS_PADRAO de propósito: a mensagem já vem escrita e vence o catálogo.
    if not _dominio_recusado(email):
        return None
    return ErroBruto(controle="email", tipo="dominio", mensagem=ERRO_DOMINIO)


def criar_servidor(valores, foto=None) -> DesfechoCadastro:
    leitura = ler_novo_servidor(valores)
    novo = leitura.dto
    if novo is None:
        return DesfechoCadastro(perfil=None, recusa=leitura.recusa or RecusaDeFormulario())
    recusa = _recusa_de_politica(novo.email, foto)
    if recusa is not None:
        return DesfechoCadastro(perfil=None, recusa=recusa)
    ...


def editar_servidor(valores, foto=None) -> DesfechoCadastro:
    leitura = ler_edicao_servidor(valores)
    edicao = leitura.dto
    if edicao is None:
        return DesfechoCadastro(perfil=None, recusa=leitura.recusa or RecusaDeFormulario())
    # A MESMA linha da criação: é a ausência dela aqui que deixava a edição gravar @gmail.com.
    recusa = _recusa_de_politica(edicao.email, foto)
    if recusa is not None:
        return DesfechoCadastro(perfil=None, recusa=recusa)
    perfil = get_object_or_404(Perfil, pk=edicao.servidor_id)
    ...
```

### Os dois catálogos de unidade são recortados, e não só o do select de lotação

**`apps/user_admin/context.py`**
```python
def contexto_modal_perfil(
    perfil: Perfil,
    ids_permitidos: Collection[int],
    valores: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    # O painel de nova unidade e o select de lotação dividem a chave "unidades": recortar um só não
    # recorta nada — quem vencesse o merge decidiria o que a tela oferece. Recortados os dois na
    # fonte, a ordem do merge deixa de ser regra escondida.
    return (
        _contexto_do_modal_de_unidade(ids_permitidos)
        | _catalogos_de_lotacao(ids_permitidos)
        | {
            "perfil": perfil,
            "valores": valores if valores is not None else _valores_do_perfil(perfil),
            "imagem": _imagem_do_perfil(perfil),
            "cor_unidade_hex": hex_da_cor(perfil.cor_unidade),
        }
    )


def contexto_criar_perfil(ids_permitidos: Collection[int]) -> dict[str, Any]:
    # O mesmo painel, na tela de criação: o recorte desce pelos dois caminhos aqui também.
    return (
        contexto_fundo_admin()
        | _contexto_do_modal_de_unidade(ids_permitidos)
        | _catalogos_de_lotacao(ids_permitidos)
    )


def _contexto_do_modal_de_unidade(
    ids_permitidos: Collection[int] | None = None,
) -> dict[str, Any]:
    return _catalogos_de_unidade(ids_permitidos) | contexto_cor_sugerida(None)


def _catalogos_de_unidade(ids_permitidos: Collection[int] | None = None) -> dict[str, Any]:
    return _catalogo_de_unidades(ids_permitidos) | {
        "tipos_unidade": TipoUnidade.objects.order_by("-nivel", "nome"),
        # Raiz não tem pai e por isso não está no alcance de ninguém. Quem chama sem recorte — a
        # página de cadastro de unidade (SPEC user_admin/012) — continua oferecendo.
        "permite_raiz": ids_permitidos is None,
    }


def contexto_edicao_recusada(
    perfil: Perfil,
    ids_permitidos: Collection[int],
    valores: Mapping[str, Any],
    recusa: RecusaDeFormulario,
) -> dict[str, Any]:
    return contexto_modal_perfil(perfil, ids_permitidos, _valores_do_formulario(valores)) | {
        "erros": recusa.mensagens,
        "realce": recusa.realce,
    }
```

**`templates/user_admin/partials/_campos_unidade.html`**
```html
{# Chave ausente é falso: painel incluído sem recorte declarado não oferece raiz. #}
{% if permite_raiz %}<option value="">— sem unidade superior (raiz) —</option>{% endif %}
```

**`apps/user_admin/views.py`**
```python
@acao_protegida(ACAO_EDITAR_SERVIDOR)
def editar_perfil(request: HttpRequest, servidor: int) -> HttpResponse:
    # Oferecer o que o decorator vai recusar no POST é convidar ao 403 — que o HTMX não troca na
    # tela. A lista sai do mesmo alcance que a barreira confere, como em `criar_perfil`.
    return render(
        request,
        TEMPLATE_MODAL_PERFIL,
        contexto_modal_perfil(_perfil(servidor), alcance_do_perfil(_autor(request))),
    )
```

### O controle da foto passa a poder ser realçado

**`templates/user_admin/partials/_campo_upload_foto.html`** e o bloco de foto de
**`_modal_editar_perfil.html`**
```html
<input type="file" name="foto" accept="image/*"
       class="file-input file-input-glass file-input-sm max-w-xs {{ realce.foto }}" />
```

### O superusuário é um servidor completo, não um esqueleto

`createsuperuser` preenche só `rf`, `nome` e `sobrenome`; `unidade` e `cargo_base` são obrigatórios
e não estão em `REQUIRED_FIELDS`, então o `save()` estoura no banco. Este é o caminho que produz um
Perfil gravável.

**`apps/user_admin/superusuario.py`**
```python
def criar_superusuario(novo: NovoSuperusuario, senha: SecretStr) -> Perfil:
    """Um ato só: sem unidade, cargo ou compatibilidade de titularidade, nada é gravado."""
    with transaction.atomic():
        perfil = Perfil(
            rf=novo.rf,
            nome=novo.nome,
            sobrenome=novo.sobrenome,
            email=novo.email,
            unidade=_unidade(novo.unidade_sigla),
            cargo_base=_cargo_base(novo.cargo_base_sigla),
            cargo_comissao=_cargo_comissao(novo.cargo_comissao_nome),
            is_staff=True,
            is_superuser=True,
        )
        perfil.set_password(senha.get_secret_value())
        perfil.full_clean(exclude=["password"])
        perfil.save()
        if novo.e_titular:
            # Depois do save: `definir_titular` cruza cargo → unidade → tipo e precisa da linha.
            definir_titular(perfil)
    return perfil
```

**`apps/user_admin/management/commands/criar_superusuario.py`**
```python
class Command(BaseCommand):
    help = "Cria um superusuário com lotação, cargos e, opcionalmente, titularidade da unidade."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--rf", required=True)
        parser.add_argument("--nome", required=True)
        parser.add_argument("--sobrenome", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--unidade", default=UNIDADE_PADRAO, help="sigla da unidade de lotação.")
        parser.add_argument("--cargo-base", default=CARGO_BASE_PADRAO, help="sigla do cargo base.")
        parser.add_argument("--cargo-comissao", default=CARGO_COMISSAO_PADRAO)
        parser.add_argument("--titular", action="store_true", help="marca como titular da unidade.")

    def handle(self, *args: object, **options: object) -> None:
        # A senha nunca vem por argumento: linha de comando fica no histórico do shell.
        senha = SecretStr(getpass("Senha: "))
        try:
            perfil = criar_superusuario(_dto(options), senha)
        except (ObjectDoesNotExist, ValidationError) as exc:
            raise CommandError(f"superusuário não criado: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"superusuário {perfil.rf} criado."))
```

### A faixa fictícia passa a sete dígitos

**`apps/user_admin/ficticios.py`**
```python
# Longe de qualquer RF real: sete dígitos altos que a Prefeitura não emite.
RF_INICIAL_FICTICIO = 9999000
```

### Sequência de aplicação — uma vez, no banco de desenvolvimento

A ordem não é livre: `remover_servidores_ficticios` apaga por `rf__in=FAIXA_RF_FICTICIA`, e trocar a
constante antes de rodar o `--remover` deixa os vinte fictícios de seis dígitos órfãos, fora do
alcance do único comando que sabe removê-los.

```bash
# 1. AINDA com a faixa de seis dígitos no código: é ela que casa com o que está gravado.
uv run python manage.py servidores_ficticios --remover

# 2. Trocar RF_INICIAL_FICTICIO para 9999000 (o snippet acima).

# 3. Os demais perfis, incluindo o superusuário antigo. Impedimento sai primeiro: Substituicao
#    protege o substituto com PROTECT, e a cascata do impedimento é que solta esse vínculo.
#    ExecucaoAcao.perfil é SET_NULL — o registro dos atos praticados sobrevive à limpeza.
uv run python manage.py shell -c "
from apps.user_admin.models import Impedimento, Perfil
Impedimento.objects.all().delete()
print(Perfil.objects.all().delete())
"

# 4. O superusuário novo, titular da DIMAP. 'Diretor de Divisão' é nível 4 e o tipo Divisão exige
#    nível mínimo 4: é o cargo que titulariza.
uv run python manage.py criar_superusuario \
  --rf 8123456 --nome Henrique --sobrenome Pougy \
  --email henrique@prefeitura.sp.gov.br \
  --unidade DIMAP --cargo-base AFTM --cargo-comissao "Diretor de Divisão" --titular

# 5. A faixa fictícia nova.
uv run python manage.py servidores_ficticios
```

## 7 · Caveats
O formato de RF e de nome vive nos DTOs, não no model. É a mesma escolha que a política de e-mail
institucional já fez: gravar pelo shell, por um comando ou por uma seed continua livre, e a regra
não vira migração de schema. O custo é que um RF de seis dígitos já gravado por fora só é recusado
quando alguém abre aquele cadastro na tela de edição — e aí a correção do RF é exigida junto com o
que a pessoa queria mudar.

O sétimo dígito é exigido como dígito, não conferido como verificador. Não há algoritmo público
confiável para o DV do RF da Prefeitura, e inventar um recusaria RF legítimo. O custo é que
`8123459` com DV errado é aceito como se fosse válido.

`criar_superusuario` remonta o `Perfil` que `criar_servidor` já monta. `criar_servidor` exige
`url_acesso` e entrega a senha por SMTP dentro da transação, o que não existe em linha de comando —
compartilhar o ato obrigaria a inventar um modo "sem envio" dentro dele. O custo é que dois lugares
constroem `Perfil` e podem divergir no dia em que o cadastro ganhar campo novo.

O 403 do destino fora do alcance continua sem swap no HTMX. Com o select recortado, o caminho deixa
de existir na interface, e um POST que ainda o alcance é forjado ou disputa uma janela em que o
alcance mudou com o modal aberto. O custo é que nesses dois casos a tela congela sem dizer nada — a
negativa fica só no registro de execução.

`_campos_unidade.html` passa a decidir pelo contexto se oferece a opção de raiz, e o mesmo partial
serve o painel dos dois formulários de servidor e a página de cadastro de unidade. Um partial irmão
só para o painel duplicaria os cinco campos e a coreografia da cor sugerida. O custo é que uma tela
nova que o inclua sem declarar `permite_raiz` esconde a opção em silêncio, sem nada acusar.

A foto é lida duas vezes: uma pelo `verify()`, outra pela gravação. Ler uma vez exigiria segurar o
arquivo inteiro em memória para reaproveitá-lo. O custo é um seek e uma releitura por upload, em
arquivo que já está limitado a 2 MB.

## 8 · Testes (TDD)

**Comportamento dos tipos** — `tests/apps/user_admin/test_schemas.py`, sem marker:

- `test_rf_normaliza_pontuacao_e_recusa_fora_do_formato` — `812.345-6`, `812345-6` e `8123456`
  produzem o mesmo `8123456`; seis dígitos, oito dígitos e texto sem dígito não constroem o DTO.
- `test_nome_de_gente_passa_e_o_resto_nao` — `Ana d'Ávila`, `Silva-Santos` e `José` passam;
  `12345`, `Ana2` e `Nogueira Jr.` não.
- `test_espacos_do_nome_sao_aparados_e_colapsados` — `"  Ana   Maria  "` vira `"Ana Maria"`.
- `test_email_e_normalizado_em_caixa_baixa` — `ANA@Prefeitura.SP.gov.BR` vira
  `ana@prefeitura.sp.gov.br`.
- `test_campo_em_branco_erra_por_obrigatoriedade` — RF e nome vazios erram como comprimento, não
  como formato, e o catálogo os traduz em "preencha".

**Contrato das telas** — `tests/apps/user_admin/views/`, marker `banco`:

- `test_recusa_de_formato_volta_realcada_no_controle_certo` — RF de seis dígitos e nome numérico
  voltam 422 no formulário e no modal, cada frase no seu controle, sem gravar.
- `test_edicao_recusa_email_nao_institucional` — a edição recusa `@gmail.com` com a mesma frase da
  criação, e o cadastro segue como estava.
- `test_foto_invalida_e_recusada_sem_gravar_o_cadastro` — arquivo que não é imagem e arquivo acima
  de 2 MB voltam 422, e nem a foto nem os demais campos mudam.
- `test_selects_de_unidade_so_oferecem_o_alcance` — no modal de edição e no formulário de criação,
  nem o select de lotação nem o de unidade superior do painel trazem unidade fora do alcance de quem
  preenche, e o painel não traz a opção de raiz — que a página de cadastro de unidade continua
  trazendo.

**Comando** — `tests/apps/user_admin/test_superusuario.py`, marker `banco`:

- `test_superusuario_nasce_lotado_e_titular` — o comando grava um `Perfil` com unidade, cargos,
  `is_superuser` e a titularidade da unidade pedida.
