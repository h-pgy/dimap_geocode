---
spec: ingestao_dados/007
versao: v1
atualizado_em: 2026-07-31
implementado: false
depende_de: ingestao_dados/006
changelog:
  - v1: versão inicial
---

# SPEC ingestao_dados/007 — Daemon de atualização dos dados + metadados de `data/`

- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

> **Depende da SPEC 006** (contrato `ScriptRunner`, escrita atômica em `services/utils/io`,
> isolamento da `data/` real nos testes). Sem ela, o pipeline quebra na 4ª etapa por falta de
> `--verbose`, o registro de falha mente sobre um parquet truncado e a suíte grava metadado de
> teste no JSON versionado.

## User story
Como operador da plataforma, quero que os parquets de `data/` sejam reextraídos sozinhos, num
horário fixo do dia definido por variável de ambiente, e que cada arquivo registre **quando foi
atualizado pela última vez**, para que o runtime web deixe de reler eternamente o mesmo arquivo
velho e passe a ter como saber se o dado em disco mudou.

## Critérios de aceite

### Pipeline one-shot

- [ ] Existe um comando **one-shot** que executa o pipeline de cargas **na ordem correta**
      (§6.4: cargas → variações → cache), reaproveitando os comandos que já existem, e imprime o
      resultado de cada etapa.
- [ ] O one-shot chama **toda** etapa em modo verboso — não é opção dele, é o contrato: rodando sem
      ninguém olhando, log mudo é log inútil.
- [ ] Se uma etapa falha, o ciclo **para naquela etapa** (as seguintes consomem o artefato da
      anterior), reporta qual falhou e por quê, e sai com código de erro — sem executar as
      etapas restantes.

### Daemon

- [ ] Existe um comando **daemon**, que roda como processo próprio, dorme até o **horário do dia**
      configurado em variável de ambiente (`DATA_UPDATE_TIME`, formato `HH:MM`, no fuso do
      projeto) e então dispara o pipeline one-shot; ao terminar, volta a dormir até a próxima
      ocorrência. **Roda indefinidamente.**
- [ ] A variável é lida pelo `_Settings` **já tipada como `datetime.time`** e reextraída para a
      constante `DATA_UPDATE_TIME` — a aritmética do domínio recebe um `time`, nunca uma string
      para parsear.
- [ ] Uma falha do pipeline **não derruba o daemon**: ele reporta o erro e segue agendado para o
      dia seguinte.
- [ ] O daemon sobe como **serviço próprio do `docker compose`**, paralelo ao `web`, usando a
      mesma imagem — o processo web não é onerado pela extração.
- [ ] O daemon é **opcional por flag do compose**: `docker compose up` sobe `db` + `web` **sem**
      atualização automática; `docker compose --profile atualizacao up` sobe os três. A escolha é
      feita **na hora de subir**, sem editar arquivo e sem container ocioso rodando à toa.

### Contrato: a chave `manual`

- [ ] O contrato `ScriptRunner` da SPEC 006 é **estendido** com uma segunda chave:
      `run(request, *, verbose=False, manual=True) -> Result`. O `Protocol`, os quatro runners e o
      teste de varredura acompanham — a extensão é aditiva e continua verificada pelo `mypy`.
- [ ] `manual` é **verdadeiro por padrão** e só vira falso quando a execução vem do daemon: rodar
      qualquer comando do pipeline na mão produz `manual: true`, sem flag nenhuma. Quem marca a
      execução como automática é o daemon, e a marcação atravessa a cadeia até o registro.
- [ ] **Todo comando do pipeline expõe `--automatico`**, repassando-o ao `run()` como
      `manual=not automatico`. É a única negação da cadeia, e ela mora no comando.

### Metadados

- [ ] Toda execução de script do pipeline registra seu resultado num **JSON de metadados em
      `data/`**, tenha ela **dado certo ou errado**. Vale para execução pelo daemon **e** para
      execução manual de um comando isolado.
