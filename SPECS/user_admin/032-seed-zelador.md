---
spec: user_admin/032
versao: v1
atualizado_em: 2026-10-07
testes_tdd: false
implementado: false
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
---

# SPEC user_admin/032 — Seed do zelador: o administrador de bootstrap

## 1 · User story
Quem implanta a plataforma sobe o sistema sobre um banco sem administrador no contexto de um deploy
para obter um servidor com plenos poderes com que entrar e cadastrar os demais.

## 2 · Condições de pronto
- [ ] Subir o sistema sobre um banco **sem administrador** deixa cadastrado o **zelador**: RF de
      `ADMIN_RF` (`0000000` por padrão), e-mail de `ADMIN_EMAIL`, administrador, lotado em `SF-GAB`,
      cargo base `AFTM`, cargo em comissão `Assessor IV`, não titular.
- [ ] O zelador **entra pelo primeiro acesso** com a senha de `ADMIN_SENHA_INICIAL` e é levado a
      definir a senha definitiva.
- [ ] **Subir de novo não cria um segundo zelador nem reescreve o primeiro**: senha já trocada e
      dados editados pela tela sobrevivem, mesmo com o arquivo da seed ou as variáveis alterados.
- [ ] Havendo **qualquer administrador** no banco, o zelador não é criado — com ou sem as variáveis
      `ADMIN_*` configuradas — e o log diz que já existe administrador e que a criação foi pulada.
- [ ] **Toda execução diz no log o que aconteceu**: zelador criado (com o RF), criação pulada por
      já haver administrador, ou — como erro — sistema sem administrador e por quê.
- [ ] Precisando criar e **sem `ADMIN_EMAIL` ou sem `ADMIN_SENHA_INICIAL`**, nada é gravado, o log
      traz uma **mensagem de erro** dizendo que o sistema está sem administrador e o que definir, e
      a subida segue.
- [ ] Precisando criar e com o RF de `ADMIN_RF` **já ocupado por outro servidor** (o zelador
      exonerado), nada é gravado, o log traz uma **mensagem de erro** dizendo que o sistema está
      sem administrador e que o RF está em uso, e a subida segue.
- [ ] `ADMIN_RF` ou `ADMIN_EMAIL` fora do formato, unidade ou cargo do zelador ausente do banco, ou
      e-mail já usado por outro servidor **abortam a carga sem gravar nada**, com erro legível no
      console.
- [ ] `--dry-run` percorre a criação inteira e não persiste nada.
- [ ] A subida do container roda a seed do zelador **depois** das de unidades e de cargos.

## 3 · Domínio
O zelador não é entidade nova: é um servidor administrador, e o que o descreve é o
`NovoSuperusuario` de [criacao_usuarios/006](../criacao_usuarios/006-enforcement-do-cadastro-de-servidor.md),
que entrega `criar_superusuario`. A pergunta desta SPEC a ele: **como nasce um administrador
completo sem ninguém ao teclado?** O modelo é alterado e passa a valer na forma abaixo.

**`apps/user_admin/schemas.py`**
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
    # ALTERADO nesta SPEC: campo novo. True = a senha informada vale só para o primeiro acesso.
    senha_provisoria: bool = False
```

O `NovoSuperusuario` do zelador nasce de duas metades: a identidade de acesso, que é do ambiente, e
o cadastro funcional, que é do arquivo versionado.

**`apps/user_admin/seeds/zelador.py`**
```python
class CredencialAdmin(BaseModel):
    """O que o ambiente diz do administrador de bootstrap. Texto cru: quem dá forma ao RF e ao
    e-mail é o `NovoSuperusuario`, e só quando há o que criar."""

    model_config = ConfigDict(frozen=True)

    rf: str
    # Vazio = não configurado.
    email: str
    # Vazia = não configurada.
    senha: SecretStr


class CadastroZelador(BaseModel):
    """A metade do `NovoSuperusuario` que o arquivo versionado carrega."""

    nome: NomeDePessoa
    sobrenome: SobrenomeDePessoa
    unidade_sigla: str
    cargo_base_sigla: str
    cargo_comissao_nome: str
    senha_provisoria: bool


class ArquivoSeedZelador(BaseModel):
    zelador: CadastroZelador


class DesfechoZelador(StrEnum):
    CRIADO = "criado"
    # Já há administrador no banco.
    DISPENSADO = "dispensado"
    # Era preciso criar e faltou e-mail ou senha no ambiente.
    SEM_CREDENCIAL = "sem_credencial"
    # Era preciso criar e o RF configurado já pertence a outro servidor.
    RF_OCUPADO = "rf_ocupado"


