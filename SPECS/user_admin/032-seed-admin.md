---
spec: user_admin/032
versao: v2
atualizado_em: 2026-10-07
testes_tdd: true
implementado: true
markers_obrigatorios: [banco]
changelog:
  - v1: versão inicial
  - v2: `ADMIN_EMAIL` ganha default em `config/settings.py`, para o admin nascer também sem `.env`
---

# SPEC user_admin/032 — Seed do admin inicial

## 1 · User story
Quem implanta a plataforma sobe o sistema sobre um banco sem administrador no contexto de um deploy
para obter um servidor com plenos poderes com que entrar e cadastrar os demais.

## 2 · Condições de pronto
- [ ] Subir o sistema sobre um banco **sem administrador** deixa cadastrado o **admin**: RF de
      `ADMIN_RF` (`0000000` por padrão), e-mail de `ADMIN_EMAIL`, administrador, lotado em `SF-GAB`,
      cargo base `AFTM`, cargo em comissão `Assessor IV`, não titular — e o log diz que ele foi
      criado, com o RF, e como entrar.
- [ ] O admin inicial **entra sem senha configurada em lugar nenhum**: informa o RF, pede a senha de
      uso único na tela de primeiro acesso, recebe-a em `ADMIN_EMAIL` — ou na própria tela, com o
      envio de e-mail desligado — e é levado a definir a senha definitiva.
- [ ] Admin criado com o **envio de e-mail desligado** faz o log trazer, além da linha de criação,
      um **alerta em destaque, em estilo de erro**, dizendo que a senha de uso único aparece na tela
      para quem informar o RF; a subida segue.
- [ ] **Subir de novo não cria um segundo admin inicial nem reescreve o primeiro**: senha já
      definida e dados editados pela tela sobrevivem, mesmo com o arquivo da seed ou as variáveis
      alterados.
- [ ] Havendo **qualquer administrador** no banco, o admin inicial não é criado — com ou sem as
      variáveis `ADMIN_*` configuradas — e o log diz que já existe admin e que a criação foi pulada.
- [ ] Precisando criar e **sem `ADMIN_EMAIL`**, nada é gravado, o log traz uma **mensagem de erro**
      dizendo que o sistema está sem administrador e o que definir, e a subida segue.
- [ ] Precisando criar e com o RF de `ADMIN_RF` **já ocupado por outro servidor** (o admin inicial
      exonerado), nada é gravado, o log traz uma **mensagem de erro** dizendo que o sistema está
      sem administrador e que o RF está em uso, e a subida segue.
- [ ] `ADMIN_RF` ou `ADMIN_EMAIL` fora do formato, unidade ou cargo do admin inicial ausente do
      banco, ou e-mail já usado por outro servidor **abortam a carga sem gravar nada**, e o erro no
      console diz que foi a criação do admin inicial que falhou, e por quê.
- [ ] `--dry-run` percorre a criação inteira e não persiste nada.
- [ ] A subida do container roda a seed do admin inicial **depois** das de unidades e de cargos.

## 3 · Domínio
O admin inicial não é entidade nova: é um servidor administrador, e o que o descreve é o
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
    # ALTERADO nesta SPEC: campo novo. True = a senha gravada vale só para o primeiro acesso.
    senha_provisoria: bool = False
```

O `NovoSuperusuario` do admin inicial nasce de duas metades: a identidade de acesso, que é do
ambiente, e o cadastro funcional, que é do arquivo versionado. Senha não é metade nenhuma: ele nasce
em primeiro acesso, e quem lhe entrega a senha de uso único é o reenvio de
[autenticacao/004](../autenticacao/004-reenvio-da-senha-de-uso-unico.md).

**`apps/user_admin/seeds/admin.py`**
```python
class ConfiguracaoAdmin(BaseModel):
    """O que o ambiente diz do admin inicial. Texto cru: quem dá forma ao RF e ao e-mail é o
    `NovoSuperusuario`, e só quando há o que criar."""

    model_config = ConfigDict(frozen=True)

    rf: str
    # Vazio = não configurado.
    email: str
    # Desligado, a senha de uso único sai na tela em vez de ir para a caixa.
    envio_de_email_habilitado: bool