- [ ] O registro traz, por arquivo: **`status`** (`sucesso`/`falha`), **`last_run`** (quando a
      última tentativa terminou, **tenha falhado ou não**), **`manual`** (booleano: se a execução foi
      disparada na mão ou pelo daemon), **`last_successful_run`** (quando o parquet foi de fato
      reescrito pela última vez) e **`registros`** (contagem gravada). Em caso de falha, traz também
      o **erro** e o **traceback** — é o que responde "por que não atualizou" sem precisar do log do
      container.
- [ ] As duas datas são gravadas como **string no formato dia-mês-ano**, com hora
      (`31-07-2026 03:04:12`), e o formato vive numa **constante única** do módulo de metadados —
      quem escreve e quem lê usam a mesma, nunca um literal solto (§6.1).
- [ ] **`last_successful_run` só é reescrito quando a execução dá certo.** Ao abrir o JSON para
      gravar, o valor anterior é guardado; se a execução falhar, ele é **devolvido ao arquivo
      inalterado**, junto de `registros`. Nunca houve sucesso ainda → fica nulo.
- [ ] **Uma falha não apaga a memória do último sucesso.** `status`/`last_run`/`manual`/`erro`
      descrevem a última **tentativa**; `last_successful_run`/`registros` descrevem a última
      **escrita bem-sucedida** e sobrevivem intactos a quantas falhas vierem depois — é deles que a
      fase 2 vai depender.
- [ ] A gravação é **read-modify-write por chave**: lê o JSON, parseia para dicionário, **sobrescreve
      apenas a chave daquele script** e reescreve o arquivo inteiro. O registro de um arquivo nunca
      apaga o dos demais.
- [ ] Ler os metadados quando o JSON ainda não existe (primeira execução, checkout limpo) devolve
      "nada registrado" em vez de quebrar.
- [ ] A escrita do JSON é **atômica**, pelo helper de `services/utils/io` entregue na SPEC 006 — o
      processo web nunca lê um JSON pela metade, e o módulo de metadados não monta `Path` nem
      reimplementa `os.replace`.
- [ ] A falha continua **propagando** depois de registrada: o registro é observabilidade, não
      captura de erro. O comando falha, o pipeline aborta, o daemon reporta.

### Documentação

- [ ] A skill `management-commands` documenta as duas regras novas: **todo `runner.py` que escreve
      um artefato em `data/` registra a execução nos metadados** (via o helper compartilhado,
      envolvendo o trabalho) e **todo comando do pipeline expõe `--automatico`**, traduzindo-o para
      `manual`. Sem isso as regras existiriam só neste arquivo e o próximo script do pipeline
      nasceria sem elas.

## Contexto e decisões de arquitetura

Hoje as duas pontas não se falam. Os comandos de extração produzem parquets em `data/`; os
`Catalog` in-memory (skill `catalogos-lookup`) releem o parquet quando o TTL expira. Mas nada
atualiza o parquet: sem alguém rodando os comandos, o TTL só faz o catálogo reler **o mesmo
arquivo**. Esta SPEC fecha a ponta de trás (quem atualiza o disco, e quando) e deixa **registrado
em disco** o que a ponta da frente vai precisar depois para decidir se vale reler.

**Três peças, em camadas distintas:**

1. **Agenda (domínio puro, `services/`).** A aritmética "dado o horário configurado e o instante
   atual, quantos segundos até a próxima ocorrência" é uma função pura — é o único pedaço do
   daemon com regra própria, e é onde moram as bordas (horário já passou hoje → amanhã; horário
   exatamente agora → **próximo dia**, nunca zero, para não disparar duas vezes).
2. **Pipeline (domínio puro, `services/`).** A execução ordenada com parada na primeira falha é
   uma classe callable que recebe o executor **por composição, tipado como `Callable[[str], None]`**
   (§7.1) e devolve um `...Result` Pydantic. Ela **não sabe o que é um management command** — recebe
   uma lista de nomes e um executor. É isso que a torna testável sem Django, sem rede e sem banco.