class ResultadoSeedZelador(BaseModel):
    desfecho: DesfechoZelador
```

**`data/seed/zelador.json`**
```json
{
  "zelador": {
    "nome": "Zelador",
    "sobrenome": "do Sistema",
    "unidade_sigla": "SF-GAB",
    "cargo_base_sigla": "AFTM",
    "cargo_comissao_nome": "Assessor IV",
    "senha_provisoria": true
  }
}
```

A unidade e os cargos nomeados vêm das seeds de [user_admin/008](008-seed-unidades.md) e
[user_admin/009](009-seed-cargos.md). O primeiro acesso com senha provisória é o de
[autenticacao/001](../autenticacao/001-login-e-primeiro-acesso.md).

## 4 · Fora de escopo
- Propagar para o zelador já criado uma edição de `data/seed/zelador.json` ou das variáveis
  `ADMIN_*` — sem dono; a seed só cria.
- Aposentar o zelador quando o primeiro administrador real é nomeado — sem dono; é ato de exoneração
  feito pela tela ([user_admin/027](027-exoneracao-de-servidor.md)).
- Recusar o reenvio da senha de uso único em tela para administrador com o envio de e-mail
  desligado — épico `autenticacao`, sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/user_admin/superusuario.py` → `criar_superusuario`: monta e grava o `Perfil` completo, com
  senha hasheada, em transação.
- `@apps/user_admin/schemas.py` → `RegistroFuncional`, `NomeDePessoa`, `SobrenomeDePessoa`,
  `EmailDeServidor`: a forma dos campos de identificação.
- `@apps/user_admin/seeds/tipos_impedimento.py` → padrão de carga: DTO do arquivo, `atomic()` único,
  `dry_run` por rollback.
- `@apps/user_admin/management/commands/seed_unidades.py` → comando fino de seed com a fronteira de
  erro (`CommandError`).
- `@services/utils/io` → `subpasta_de_data`, `read_json_from_folder`: leitura de `data/seed/`.
- `@tests/apps/user_admin/test_superusuario.py` → builders de unidade e cargos para teste de
  superusuário.
- Skills: `seeds`, `management-commands`, `escrever-testes`.

## 6 · Snippets
Os comentários abaixo são didáticos e **não são portados**: no código vale o §7.2 do CLAUDE.md.

**`apps/user_admin/seeds/zelador.py`**
```python
NOME_SUBPASTA_SEED = "seed"
NOME_ARQUIVO_SEED = "zelador.json"


def carregar_seed_zelador(admin: CredencialAdmin, *, dry_run: bool = False) -> ResultadoSeedZelador:
    # A ordem das guardas é a regra. Primeiro a que não depende de configuração: quem já tem
    # administrador nunca é cobrado pelas variáveis, e pode tirá-las do .env depois da primeira
    # subida sem ganhar erro — nem de falta, nem de formato — a cada boot.
    if Perfil.objects.filter(is_superuser=True).exists():
        return ResultadoSeedZelador(desfecho=DesfechoZelador.DISPENSADO)
    if not admin.email or not admin.senha.get_secret_value():
        return ResultadoSeedZelador(desfecho=DesfechoZelador.SEM_CREDENCIAL)
    novo = _novo_superusuario(admin)
    # Pelo RF já normalizado (`000.000-0` e `0000000` são o mesmo servidor). A exoneração tira o
    # `is_superuser`: zelador exonerado deixa o banco "sem administrador" e com o RF ocupado, e
    # recriá-lo estouraria o `unique` na subida.
    if Perfil.objects.filter(rf=novo.rf).exists():
        return ResultadoSeedZelador(desfecho=DesfechoZelador.RF_OCUPADO)
    with transaction.atomic():
        criar_superusuario(novo, admin.senha)
        if dry_run:
            transaction.set_rollback(True)
    return ResultadoSeedZelador(desfecho=DesfechoZelador.CRIADO)


def _novo_superusuario(admin: CredencialAdmin) -> NovoSuperusuario:
    pasta = subpasta_de_data(NOME_SUBPASTA_SEED)
    dados = read_json_from_folder(pasta, NOME_ARQUIVO_SEED)
    cadastro = ArquivoSeedZelador.model_validate(dados).zelador
    # É aqui que RF e e-mail do ambiente ganham forma: fora do formato, o Pydantic recusa.
    return NovoSuperusuario(
        rf=admin.rf,
        email=admin.email,
        **cadastro.model_dump(),
    )
```

**`apps/user_admin/superusuario.py`** — uma linha a mais no `Perfil(...)` que já existe:
```python
        perfil = Perfil(
            ...
            is_staff=True,
            is_superuser=True,
            senha_provisoria=novo.senha_provisoria,
        )
```