class CadastroAdmin(BaseModel):
    """A metade do `NovoSuperusuario` que o arquivo versionado carrega."""

    nome: NomeDePessoa
    sobrenome: SobrenomeDePessoa
    unidade_sigla: str
    cargo_base_sigla: str
    cargo_comissao_nome: str


class ArquivoSeedAdmin(BaseModel):
    admin: CadastroAdmin


class DesfechoAdmin(StrEnum):
    CRIADO = "criado"
    # Já há administrador no banco.
    DISPENSADO = "dispensado"
    # Era preciso criar e o e-mail não foi configurado.
    SEM_EMAIL = "sem_email"
    # Era preciso criar e o RF configurado já pertence a outro servidor.
    RF_OCUPADO = "rf_ocupado"


class ResultadoSeedAdmin(BaseModel):
    desfecho: DesfechoAdmin
    # True só em CRIADO: quem informar o RF na tela de primeiro acesso vê a senha de uso único.
    senha_sai_em_tela: bool = False
```

**`data/seed/admin.json`**
```json
{
  "admin": {
    "nome": "Admin",
    "sobrenome": "do Sistema",
    "unidade_sigla": "SF-GAB",
    "cargo_base_sigla": "AFTM",
    "cargo_comissao_nome": "Assessor IV"
  }
}
```

A unidade e os cargos nomeados vêm das seeds de [user_admin/008](008-seed-unidades.md) e
[user_admin/009](009-seed-cargos.md). O primeiro acesso com senha provisória é o de
[autenticacao/001](../autenticacao/001-login-e-primeiro-acesso.md).

## 4 · Fora de escopo
- Propagar para o admin inicial já criado uma edição de `data/seed/admin.json` ou das variáveis
  `ADMIN_*` — sem dono; a seed só cria.
- Aposentar o admin inicial quando o primeiro administrador real é nomeado — sem dono; é ato de
  exoneração feito pela tela ([user_admin/027](027-exoneracao-de-servidor.md)).
- Recusar o reenvio da senha de uso único em tela para administrador com o envio de e-mail
  desligado — épico `autenticacao`, sem dono ainda.

## 5 · Peças de referência a compor
- `@apps/user_admin/superusuario.py` → `criar_superusuario`: monta e grava o `Perfil` completo, com
  senha hasheada, em transação.
- `@apps/user_admin/schemas.py` → `RegistroFuncional`, `NomeDePessoa`, `SobrenomeDePessoa`,
  `EmailDeServidor`: a forma dos campos de identificação.
- `@services/utils/senha.py` → `gerar_senha_temporaria`: sorteia a senha de uso único.
- `@apps/autenticacao/reenvio.py` → `reenviar_senha_uso_unico`: emite e entrega a senha de uso único
  de quem está em primeiro acesso, por e-mail ou na tela.
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

**`apps/user_admin/seeds/admin.py`**
```python
NOME_SUBPASTA_SEED = "seed"
NOME_ARQUIVO_SEED = "admin.json"


def carregar_seed_admin(config: ConfiguracaoAdmin, *, dry_run: bool = False) -> ResultadoSeedAdmin:
    # A ordem das guardas é a regra. Primeiro a que não depende de configuração: quem já tem
    # administrador nunca é cobrado pelas variáveis, e pode tirá-las do .env depois da primeira
    # subida sem ganhar erro — nem de falta, nem de formato — a cada boot.
    if Perfil.objects.filter(is_superuser=True).exists():
        return ResultadoSeedAdmin(desfecho=DesfechoAdmin.DISPENSADO)
    # Sem e-mail o reenvio não atende o pedido: seria um administrador que ninguém consegue usar.
    if not config.email:
        return ResultadoSeedAdmin(desfecho=DesfechoAdmin.SEM_EMAIL)
    novo = _novo_superusuario(config)
    # Pelo RF já normalizado (`000.000-0` e `0000000` são o mesmo servidor). A exoneração tira o
    # `is_superuser`: admin inicial exonerado deixa o banco "sem administrador" e com o RF ocupado,
    # e recriá-lo estouraria o `unique` na subida.
    if Perfil.objects.filter(rf=novo.rf).exists():
        return ResultadoSeedAdmin(desfecho=DesfechoAdmin.RF_OCUPADO)
    with transaction.atomic():
        # Sorteada e descartada: ninguém conhece esta senha, nem a carga a devolve. Ela só ocupa
        # o campo até o reenvio do primeiro acesso emitir a que o admin vai de fato usar.
        criar_superusuario(novo, gerar_senha_temporaria())
        if dry_run:
            transaction.set_rollback(True)
    return ResultadoSeedAdmin(
        desfecho=DesfechoAdmin.CRIADO,
        senha_sai_em_tela=not config.envio_de_email_habilitado,
    )