3. **Comandos (orquestração, `apps/core`).** Quem sabe que "executar uma etapa" é
   `call_command(nome)` e quem conhece a **ordem** das etapas é o Django — logo, vive no comando.
   O comando one-shot passa a lista ordenada no `...Request` e injeta `call_command` como executor;
   o comando daemon lê `settings.DATA_UPDATE_TIME`, chama a agenda, dorme e dispara o one-shot.
   O daemon mora em `apps/core` (não em `address_geocoder` nem em `logradouro_matcher`) porque
   atravessa os dois domínios — §7.1: módulo não cruza domínios, e infraestrutura transversal é do
   `core`.

**Agenda e pipeline são módulos soltos em `services/scripts/`, não um subpacote.** Eles são
infraestrutura do pipeline, não scripts de carga: não têm `run()`, não recebem `Request` de
extração e não escrevem artefato em `data/`. A SPEC 006 fixou a regra topológica que separa as duas
coisas — **subpacote de `services/scripts/` é script de carga e tem que expor um `run()` aderente ao
contrato; módulo solto no topo é infraestrutura e não é varrido** — justamente para que estes dois
possam morar ali sem reprovar o teste de contrato e sem precisar de lista de exceções. É a mesma
prateleira do `contrato.py`.

**Verbose obrigatório.** O daemon roda sem plateia: se uma extração do GeoSampa trava por 40
minutos, a única evidência disponível é o stdout do container. Por isso o executor injetado pelo
one-shot é `call_command(etapa, verbose=True)` — fixo, não configurável. Isso exige que **as quatro
etapas exponham `--verbose`**, o que a SPEC 006 entrega (hoje `augment_logradouro_types` não expõe,
e como `call_command` levanta `TypeError: Unknown option(s)` para flag não declarada, o pipeline
quebraria na 4ª etapa).

**Onde `--automatico` é verificado, e onde só é regra.** O `run()` tem o contrato: a chave `manual`
entra no `Protocol`, é checada estaticamente pelo `mypy` e varrida pelo teste de descoberta da SPEC
006, que passa a exigir as duas chaves. Já o `--automatico` do **management command** fica como
regra documentada na skill: verificá-lo exigiria carregar a classe do comando e montar o parser, ou
seja, `django.setup()` numa suíte que hoje não depende do Django (não há `pytest-django` no
projeto). O custo não paga — o comando é fino, e com o `run()` já obrigado pelo contrato o que sobra
ali é uma linha de repasse. E o `call_command` levantando `TypeError` faz o esquecimento aparecer na
primeira execução do pipeline, não em produção silenciosa.

> **Divergência consciente da skill `management-commands`:** ela diz que o comando não tem
> comportamento próprio e por isso não se testa. Aqui o comando one-shot **orquestra outros
> comandos** — e o comportamento que importa (ordem + parada na falha) foi deliberadamente extraído
> para `services/`, justamente para continuar valendo a regra. O comando segue fino: lista ordenada,
> injeção do executor, formatação do resultado.

**Metadados: Pydantic + JSON em `data/`, não model do Django.** O consumidor final deste registro é
o `Catalog` (fase 2, fora desta SPEC), que vive em `services/domain/` e **não pode depender do
Django** (§3.3) — um model do ORM seria ilegível exatamente por quem precisa lê-lo. Além disso o
registro é escrito por scripts que rodam apartados do runtime web (§6.4), fora do ciclo de
request, e `data/` já é o lugar dos artefatos do pipeline (§5). Então o "model" é um **DTO Pydantic**
serializado para um JSON versionável em `data/` — que é literalmente o que ele precisa ser para
sobreviver à troca de processo. Fica em `services/utils/` (escopo geral, sem domínio, vizinho de
`io/` que já resolve `data/`), e não em `services/scripts/`, para que o domínio possa lê-lo sem
importar a camada de scripts.