**`apps/user_admin/management/commands/seed_zelador.py`**
```python
ADMIN_RF: str = settings.ADMIN_RF
ADMIN_EMAIL: str = settings.ADMIN_EMAIL
ADMIN_SENHA_INICIAL: SecretStr = settings.ADMIN_SENHA_INICIAL

# Uma frase por desfecho, sempre impressa: quem lê o log da subida sabe o que a seed fez sem abrir
# o banco.
MENSAGENS: dict[DesfechoZelador, str] = {
    DesfechoZelador.CRIADO: "nenhum administrador encontrado: zelador criado com o RF {rf}.",
    DesfechoZelador.DISPENSADO: "administrador já existe: criação do zelador pulada.",
    DesfechoZelador.SEM_CREDENCIAL: (
        "ERRO: nenhum administrador encontrado e zelador NÃO criado. "
        "Defina ADMIN_EMAIL e ADMIN_SENHA_INICIAL e suba de novo."
    ),
    DesfechoZelador.RF_OCUPADO: (
        "ERRO: nenhum administrador encontrado e zelador NÃO criado: o RF {rf} já pertence a um "
        "servidor. Mude ADMIN_RF ou use criar_superusuario."
    ),
}
# Os dois desfechos em que o sistema segue sem administrador são erro para quem lê o log, mas não
# para o processo: saem em estilo de erro, no stderr, e o comando termina com código de saída zero —
# `CommandError` faria o `set -e` do entrypoint derrubar a subida.
ERROS = frozenset({DesfechoZelador.SEM_CREDENCIAL, DesfechoZelador.RF_OCUPADO})


class Command(BaseCommand):
    help = "Cria o zelador de data/seed/zelador.json quando o sistema não tem administrador."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="valida a criação completa sem persistir nada.",
        )

    def handle(self, *args: object, **options: object) -> None:
        admin = CredencialAdmin(
            rf=ADMIN_RF,
            email=ADMIN_EMAIL,
            senha=ADMIN_SENHA_INICIAL,
        )
        try:
            resultado = carregar_seed_zelador(admin, dry_run=bool(options["dry_run"]))
        # ObjectDoesNotExist: unidade ou cargo fora do banco. ValidationError do Django: e-mail em
        # uso. ValidationError do Pydantic: ADMIN_RF ou ADMIN_EMAIL fora do formato.
        except (ObjectDoesNotExist, ValidationError, PydanticValidationError) as exc:
            raise CommandError(f"carga abortada: {exc}") from exc
        mensagem = MENSAGENS[resultado.desfecho].format(rf=ADMIN_RF)
        if resultado.desfecho in ERROS:
            self.stderr.write(self.style.ERROR(mensagem))
            return
        self.stdout.write(self.style.SUCCESS(mensagem))
```

**`config/settings.py`**
```python
    # em _Settings
    admin_rf: str = Field(default="0000000", alias="ADMIN_RF")
    admin_email: str = Field(default="", alias="ADMIN_EMAIL")
    admin_senha_inicial: SecretStr = Field(default=SecretStr(""), alias="ADMIN_SENHA_INICIAL")

# Administrador de bootstrap, o zelador (apps.user_admin.seeds.zelador); e-mail ou senha vazios =
# seed não cria.
ADMIN_RF = _env.admin_rf
ADMIN_EMAIL = _env.admin_email
ADMIN_SENHA_INICIAL = _env.admin_senha_inicial
```

**`.env.example`**
```bash
# Administrador de bootstrap (o "zelador"), criado na subida quando o banco não tem administrador.
# Sem e-mail ou sem senha a seed não cria ninguém e avisa no log. A senha vale só até o primeiro
# acesso.
ADMIN_RF=0000000
ADMIN_EMAIL=
ADMIN_SENHA_INICIAL=
```

**`docker/run_seeds.sh`** — última etapa, depois das três que existem:
```sh
echo "==> Verificando administrador do sistema..."
python manage.py seed_zelador
```

## 7 · Caveats
**RF previsível com senha provisória.** O zelador nasce em primeiro acesso, e o reenvio da senha de
uso único atende quem informa o RF sem estar autenticado; a razão é reusar o fluxo de troca
obrigatória que já existe em vez de criar outro. Com `EMAIL_ENVIO_HABILITADO=0` esse reenvio exibe a
senha nova na tela, então, do deploy até o primeiro login do zelador, quem digitar o RF de
`ADMIN_RF` — `0000000` em todo deploy que não o trocar — obtém a credencial de um administrador.