def _novo_superusuario(config: ConfiguracaoAdmin) -> NovoSuperusuario:
    pasta = subpasta_de_data(NOME_SUBPASTA_SEED)
    dados = read_json_from_folder(pasta, NOME_ARQUIVO_SEED)
    cadastro = ArquivoSeedAdmin.model_validate(dados).admin
    # É aqui que RF e e-mail do ambiente ganham forma: fora do formato, o Pydantic recusa.
    return NovoSuperusuario(
        rf=config.rf,
        email=config.email,
        # Regra, não dado do arquivo: sem senha conhecida, o único caminho é o primeiro acesso.
        senha_provisoria=True,
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

**`apps/user_admin/management/commands/seed_admin.py`**
```python
ADMIN_RF: str = settings.ADMIN_RF
ADMIN_EMAIL: str = settings.ADMIN_EMAIL
EMAIL_ENVIO_HABILITADO: bool = settings.EMAIL_ENVIO_HABILITADO

# Uma frase por desfecho, sempre impressa: quem lê o log da subida sabe o que a seed fez sem abrir
# o banco.
MENSAGENS: dict[DesfechoAdmin, str] = {
    DesfechoAdmin.CRIADO: (
        "nenhum admin encontrado: admin criado com o RF {rf}. Para entrar, informe o RF na tela "
        "de login e peça a senha de uso único."
    ),
    DesfechoAdmin.DISPENSADO: "admin já existe: criação pulada.",
    DesfechoAdmin.SEM_EMAIL: (
        "ERRO: nenhum admin encontrado e admin NÃO criado. Defina ADMIN_EMAIL e suba de novo."
    ),
    DesfechoAdmin.RF_OCUPADO: (
        "ERRO: nenhum admin encontrado e admin NÃO criado: o RF {rf} já pertence a um "
        "servidor. Mude ADMIN_RF ou use criar_superusuario."
    ),
}
# Os dois desfechos em que o sistema segue sem administrador são erro para quem lê o log, mas não
# para o processo: saem em estilo de erro, no stderr, e o comando termina com código de saída zero —
# `CommandError` faria o `set -e` do entrypoint derrubar a subida.
ERROS = frozenset({DesfechoAdmin.SEM_EMAIL, DesfechoAdmin.RF_OCUPADO})
# Grande e em estilo de erro de propósito: é a única coisa que separa um deploy de produção de um
# administrador cuja senha qualquer visitante consegue ver.
ALERTA_SENHA_EM_TELA = (
    "\n"
    "############################################################################\n"
    "#  ATENÇÃO: ADMIN CRIADO COM O ENVIO DE E-MAIL DESLIGADO.                  #\n"
    "#  A SENHA DE USO ÚNICO APARECE NA TELA PARA QUEM INFORMAR O RF DO ADMIN.  #\n"
    "#  SE ISTO É PRODUÇÃO, LIGUE EMAIL_ENVIO_HABILITADO E FAÇA O PRIMEIRO      #\n"
    "#  ACESSO AGORA.                                                           #\n"
    "############################################################################\n"
)


class Command(BaseCommand):
    help = "Cria o admin inicial (data/seed/admin.json) quando o sistema não tem nenhum."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="valida a criação completa sem persistir nada.",
        )

    def handle(self, *args: object, **options: object) -> None:
        config = ConfiguracaoAdmin(
            rf=ADMIN_RF,
            email=ADMIN_EMAIL,
            envio_de_email_habilitado=EMAIL_ENVIO_HABILITADO,
        )
        try:
            resultado = carregar_seed_admin(config, dry_run=bool(options["dry_run"]))
        # ObjectDoesNotExist: unidade ou cargo fora do banco. ValidationError do Django: e-mail em
        # uso. ValidationError do Pydantic: ADMIN_RF ou ADMIN_EMAIL fora do formato.
        except (ObjectDoesNotExist, ValidationError, PydanticValidationError) as exc:
            # A frase nomeia o que falhou: no log da subida, "carga abortada" não diz de quê.
            raise CommandError(f"falha na criação do admin inicial: {exc}") from exc
        mensagem = MENSAGENS[resultado.desfecho].format(rf=ADMIN_RF)
        if resultado.desfecho in ERROS:
            self.stderr.write(self.style.ERROR(mensagem))
            return
        self.stdout.write(self.style.SUCCESS(mensagem))
        if resultado.senha_sai_em_tela:
            self.stderr.write(self.style.ERROR(ALERTA_SENHA_EM_TELA))
```

**`config/settings.py`**
```python
    # em _Settings
    admin_rf: str = Field(default="0000000", alias="ADMIN_RF")
    admin_email: str = Field(default="hpougy@sf.prefeitura.sp.gov.br", alias="ADMIN_EMAIL")

# Admin inicial do sistema (apps.user_admin.seeds.admin); e-mail vazio = seed não cria.
ADMIN_RF = _env.admin_rf
ADMIN_EMAIL = _env.admin_email
```

**`.env.example`**
```bash
# Admin inicial do sistema, criado na subida quando o banco não tem nenhum admin.
# Sem e-mail o admin não é criado e a subida registra erro no log.
# Não há senha aqui: no primeiro acesso, informe o RF e peça a senha de uso único. Ela vai para
# ADMIN_EMAIL — ou aparece na tela, com EMAIL_ENVIO_HABILITADO=0.
# ATENÇÃO: COM EMAIL_ENVIO_HABILITADO=0, QUEM INFORMAR O RF VÊ A SENHA DO ADMIN NA TELA.
# ISSO É SÓ PARA DESENVOLVIMENTO E HOMOLOGAÇÃO. EM PRODUÇÃO, LIGUE O ENVIO DE E-MAIL.
ADMIN_RF=0000000
ADMIN_EMAIL=hpougy@sf.prefeitura.sp.gov.br
```

**`docker/run_seeds.sh`** — última etapa, depois das três que existem:
```sh
echo "==> Verificando admin do sistema..."
python manage.py seed_admin
```

## 7 · Caveats
**A senha do admin inicial sai pelo reenvio.** A seed não define senha: o admin nasce em primeiro
acesso e obtém a de uso único pelo reenvio, que atende quem informa o RF sem estar autenticado; a
razão é reusar o fluxo que já existe em vez de pôr uma senha no ambiente. Com
`EMAIL_ENVIO_HABILITADO=0` esse reenvio exibe a senha na tela, então, do deploy até o primeiro acesso
do admin inicial, quem informar o RF de `ADMIN_RF` — `0000000` em todo deploy que não o trocar —
torna-se administrador, e a única defesa é o alerta no log da subida que o criou.

**O e-mail do admin inicial ocupa a unicidade.** `ADMIN_EMAIL` aponta para a caixa de uma pessoa
real, e o `.env.example` já traz uma, porque é por ela que a senha de uso único e a recuperação
chegam. O dono da caixa não consegue cadastrar o próprio servidor com esse endereço enquanto o admin
inicial o detiver.

**A carga recebe a configuração por parâmetro.** `carregar_seed_admin` foge da assinatura
`carregar_seed_<nome>(*, dry_run)` da skill `seeds`, porque quem lê `settings` é o comando e RF e
e-mail não moram em `data/`. O custo é uma seed cuja chamada não é idêntica à das demais.

**`CadastroAdmin` repete campos do `NovoSuperusuario`.** O arquivo carrega só a metade que não vem
do ambiente, e essa metade precisa de um tipo para ser validada na leitura. Campo novo obrigatório
no `NovoSuperusuario` tem de ser acrescentado nos dois.

**A seed passa a conhecer o estado do envio de e-mail.** `ConfiguracaoAdmin` carrega
`EMAIL_ENVIO_HABILITADO` só para decidir o alerta, porque é esse flag que determina por onde a senha
sai. Ligar o envio depois da subida não desfaz o alerta já impresso, nem o reimprime se for
desligado de novo.

**Deploy pode subir sem administrador.** Sem e-mail ou com o RF ocupado a seed não cria nada e não
derruba a subida, para que as variáveis sigam opcionais onde já há administrador. O único sinal de
que o sistema ficou sem ninguém que o administre é uma linha de erro no log do container.

**"Sempre há um administrador" não é invariante.** A seed pergunta só na subida e nunca recria o
admin inicial sobre o RF ocupado, porque a alternativa seria reativar um servidor exonerado por um
ato automático. Se o último administrador perder a marca depois de o admin inicial ter sido
exonerado, a subida só devolve um com `ADMIN_RF` trocado — ou pelo comando `criar_superusuario`.

**Servidor fictício no quadro.** O admin inicial é um `Perfil` como outro qualquer, lotado em
`SF-GAB`, porque o model não distingue conta de serviço de servidor. Ele aparece nas listagens e na
página da unidade até ser exonerado.

## 8 · Testes (TDD)
`tests/apps/user_admin/test_seed_admin.py`, exercitando `carregar_seed_admin`. Todos com o marker
`banco`, exceto o último.

- `test_banco_sem_administrador_ganha_admin_inicial` — banco com unidade e cargos e nenhum
  administrador, envio de e-mail habilitado: o desfecho é `CRIADO` com `senha_sai_em_tela=False`, e
  o perfil tem o RF e o e-mail da configuração, é administrador, lotado e com os cargos do arquivo,
  não titular e em senha provisória. *(marker `banco`)*
- `test_admin_inicial_entra_pela_senha_de_uso_unico_reenviada` — criado com o envio desligado, o
  resultado traz `senha_sai_em_tela=True`; `reenviar_senha_uso_unico` para o RF devolve a senha a
  exibir, e `autenticar_primeiro_login` com ela devolve o admin inicial. *(marker `banco`)*
- `test_segunda_carga_nao_duplica_nem_reescreve` — depois da primeira carga a senha é definida, o
  arquivo é reescrito com outro sobrenome e a configuração muda de e-mail; a segunda carga devolve
  `DISPENSADO`, segue havendo um perfil só, com o sobrenome, o e-mail e a senha de antes dela.
  *(marker `banco`)*
- `test_administrador_existente_dispensa_admin_inicial_mesmo_sem_email` — com outro administrador no
  banco e e-mail vazio, o desfecho é `DISPENSADO`, não `SEM_EMAIL`, e nenhum perfil é criado.
  *(marker `banco`)*
- `test_sem_email_nao_cria` — sem administrador e com o e-mail vazio: desfecho `SEM_EMAIL` e nenhum
  perfil gravado. *(marker `banco`)*
- `test_rf_ocupado_nao_cria_e_nao_estoura` — RF da configuração pertencendo a um servidor exonerado
  e nenhum administrador: o desfecho é `RF_OCUPADO`, sem exceção e sem segundo perfil.
  *(marker `banco`)*
- `test_rf_fora_do_formato_aborta_sem_gravar_nada` — configuração com RF de cinco dígitos: a carga
  levanta o `ValidationError` do Pydantic e nenhum perfil fica no banco. *(marker `banco`)*
- `test_unidade_ausente_aborta_sem_gravar_nada` — arquivo nomeando sigla que não existe: a carga
  levanta `ObjectDoesNotExist` e nenhum perfil fica no banco. *(marker `banco`)*
- `test_dry_run_nao_persiste` — mesmo cenário do primeiro teste com `dry_run=True`: desfecho
  `CRIADO` e nenhum perfil gravado. *(marker `banco`)*
- `test_run_seeds_chama_seed_admin_depois_de_unidades_e_cargos` — em `docker/run_seeds.sh`, a linha
  de `seed_admin` vem depois das de `seed_unidades` e `seed_cargos`.