**Quem registra é o `runner.py` de cada script**, logo após `write_parquet_to_data` — não o daemon.
Se quem registrasse fosse o daemon, rodar `extrair_enderecos_fiscais` na mão deixaria o metadado
mentindo, e a fase 2 tomaria decisão errada com base nele. O runner é o único ponto que sabe, ao
mesmo tempo, **qual arquivo** escreveu e **quantos registros** gravou.

**Mas o runner não escreve JSON — ele usa um helper único, compartilhado.** O registro mora em
`services/utils/` e é **importado por todos os runners**, exatamente como `write_parquet_to_data` já
é hoje. Nenhum script monta `Path`, serializa DTO ou decide formato do JSON: quem faz isso é o
módulo de metadados, uma vez só. É o mesmo raciocínio do §6.1 (normalização única): o formato do
registro é lido depois por outro código, em outro processo — se cada script escrevesse o seu, a
primeira divergência de formato só apareceria na fase 2, do lado do `Catalog`, que é o pior lugar
possível para descobrir isso. O runner passa **o que ele sabe** (nome do arquivo e contagem); o
resto — timestamp, fuso, captura do traceback, merge com os registros dos outros arquivos, escrita
atômica — é do módulo.

**Registrar a falha muda a forma do helper: de função para gerenciador de contexto.** Uma função
chamada *depois* da escrita nunca roda quando a escrita explode — e é justamente aí que o registro
importa. Então o runner **envolve** seu trabalho:

```
with registrar_execucao(OUTPUT_FILENAME, manual=manual) as registro:
    ...extrai, escreve o parquet...
    registro.sucesso(registros=len(rows))
```

Saindo limpo, grava `sucesso`; saindo por exceção, grava `falha` com erro e traceback **e deixa a
exceção seguir** — o registro é observabilidade, não `try/except` disfarçado. O comando continua
falhando, o pipeline continua abortando na etapa e o daemon continua reportando. Fica um único
ponto no projeto que sabe escrever esse JSON, e nenhum runner ganha `try/except`.

**Duas linhas do tempo no mesmo registro.** `status`/`last_run`/`manual`/`erro` falam da última
**tentativa**; `last_successful_run`/`registros` falam da última **escrita bem-sucedida**. `last_run`
é carimbado sempre, deu certo ou não — é ele que responde "o daemon acordou hoje?". Uma falha
atualiza os primeiros e **preserva** os segundos: ao abrir o JSON, o helper guarda o
`last_successful_run` que estava lá e, se o bloco explodir, devolve o mesmo valor ao arquivo. Se
falha zerasse esse campo, a fase 2 concluiria que o parquet nunca foi escrito e reagiria a um dado
que continua lá, íntegro, do dia anterior.

Essa preservação é consequência direta do **read-modify-write por chave**: lê o JSON inteiro, mexe
só na entrada daquele arquivo (herdando dela o que não mudou), reescreve. Escritor concorrente é
teoricamente possível — nada impede alguém rodar um comando na mão enquanto o daemon roda, e aí a
última escrita ganha —, mas numa janela de segundos, uma vez por dia, para dezenas de usuários
internos, travar arquivo custaria mais do que o problema que evita (§1: a simplicidade vence). A
concorrência que **de fato** precisa de tratamento é outra: o processo web **lendo** enquanto o
daemon escreve, e é só para isso que serve o `os.replace`.

**Datas como string dia-mês-ano, com o formato numa constante única.** É o formato pedido, e para um
arquivo lido por gente (é o primeiro lugar onde se olha quando "a busca está desatualizada") ele
ganha do ISO. O custo: string em `DD-MM-YYYY` não é ordenável lexicamente e obriga quem lê a parsear
com o formato certo — se a fase 2 usar um literal próprio, a primeira divergência aparece como um
`ValueError` no `Catalog`, longe da causa. Por isso o formato é **uma constante do módulo de
metadados** (`FORMATO_DATA`), usada tanto na escrita quanto na leitura, e o módulo entrega
`datetime` já parseado a quem consome — mesmo raciocínio da normalização única (§6.1): a regra de
formato existe **uma vez**, e ninguém fora do módulo escreve `strftime`/`strptime`.