**O e-mail do zelador ocupa a unicidade.** `ADMIN_EMAIL` aponta para a caixa de uma pessoa real,
porque é por ela que a senha de uso único e a recuperação chegam. O dono da caixa não consegue
cadastrar o próprio servidor com esse endereço enquanto o zelador o detiver.

**A carga recebe a credencial por parâmetro.** `carregar_seed_zelador` foge da assinatura
`carregar_seed_<nome>(*, dry_run)` da skill `seeds`, porque quem lê `settings` é o comando e RF,
e-mail e senha não moram em `data/`. O custo é uma seed cuja chamada não é idêntica à das demais.

**`CadastroZelador` repete campos do `NovoSuperusuario`.** O arquivo carrega só a metade que não vem
do ambiente, e essa metade precisa de um tipo para ser validada na leitura. Campo novo obrigatório
no `NovoSuperusuario` tem de ser acrescentado nos dois.

**A senha do ambiente não é validada.** `ADMIN_SENHA_INICIAL` não passa pelos validadores de senha
do Django, porque vale só até o primeiro acesso. Até lá, a força da credencial de um administrador é
a que quem escreveu o `.env` escolheu.

**Deploy pode subir sem administrador.** Sem e-mail, sem senha ou com o RF ocupado a seed não cria
nada e não derruba a subida, para que as variáveis sigam opcionais onde já há administrador. O único
sinal de que o sistema ficou sem ninguém que o administre é uma linha de erro no log do container.

**"Sempre há um administrador" não é invariante.** A seed pergunta só na subida e nunca recria o
zelador sobre o RF ocupado, porque a alternativa seria reativar um servidor exonerado por um ato
automático. Se o último administrador perder a marca depois de o zelador ter sido exonerado, a
subida só devolve um com `ADMIN_RF` trocado — ou pelo comando `criar_superusuario`.

**Servidor fictício no quadro.** O zelador é um `Perfil` como outro qualquer, lotado em `SF-GAB`,
porque o model não distingue conta de serviço de servidor. Ele aparece nas listagens e na página da
unidade até ser exonerado.

## 8 · Testes (TDD)
`tests/apps/user_admin/test_seed_zelador.py`, exercitando `carregar_seed_zelador`. Todos com o marker
`banco`, exceto o último.

- `test_banco_sem_administrador_ganha_zelador` — banco com unidade e cargos e nenhum administrador:
  o desfecho é `CRIADO` e o perfil tem o RF e o e-mail da credencial, é administrador, lotado e com
  os cargos do arquivo, não titular e em senha provisória. *(marker `banco`)*
- `test_zelador_entra_pelo_primeiro_acesso` — `autenticar_primeiro_login` com o RF e a senha da
  credencial devolve o zelador. *(marker `banco`)*
- `test_segunda_carga_nao_duplica_nem_reescreve` — depois da primeira carga a senha é trocada, o
  arquivo é reescrito com outro sobrenome e a credencial muda de e-mail; a segunda carga devolve
  `DISPENSADO`, segue havendo um perfil só, com o sobrenome, o e-mail e a senha de antes dela.
  *(marker `banco`)*
- `test_administrador_existente_dispensa_zelador_mesmo_sem_credencial` — com outro administrador no
  banco e e-mail e senha vazios, o desfecho é `DISPENSADO`, não `SEM_CREDENCIAL`, e nenhum perfil é
  criado. *(marker `banco`)*
- `test_sem_email_ou_sem_senha_nao_cria` — sem administrador, com o e-mail vazio e depois com a
  senha vazia: desfecho `SEM_CREDENCIAL` nos dois e nenhum perfil gravado. *(marker `banco`)*
- `test_rf_ocupado_nao_cria_e_nao_estoura` — RF da credencial pertencendo a um servidor exonerado e
  nenhum administrador: o desfecho é `RF_OCUPADO`, sem exceção e sem segundo perfil.
  *(marker `banco`)*
- `test_rf_fora_do_formato_aborta_sem_gravar_nada` — credencial com RF de cinco dígitos: a carga
  levanta o `ValidationError` do Pydantic e nenhum perfil fica no banco. *(marker `banco`)*
- `test_unidade_ausente_aborta_sem_gravar_nada` — arquivo nomeando sigla que não existe: a carga
  levanta `ObjectDoesNotExist` e nenhum perfil fica no banco. *(marker `banco`)*
- `test_dry_run_nao_persiste` — mesmo cenário do primeiro teste com `dry_run=True`: desfecho
  `CRIADO` e nenhum perfil gravado. *(marker `banco`)*
- `test_run_seeds_chama_zelador_depois_de_unidades_e_cargos` — em `docker/run_seeds.sh`, a linha de
  `seed_zelador` vem depois das de `seed_unidades` e `seed_cargos`.