**Quem sabe se a execução foi manual é o processo, não o script.** O `run()` não tem como
descobrir sozinho quem o chamou — a informação nasce lá em cima e desce pela cadeia. O daemon
dispara `call_command("atualizar_dados", automatico=True)`; o one-shot repassa o mesmo valor a cada
etapa; cada comando traduz para `manual=not automatico` e entrega ao `run()`, que o passa ao
registro. A flag `--automatico` existe nos comandos do pipeline como **uso interno do daemon**, e o
padrão (`store_true` desligado) é o que garante o comportamento pedido: quem digita
`manage.py extrair_nomes_logradouros` no terminal grava `manual: true` sem saber que a flag existe.
Rodar `manage.py atualizar_dados` na mão também é manual — "manual" não é "etapa isolada", é
"não foi o daemon". O default conservador também protege script novo que esqueça de repassar o
parâmetro: no pior caso uma execução automática aparece rotulada como manual, nunca o contrário.

É por isso que `manual` mora **aqui** e não na SPEC 006: entregar a chave junto do contrato, antes do
registro existir, seria um parâmetro que ninguém lê e uma flag de CLI que não faz nada. O contrato é
estendido de forma aditiva — nenhum runner reescrito, uma chave a mais no `Protocol` e no teste de
varredura.

**Chave do dicionário = nome do arquivo parquet** (`enderecos_fiscais.parquet`), não nome do script:
quem vai consultar isso na fase 2 é o `Catalog`, e o que ele conhece é o arquivo que lê. Um script
por parquet, então a distinção é sem diferença hoje — mas a chave certa é a do consumidor.

**O daemon torna o `git status` permanentemente sujo, e isso é aceito.** O serviço monta o código do
host em `/app`, então ele escreve nos parquets e no JSON **versionados** — depois de cada ciclo
noturno, `git diff` acusa os quatro artefatos. É consequência direta de manter `data/` versionado
(decisão da SPEC 006: `git pull` + `runserver` tem que subir com dado real), e a alternativa —
ignorar os parquets — custaria minutos de GeoSampa a cada clone. Quem sobe o profile `atualizacao`
está assumindo que vai commitar ou descartar a carga do dia; o JSON de metadados, versionado junto,
é o que diz **de quando** é o dado que veio no clone.

**Fluxo:**

```
docker compose: serviço `daemon` (profile `atualizacao`)
  └→ manage.py daemon_atualizar_dados            (orquestração)
       ├→ agenda: segundos até HH:MM             (services — puro)
       ├→ dorme
       └→ call_command("atualizar_dados", automatico=True)   (orquestração)
            └→ PipelineAtualizacao(executor)     (services — puro)
                 ├→ extrair_nomes_logradouros    ──┐
                 ├→ extrair_segmentos_logradouros  │ cargas  (executor = call_command
                 ├→ extrair_enderecos_fiscais    ──┘          com verbose/automatico fixos)
                 └→ augment_logradouro_types       variações (consome nomes_logradouros)
                      └→ cada runner: registrar_execucao(...) envolvendo
                         write_parquet_to_data      → data/metadados_dados.json
```

## Peças de referência a compor

- `@services/scripts/contrato.py` *(SPEC 006)* → o `ScriptRunner`, estendido aqui com a chave
  `manual`.
- `@services/scripts/*/runner.py` → os quatro `run()`: ganham a chave `manual` e envolvem o trabalho
  no `registrar_execucao`. A lógica de extração — extractors, `_to_columns`, `pipeline` do augment —
  **não muda**, e nenhum deles conhece o formato do JSON de metadados.
- `@services/utils/io` → o helper de escrita atômica entregue pela SPEC 006: o módulo de metadados o
  **usa**, não reimplementa `os.replace` nem monta `Path` para `data/`.
- `@apps/*/management/commands/extrair_*.py`, `@apps/logradouro_matcher/management/commands/augment_logradouro_types.py`
  → as quatro etapas do pipeline, **reaproveitadas como etapas** (o one-shot as executa via
  `call_command`, não reimplementa nenhuma extração). Cada uma passa a expor `--automatico` e
  repassá-lo — permanecem finas, no padrão da skill.
- `@config/settings.py` → padrão Pydantic Settings + reextração para constante `UPPER_CASE`; o campo
  novo é tipado `datetime.time` para o Pydantic coagir o `HH:MM` do env. `TIME_ZONE =
  "America/Sao_Paulo"` e `USE_TZ = True` já definem o fuso.
- `@apps/core` → o app transversal onde os dois comandos novos moram; hoje ele não tem diretório
  `management/`.
- `@docker-compose.yml` + `@Dockerfile` + `@entrypoint.sh` → o serviço `daemon` reusa a mesma
  imagem e o mesmo entrypoint do `web` (que já faz `exec "$@"` e respeita `DJANGO_AUTO_MIGRATE`),
  trocando só o `command`.
- `@.env.example` → onde a nova variável é documentada.
- `@tests/conftest.py` → o fixture `autouse` que a SPEC 006 aponta para um diretório temporário: é o
  que faz os testes de metadados não tocarem o JSON versionado.
- `@.claude/skills/management-commands/SKILL.md` → "Anatomia do script": é onde entram o registro de
  metadados no `runner.py` e a flag `--automatico` do comando.

## Snippets sugeridos

```python
# services/scripts/agenda.py — módulo solto no topo: infraestrutura, não é varrido pelo contrato
def segundos_ate_proximo(horario: time, agora: datetime) -> float:
    alvo = agora.replace(hour=horario.hour, minute=horario.minute, second=0, microsecond=0)
    if alvo <= agora:                      # já passou hoje (ou é exatamente agora) → amanhã
        alvo += timedelta(days=1)
    return (alvo - agora).total_seconds()


# services/scripts/pipeline.py — não sabe o que é management command
class PipelineAtualizacao:
    def __init__(self, executar: Callable[[str], None]) -> None:
        self._executar = executar

    def __call__(self, request: AtualizacaoRequest) -> AtualizacaoResult:
        executadas: list[str] = []
        for etapa in request.etapas:
            try:
                self._executar(etapa)
            except Exception as exc:       # etapa seguinte consome o artefato desta → aborta
                return AtualizacaoResult(executadas=executadas, falhou_em=etapa, erro=str(exc))
            executadas.append(etapa)
        return AtualizacaoResult(executadas=executadas)


# services/scripts/contrato.py — a chave `manual` entra aqui (SPEC 006 entregou só `verbose`)
class ScriptRunner(Protocol[Req, Res]):
    """Todo script de carga entra por aqui: um Request, e as duas chaves do pipeline."""

    def __call__(self, request: Req, *, verbose: bool = False, manual: bool = True) -> Res: ...


# services/scripts/<nome>/runner.py — registro envolvendo o trabalho
def run(
    request: EnderecosFiscaisRequest, *, verbose: bool = False, manual: bool = True
) -> EnderecosFiscaisResult:
    with registrar_execucao(OUTPUT_FILENAME, manual=manual) as registro:
        fetcher = WfsFetcher(request.conexao, retry_policy=request.retry, verbose=verbose)
        rows = EnderecosFiscaisExtractor(fetcher)(request)
        output_path = write_parquet_to_data(_to_columns(rows), OUTPUT_FILENAME)
        registro.sucesso(registros=len(rows))
    return EnderecosFiscaisResult(total_records=len(rows), output_path=output_path)


# services/utils/metadados/ — DTO que vira o JSON de data/, e o helper único que todos usam
FORMATO_DATA = "%d-%m-%Y %H:%M:%S"   # constante única: escrita E leitura passam por aqui


class MetadadoArquivo(BaseModel):
    arquivo: str
    # última TENTATIVA — carimbada sempre, deu certo ou não
    status: Literal["sucesso", "falha"]
    last_run: datetime               # serializado com FORMATO_DATA
    manual: bool                     # True = disparado na mão; False = disparado pelo daemon
    erro: str | None = None          # "TipoDoErro: mensagem"
    traceback: str | None = None     # traceback completo, truncado — o "por que falhou"
    # última ESCRITA bem-sucedida — devolvidas intactas quando a tentativa falha
    last_successful_run: datetime | None = None
    registros: int | None = None


def ler_metadados() -> dict[str, MetadadoArquivo]: ...   # {} se o JSON ainda não existe


@contextmanager
def registrar_execucao(arquivo: str, *, manual: bool) -> Iterator[Registro]:
    """Envolve o trabalho do runner: grava sucesso ao sair limpo, falha ao sair por exceção.

    Read-modify-write: lê o JSON, sobrescreve SÓ a chave `arquivo`, reescreve pelo helper
    atômico de services.utils.io. `last_run` é carimbado nos dois caminhos. Na falha, devolve
    ao arquivo o `last_successful_run`/`registros` que já estavam lá — a memória do último
    sucesso não se perde — e RELEVANTA a exceção (isto não é try/except, é observabilidade).
    """


# config/settings.py — tipado como `time` para o Pydantic coagir o "HH:MM" do env
class _Settings(BaseSettings):
    data_update_time: time = Field(default=time(3, 0), alias="DATA_UPDATE_TIME")


DATA_UPDATE_TIME = _env.data_update_time


# apps/*/management/commands/<etapa>.py — a flag do daemon e a única negação da cadeia
parser.add_argument(
    "--automatico",
    action="store_true",
    help="uso interno do daemon: marca a execução como automática nos metadados.",
)

result = run(
    request,
    verbose=bool(options["verbose"]),
    manual=not options["automatico"],            # a única negação, e é aqui
)


# apps/core/management/commands/atualizar_dados.py — verbose é do contrato, não opção do usuário;
# `automatico` é repassado: o one-shot rodado na mão marca as etapas como manuais.
ETAPAS: tuple[str, ...] = (
    "extrair_nomes_logradouros",
    "extrair_segmentos_logradouros",
    "extrair_enderecos_fiscais",
    "augment_logradouro_types",     # variações: consome nomes_logradouros.parquet
)

automatico = bool(options["automatico"])
resultado = PipelineAtualizacao(
    lambda etapa: call_command(etapa, verbose=True, automatico=automatico)
)(AtualizacaoRequest(etapas=ETAPAS))
if resultado.falhou_em is not None:
    raise CommandError(f"pipeline abortou em {resultado.falhou_em}: {resultado.erro}")


# apps/core/management/commands/daemon_atualizar_dados.py — o loop, e a marca de "automático"
while True:
    espera = segundos_ate_proximo(
        settings.DATA_UPDATE_TIME, datetime.now(ZoneInfo(settings.TIME_ZONE))
    )
    self.stdout.write(f"[daemon] próxima atualização em {espera / 3600:.1f}h")
    sleep(espera)
    try:
        call_command("atualizar_dados", automatico=True)   # só o daemon marca como automático
    except Exception as exc:            # falha é reportada; o daemon segue agendado
        self.stderr.write(f"[daemon] atualização falhou: {exc}")
```

```yaml
# docker-compose.yml — processo paralelo, mesma imagem, sem porta exposta
  daemon:
    build: .
    # Flag de subida: serviço só existe sob o profile `atualizacao`.
    #   docker compose up                          → db + web (sem atualização automática)
    #   docker compose --profile atualizacao up    → db + web + daemon
    profiles: ["atualizacao"]
    command: python manage.py daemon_atualizar_dados
    environment:
      DJANGO_AUTO_MIGRATE: "0"        # quem migra é o web
      DATA_UPDATE_TIME: ${DATA_UPDATE_TIME:-03:00}
      # + as mesmas variáveis de banco/Django do serviço web
    volumes:
      - .:/app                        # grava os parquets no data/ do host
    depends_on:
      db:
        condition: service_healthy
```

**Por que `profiles` e não uma variável tipo `DATA_UPDATE_ENABLED=0`:** com a variável, o container
sobe de qualquer jeito e fica ocioso (ou morre em loop de restart) só para não fazer nada — e o
"desligado" vira estado escondido dentro do processo. Com o profile, desligado significa
**serviço não criado**; ligado é uma flag explícita no comando de subida, e o `docker compose ps`
diz a verdade sobre o que está rodando.

## Fora de escopo

- **Tudo o que a SPEC 006 entrega** — contrato `ScriptRunner` e sua verificação, escrita atômica em
  `services/utils/io`, isolamento da `data/` real nos testes, `--verbose` no `augment`,
  `data/*.tmp` no `.gitignore`. Aqui isso é **pré-requisito consumido**, não trabalho.
- **Mudar a lógica dos `Catalog`** para consultar os metadados (só reler quando o TTL estourou
  **e** o arquivo mudou em disco). É a fase 2, explicitamente adiada — esta SPEC apenas **produz**
  o dado que ela vai consumir.
- Refresh de cache do processo web a partir do daemon: continua valendo o que diz a skill
  `catalogos-lookup` (TTL lazy ou restart do processo).
- **Histórico** de execuções: o JSON guarda **uma entrada por arquivo**, a mais recente. Sucesso
  novo sobrescreve sucesso velho; falha nova sobrescreve falha velha. Quem quiser a série temporal
  tem o stdout do container — o JSON é estado, igual aos parquets.
- Lock de arquivo ou qualquer coordenação entre um daemon e um comando rodado na mão ao mesmo
  tempo: a última escrita ganha.
- Alerta/notificação em cima do `status: falha` (e-mail, webhook, painel). O dado passa a existir
  aqui; agir sobre ele é outra iteração.
- Fila/worker (Celery, RQ), cron do sistema, healthcheck ou métricas do daemon — §1: dezenas de
  usuários, a simplicidade vence.
- Múltiplos horários por dia, intervalo configurável ou execução imediata na subida do daemon.
- Retry automático de etapa que falhou (o `WfsRetryPolicy` já cobre a resiliência de rede dentro
  de cada extração).

## Testes (TDD)

- `test_segundos_ate_proximo_horario_ainda_hoje` — horário configurado ainda não passou: a espera
  é até hoje, no mesmo dia.
- `test_segundos_ate_proximo_horario_ja_passou` — horário já passou (inclusive quando é
  **exatamente agora**): a espera é até o dia seguinte e nunca é ≤ 0.
- `test_pipeline_executa_etapas_na_ordem` — com um executor fake, as etapas são chamadas na ordem
  recebida e o resultado lista todas como executadas.
- `test_pipeline_aborta_na_primeira_falha` — executor que levanta na 2ª etapa: a 3ª e a 4ª não são
  chamadas, e o resultado aponta a etapa que falhou com o erro.
- `test_registro_de_sucesso_sobrescreve_so_a_propria_chave` — registrar um arquivo grava
  `status=sucesso`, `last_run`, `last_successful_run` e `registros` (datas no formato dia-mês-ano),
  e mantém intactos os registros dos demais arquivos.
- `test_registro_de_falha_guarda_erro_e_preserva_last_successful_run` — quando o bloco levanta, o
  registro fica `status=falha` com erro/traceback e `last_run` novo, **devolve** o
  `last_successful_run`/`registros` do sucesso anterior, e a exceção **continua propagando**.
- `test_ler_metadados_sem_arquivo` — sem o JSON em `data/`, a leitura devolve vazio em vez de
  levantar.

Além dos novos, o `test_todo_runner_de_script_segue_o_contrato` (SPEC 006) é **estendido**: passa a
exigir também a chave `manual` keyword-only com default `True`. A asserção cresce; o teste continua
sendo um só, por descoberta.

## Patches

_Nenhum patch registrado até o momento._
