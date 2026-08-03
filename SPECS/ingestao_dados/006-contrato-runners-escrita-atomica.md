---
spec: ingestao_dados/006
versao: v1
atualizado_em: 2026-07-31
implementado: false
changelog:
  - v1: versão inicial
---

# SPEC ingestao_dados/006 — Contrato de runners, escrita atômica e isolamento da `data/` nos testes

- [ ] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story
Como desenvolvedor do pipeline de dados, quero que **todo script de carga entre por uma assinatura
única verificada pelo `mypy`**, que a **escrita em `data/` nunca destrua o artefato anterior**, e que
a **suíte de testes não escreva um byte na `data/` versionada**, para que o pipeline possa ser
automatizado (SPEC 007) sem que cada script novo reintroduza a mesma classe de erro — e para que
`uv run pytest` pare de reescrever parquet versionado.

## Critérios de aceite

### Contrato de runner

- [ ] **Todo runner de script tem a mesma assinatura**, declarada como contrato em código:
      `run(config, *, verbose=False) -> Result`. O que hoje entra solto por parâmetro (config de
      conexão, política de retry, nomes de arquivo) passa a ser **campo do `Config`** — DTO nas
      duas pontas, uma porta só.
- [ ] O contrato é um **`Protocol` genérico** (`ScriptRunner[Config, Result]`) e cada `runner.py`
      se declara aderente a ele, de modo que **o `mypy` confere** — quem escrever um runner com
      assinatura diferente não passa no `uv run mypy .`.
- [ ] **Um teste varre `services/scripts/` e falha se algum `run()` divergir do contrato.** A
      varredura é por descoberta, não por lista fixa: script novo entra no teste sozinho — inclusive
      um que tenha esquecido de se declarar aderente ao `Protocol`, caso que o `mypy` não pega.
- [ ] A varredura tem uma **regra estrutural, não uma lista de exceções**: **todo subpacote de
      `services/scripts/` é um script de carga e expõe um `run()` aderente**; **módulo solto no topo
      de `services/scripts/` é infraestrutura do pipeline** (o próprio `contrato.py`, e o que a SPEC
      007 acrescentar) e não é varrido. Subpacote sem `run()` reprova.
- [ ] O `augment_tipos_logradouro` ganha o `Config` que hoje não tem, com os nomes de arquivo como
      **campos com default** — o comando **não** importa constante do script só para devolvê-la.

### Verbose em todo o pipeline

- [ ] **Todos os comandos do pipeline expõem `--verbose`** e o repassam ao `run()`. Hoje
      `augment_logradouro_types` é o único que não expõe — não tem `add_arguments`; passa a expor.
- [ ] O `--verbose` do `augment` tem **conteúdo real, não flag morta**: com ele ligado, o `run()`
      devolve no `AugmentStats` a contagem de **variações geradas por tipo**, que o comando imprime.
      O script segue sem escrever em stdout — verbose ali não é "imprimir mais", é **apurar e
      devolver mais**.

### Escrita atômica

- [ ] **A sobrescrita de qualquer artefato de `data/` é atômica.** A escrita vai para um arquivo
      temporário na **própria** `data/` e só assume o nome definitivo por `os.replace` depois de
      concluída. Escrita interrompida no meio (processo morto, disco cheio) **não destrói o arquivo
      anterior**: quem lê vê o velho inteiro ou o novo inteiro, nunca um truncado.
- [ ] A atomicidade mora **num único lugar**, nos helpers de escrita de `services/utils/io` (parquet
      **e** JSON), não em cada script. **Nenhum runner muda por causa dela.**
- [ ] O temporário é **removido** quando a escrita falha — `data/` não acumula sobras — e
      `data/*.tmp` está no `.gitignore`, para que uma sobra de processo morto (`kill -9`, que não
      roda `finally`) não apareça como arquivo novo no `git status` nem entre num commit.
- [ ] O nome do temporário é **próprio de cada processo** (sufixo de PID). Dois processos escrevendo
      o mesmo artefato ao mesmo tempo não compartilham temporário — cada um promove o seu, inteiro.
- [ ] **Só o `.tmp` é ignorado.** Parquets e JSON **continuam versionados** (§5: `data/` é dado
      versionado) — `git pull` seguido de `runserver` tem que funcionar sem reextrair nada do
      GeoSampa.
- [ ] **O artefato é sobrescrito, sempre.** Cada script escreve no seu nome fixo em `data/` — não há
      versionamento, sufixo de data, diretório por execução nem retenção de histórico. `data/` é o
      estado atual dos dados, não um repositório de cargas.

### Isolamento da `data/` real nos testes

- [ ] **Nenhum teste escreve na `data/` real.** `uv run pytest` roda inteiro sem alterar um byte de
      `data/` — o diretório de dados é resolvido **na hora da chamada** (não amarrado no import),
      e um fixture `autouse` aponta os testes para um diretório temporário.
- [ ] O redirecionamento **alcança de fato os escritores**: redirecionar o diretório passa a valer
      para o próximo `write_parquet_to_data`/`read_parquet_from_data` **sem que cada módulo de IO
      precise ser patchado um a um**. Redirecionamento que não alcança o chamador falharia em
      silêncio — a suíte seguiria escrevendo na `data/` real e passando.
- [ ] O redirecionamento **não vale para os testes marcados `integration`**, que leem os parquets
      reais por definição: `uv run pytest -m integration` continua passando, lendo `data/` de
      verdade. A exceção é **por marker**, não por lista de arquivos — hoje são 8 testes, em 8
      arquivos sobre 6 pacotes de domínio, e a regra tem que valer para o 9º sem ninguém editar nada.
- [ ] O teste do `augment` deixa de depender dos artefatos reais: monta seus próprios insumos
      sintéticos no diretório temporário e afirma sobre eles. Hoje ele chama `run()` sem argumentos,
      lê o `nomes_logradouros.parquet` real e **reescreve o `tipos_logradouro_cache.parquet`
      versionado três vezes por execução da suíte**.

### Documentação

- [ ] A skill `management-commands` documenta as duas regras novas: **todo `run()` segue o contrato
      `ScriptRunner`** (`Config` + `verbose`, com a declaração que o `mypy` confere) e **todo
      comando do pipeline expõe `--verbose`**, repassando-o ao `run()`. Sem isso as regras
      existiriam só neste arquivo e o próximo script do pipeline nasceria sem elas.

## Contexto e decisões de arquitetura

Esta SPEC **não entrega funcionalidade nova** — é a fundação sobre a qual a SPEC 007 (metadados +
daemon de atualização) fica possível. Ela foi separada porque as três coisas que traz são
**independentes entre si e do daemon**, valem por si mesmas, e uma delas conserta um defeito que já
existe hoje: a suíte reescreve parquet versionado toda vez que roda.

Nada aqui toca `services/domain/`, views, templates ou banco. O raio de alcance é
`services/scripts/`, `services/utils/io/`, os quatro management commands do pipeline e `tests/`.

**Contrato de runner: uma assinatura só, declarada como `Protocol` e verificada pelo `mypy`.** Os
quatro `run()` de hoje têm quatro formas diferentes — três recebem
`(config, request, retry_policy, verbose)` e o `augment` recebe três nomes de arquivo. O equivalente
a uma ABC para função é o *callback protocol*, e ele só vira garantia de verdade se as
implementações forem **todas compatíveis com a mesma forma** — compatibilidade de callable exige que
a implementação aceite tudo o que o protocolo promete, então protocolo nenhum descreve "qualquer
parâmetro, desde que tenha `verbose`". A saída é convergir: `config` e `retry_policy` (hoje soltos
nos três runners de WFS) e os nomes de arquivo (hoje soltos no `augment`) viram **campos do
`Config`**, que já é um DTO Pydantic. Sobra uma porta única:

```python
def run(config: XConfig, *, verbose: bool = False) -> XResult
```

Isso é exatamente o §7.1 (DTO nas duas pontas) aplicado ao pipeline, e é o que faz o `Protocol`
deixar de ser decoração: com a forma uniforme, cada `runner.py` declara sua aderência e o `mypy`
confere na hora do `uv run mypy .`. Escrever um runner novo deixa de depender de alguém lembrar da
convenção — a checagem é da ferramenta.

> A SPEC 007 **estende** este contrato com uma segunda chave (`manual`), necessária para o registro
> de metadados. A extensão é aditiva e mora lá porque `manual` não tem significado nenhum sem o
> registro: entregá-la aqui seria um parâmetro morto na assinatura e uma flag morta na CLI.

**O `augment` precisa de um `Config` que não existe.** Ao contrário dos outros três, o
`services/scripts/augment_tipos_logradouro/models.py` só tem o `AugmentStats` (o resultado) —
não há `AugmentConfig`. Ele é **criado** aqui, com os três nomes de arquivo como campos. E com
**default no campo**: se o `Config` os exigisse, o comando teria que importar
`TIPOS_LOGRADOURO_AUMENTADO_MANUAL` e `PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL` do pacote do script
apenas para devolvê-los ao `run()` — constante de script vazando para a camada de orquestração, o
oposto do que a skill `management-commands` pede. Nos três runners de WFS a distinção é natural: o
que o comando **lê de `settings`** (camada, timeouts) vai sem default; o que é **constante do
script** (nome do artefato) vai com.

**Por que `Protocol` E teste, e não um dos dois.** Eles falham em situações diferentes, e é por isso
que ambos ficam:

- O **`Protocol`** pega assinatura errada — parâmetro faltando, ordem trocada, tipo incompatível —
  no lugar certo (o arquivo do runner) e sem rodar nada. É a rede fina.
- O **teste por descoberta** pega o que o `mypy` **não** tem como pegar: um `runner.py` novo que
  simplesmente **não se declarou** aderente ao protocolo. Tipagem estrutural só confere onde alguém
  anota; script que não anota é invisível para ela. A varredura enxerga todo subpacote de
  `services/scripts/`, anotado ou não. É a rede grossa, e é ela que garante que a fina foi estendida.

Sem o Protocol, o contrato viraria uma lista de strings dentro de um teste. Sem o teste, bastaria
esquecer uma linha para o contrato deixar de existir para aquele script, em silêncio.

**A varredura precisa de uma regra estrutural, não de uma lista de exceções.** `services/scripts/`
vai ganhar módulos que **não são scripts de carga** — o `contrato.py` desta SPEC, e a agenda e o
pipeline da SPEC 007. Se a varredura simplesmente exigisse `run()` de tudo que há ali, eles a
reprovariam; e se ela pulasse quem não tem `run()`, a rede grossa deixaria de existir (script novo
que esqueceu o `run()` ficaria invisível, que é justamente o caso que ela deveria pegar). Uma lista
de exclusão hardcoded seria a "lista de strings dentro de um teste" que o parágrafo anterior
rejeita.

A regra que resolve isso sem exceção nenhuma é **topológica**: **subpacote** (diretório com
`__init__.py`) de `services/scripts/` **é** um script de carga e **tem** que expor um `run()`
aderente; **módulo solto** no topo é infraestrutura do pipeline e não é varrido. Não há o que
manter: a estrutura de diretórios é a declaração.

**Escrita atômica: `pq.write_table` trunca o destino.** Ele abre o caminho final em modo escrita.
Morrendo no meio (OOM, disco cheio, `docker stop` durante os 37 MB de endereços fiscais), o que
sobra em `data/` não é o parquet velho nem o novo: é um parquet **truncado**. O dado bom que estava
lá some, e o próximo restart do web quebra no `aquecer()` dos catálogos. Isso já é verdade hoje,
antes de qualquer daemon — o daemon só multiplica a frequência da aposta.

A correção é escrever num temporário **dentro de `data/`** (mesmo sistema de arquivos, requisito do
rename atômico — um `/tmp` do sistema não serve, seria cópia entre volumes) e promover com
`os.replace`, que no POSIX é atômico e sobrescreve o destino. Em caso de erro, o temporário é
removido. Quem lê enxerga sempre um arquivo inteiro: o velho ou o novo.

**O temporário tem que ser por processo, ou a atomicidade se desfaz na SPEC 007.** Um nome fixo
(`enderecos_fiscais.parquet.tmp`) basta enquanto só existe execução manual, mas o daemon da 007 pode
estar reextraindo a mesma camada quando alguém dispara o comando na mão: os dois abrem o **mesmo**
temporário, um trunca o do outro, e o primeiro a terminar promove com `os.replace` um arquivo que o
outro ainda está escrevendo — a corrupção que esta SPEC existe para eliminar, reintroduzida pela
porta de trás. Sufixar o temporário com o PID resolve, continua casando com `data/*.tmp` no
`.gitignore` e não custa nada. É barato agora e caro de descobrir depois.

Isso mora **nos helpers de `services/utils/io`** — `write_parquet_to_data` e `write_json_to_data`
passam a escrever assim, e **nenhum runner muda por causa disso**. É a mesma razão de sempre: se
cada script resolvesse a atomicidade, o próximo nasceria sem ela. O `write_json_to_data` entra
junto mesmo sem consumidor hoje, porque o consumidor é o registro de metadados da SPEC 007 e o
helper é o mesmo.

> Atomicidade aqui significa "o leitor nunca vê um arquivo pela metade", não durabilidade contra
> queda de energia (isso pediria `fsync`). Para dezenas de usuários internos e dados reextraíveis
> por um comando, é a troca certa.

**`data/` guarda estado, não histórico.** Cada script escreve no seu nome fixo e sobrescreve o
anterior — sem sufixo de data, sem pasta por execução, sem retenção. Não é data lake: é o retrato
atual das bases oficiais. Isso já é o comportamento de `write_parquet_to_data` (caminho fixo,
`pq.write_table` sobrescreve); o que a SPEC faz é **fixar como regra**, para que nenhuma etapa
futura invente versionamento — e para que a escrita atômica não seja lida como convite a manter a
versão anterior por perto.

**A suíte não pode escrever na `data/` real — e hoje escreve.** `test_run_normaliza_chaves` e
`test_run_idempotente` chamam `run()` do `augment` sem argumentos, ou seja, com os defaults de
produção: leem o `nomes_logradouros.parquet` real e **reescrevem o `tipos_logradouro_cache.parquet`
versionado três vezes a cada `uv run pytest`** (uma no primeiro teste, duas no segundo). Todos os
demais testes do projeto patcham `read_parquet_from_data` no módulo do catalog; este é o único que
toca o diretório de verdade.

A causa é que `data/` está **amarrado no import**: `write_parquet_to_data = partial(write_parquet,
folder=_DATA_DIR)` congela o caminho no carregamento do módulo, então não há como um teste
redirecioná-lo. Trocando os `partial` por funções que resolvem o diretório **na hora da chamada**,
um fixture `autouse` no `conftest.py` aponta a suíte para um diretório temporário — e aí o teste do
`augment` monta seus próprios insumos sintéticos (o JSON de tipos e um parquet de nomes pequeno) e
afirma sobre eles, em vez de sobre 1 MB de dado real. Ele fica rápido, determinístico e para de
depender de a base de produção conter "Avenida".

**Resolver na chamada não basta: o ponto de indireção tem que ser alcançável de fora.** Se
`parquet.py` e `json.py` fizerem `from .config import data_dir`, cada um passa a ter sua **própria**
ligação para a função, e um `monkeypatch.setattr(config, "data_dir", ...)` troca o nome dentro de
`config` sem alcançar nenhum dos dois — o fixture não faria efeito, a suíte continuaria escrevendo
na `data/` real e **passaria**, que é o pior desfecho possível para um conserto de isolamento. Os
escritores importam o **módulo** (`from . import config`) e chamam `config.data_dir()`: aí existe um
único ponto de resolução, e patchá-lo vale para todos os chamadores de uma vez. É esse
comportamento — e não o monkeypatch — que o `test_diretorio_de_dados_resolvido_na_chamada` fixa.

Consertar isso **antes** da SPEC 007 não é ordem arbitrária: com o registro de metadados dentro dos
runners, o estrago cresceria — a suíte passaria a gravar também no JSON de metadados versionado,
com entradas originadas de teste, metadado mentindo sobre quando o dado foi extraído. Que é
justamente o que a 007 existe para tornar confiável.

**Com uma exceção obrigatória: os testes `integration`.** São **8 testes marcados
`@pytest.mark.integration`, em 8 arquivos sobre 6 pacotes de domínio** (`logradouros_match` ×3
arquivos, `address_geocod`, `lote_geocod`, `logradouro_geocod`, `contribuinte_match`,
`codlog_match`), e a razão de existir
deles é justamente rodar **contra os parquets reais de `data/`** — redirecionar o diretório para
eles esvaziaria o teste e o faria falhar por arquivo inexistente. O fixture consulta o **marker** do
teste e não redireciona quando ele é `integration`; é por marker, e não por lista de módulos,
justamente porque a lista cresce. A divisão fica exata e explicável: teste unitário nunca toca
`data/`; teste de integração lê `data/` e **nunca escreve** (nenhum deles chama `run()`).

**O que entra no `.gitignore` é só `data/*.tmp`.** Parquets e JSON **permanecem versionados**, por
decisão explícita: nesta fase, `git pull` + `runserver` precisa levantar a aplicação com dado real,
sem esperar os minutos de extração do GeoSampa. O temporário é o único que não representa estado
válido de nada, e é o único ignorado.

## Peças de referência a compor

- `@services/scripts/*/runner.py` → os quatro `run()`: adotam a assinatura do `ScriptRunner`
  (`Config` + `verbose`). A lógica de extração — extractors, `_to_columns`, `pipeline` do augment —
  **não muda**.
- `@services/scripts/*/models.py` → os três scripts de WFS já têm a classe, mas com o nome antigo:
  `EnderecosFiscaisRequest`, `SegmentosLogradourosRequest` e `NomesLogradourosRequest` **são
  renomeadas** para `EnderecosFiscaisConfig`, `SegmentosLogradourosConfig` e
  `NomesLogradourosConfig` — não é criação, é rename. Cada uma ganha os campos que hoje andam
  soltos na assinatura do `run()` (`WfsConnectionConfig`, `WfsRetryPolicy`); ambos já são
  `BaseModel`, então entram como campo sem adaptação. O `augment_tipos_logradouro` é o caso
  diferente: **não existe** classe nenhuma hoje (só há `AugmentStats`, o resultado) — o
  `AugmentConfig` não é rename, é **criado do zero** aqui.
- `@apps/logradouro_matcher/management/commands/extrair_nomes_logradouros.py`,
  `@apps/address_geocoder/management/commands/extrair_segmentos_logradouros.py`,
  `@apps/address_geocoder/management/commands/extrair_enderecos_fiscais.py` → os três já expõem
  `--verbose` e já usam `build_connection_config`/`build_retry_policy`; passam a montar o `Config`
  completo com o que hoje entregam solto.
- `@apps/logradouro_matcher/management/commands/augment_logradouro_types.py` → o único sem
  `add_arguments`; ganha `--verbose` e o `Config`, permanecendo fino.
- `@services/utils/io` → `write_parquet_to_data` / `write_json_to_data` / `read_parquet_from_data` /
  `read_json_from_data`: já resolvem `data/`. Aqui deixam de ser `partial` congelada no import e a
  escrita atômica entra num helper compartilhado pelos dois escritores. A ordem dos argumentos de
  cada um **é preservada** (os `partial` de JSON são posicionais e os de parquet são por keyword):
  nenhum chamador de hoje muda. De passagem, a assinatura de `write_json_to_folder` (hoje com os
  três parâmetros agrupados numa linha) é reformatada para **um parâmetro por linha**, conforme
  §7.2 do CLAUDE.md — o arquivo já é tocado por esta SPEC.
- `@tests/conftest.py` → já tem o fixture `autouse` que reseta os catálogos singleton; é onde entra,
  no mesmo molde, o redirecionamento do diretório de dados para um temporário.
- `@.gitignore` → ganha `data/*.tmp` (sobra de escrita atômica interrompida por `kill -9`).
- `@.claude/skills/management-commands/SKILL.md` → "Anatomia do script": é onde entra o contrato
  `ScriptRunner`, junto dos helpers de `services.utils.io` que já estão documentados ali. O exemplo
  de `handle()` da skill mostra a assinatura antiga do `run()` e precisa acompanhar.

## Snippets sugeridos

```python
# services/scripts/contrato.py — módulo solto no topo: infraestrutura, não é varrido
Cfg = TypeVar("Cfg", bound=BaseModel, contravariant=True)
Res = TypeVar("Res", bound=BaseModel, covariant=True)


class ScriptRunner(Protocol[Cfg, Res]):
    """Todo script de carga entra por aqui: um Config e a chave do pipeline."""

    def __call__(self, config: Cfg, *, verbose: bool = False) -> Res: ...


# services/scripts/<nome>/runner.py — assinatura do contrato
def run(config: EnderecosFiscaisConfig, *, verbose: bool = False) -> EnderecosFiscaisResult:
    fetcher = WfsFetcher(config.conexao, retry_policy=config.retry, verbose=verbose)
    rows = EnderecosFiscaisExtractor(fetcher)(config)
    output_path = write_parquet_to_data(_to_columns(rows), OUTPUT_FILENAME)
    return EnderecosFiscaisResult(total_records=len(rows), output_path=output_path)


# contrato verificado pelo mypy — assinatura divergente não passa no `uv run mypy .`
_contrato: ScriptRunner[EnderecosFiscaisConfig, EnderecosFiscaisResult] = run


# services/scripts/<nome>/models.py — o que era parâmetro solto vira campo do Config.
# Sem default o que o comando lê de settings; COM default o que é constante do script.
class EnderecosFiscaisConfig(BaseModel):
    layer_name: str
    conexao: WfsConnectionConfig       # antes: 1º parâmetro posicional de run()
    retry: WfsRetryPolicy              # antes: kwarg de run()


# services/scripts/augment_tipos_logradouro/models.py — Config NOVO (hoje só existe AugmentStats)
class AugmentConfig(BaseModel):
    input_json_name: str = TIPOS_LOGRADOURO_AUMENTADO_MANUAL
    input_parquet_name: str = PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL
    output_parquet_name: str = OUTPUT_PARQUET_NAME


class AugmentStats(BaseModel):
    n_original: int
    n_variacoes: int
    n_total: int
    tipos_nao_mapeados: list[str] = []
    # só apurado quando verbose: {"AVENIDA": 47, ...} — quem imprime é o comando
    variacoes_por_tipo: dict[str, int] | None = None


# services/utils/io/ — atomicidade num lugar só; parquet e JSON passam por aqui
def escrever_atomico(path: Path, escrever: Callable[[Path], None]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    # MESMA pasta (rename atômico exige mesmo filesystem) e PID no nome: o daemon da SPEC 007 e um
    # comando manual podem escrever o mesmo artefato ao mesmo tempo sem compartilhar temporário.
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        escrever(tmp)
        os.replace(tmp, path)                  # POSIX: atômico e sobrescreve o destino
    except BaseException:
        tmp.unlink(missing_ok=True)            # não deixa sobra em data/
        raise
    return path


# services/utils/io/ — o diretório é resolvido NA CHAMADA, não congelado no import.
# Importa-se o MÓDULO, não o nome: `from .config import data_dir` criaria uma ligação própria aqui
# e o monkeypatch do conftest não alcançaria este chamador (falharia em silêncio).
from . import config


def write_parquet_to_data(columns: Columns, filename: str) -> Path:
    return write_parquet(columns, filename, folder=config.data_dir())


# tests/conftest.py — redireciona a data/, MENOS para os testes marcados `integration`
@pytest.fixture(autouse=True)
def _isolar_diretorio_de_dados(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Testes `integration` leem os parquets reais por definição (e nunca escrevem):
    # redirecioná-los esvaziaria o teste. A exceção é pelo marker, nunca por lista de módulos.
    if request.node.get_closest_marker("integration"):
        return
    # Alcança todos os escritores porque eles chamam `config.data_dir()` pelo módulo.
    monkeypatch.setattr(io_config, "data_dir", lambda: tmp_path)


# tests/services/scripts/test_contrato.py — a rede grossa: descoberta, sem lista fixa
def test_todo_runner_de_script_segue_o_contrato() -> None:
    # Regra topológica: SUBPACOTE de services/scripts/ é script de carga e tem que expor run();
    # módulo solto no topo (contrato.py, e o que a SPEC 007 trouxer) é infraestrutura, não é varrido.
    for pacote in subpacotes_de("services.scripts"):
        run = getattr(import_module(f"services.scripts.{pacote}"), "run", None)
        assert run is not None, f"{pacote}: subpacote de scripts sem run() exposto"
        params = signature(run).parameters
        assert list(params)[0] == "config"
        assert params["verbose"].kind is Parameter.KEYWORD_ONLY
        assert params["verbose"].default is False


# apps/*/management/commands/<etapa>.py — o comando monta o Config completo
config = EnderecosFiscaisConfig(
    layer_name=settings.WFS_LAYER_LOTE_CIDADAO,
    conexao=build_connection_config(settings),   # antes ia solto no run()
    retry=build_retry_policy(settings),          # idem
)
result = run(config, verbose=bool(options["verbose"]))
```

## Fora de escopo

- **Registro de metadados de execução** (`data/*.json` com `status`/`last_run`/`registros`), a chave
  `manual` do contrato e a flag `--automatico` dos comandos → SPEC 007. Aqui o contrato nasce com
  uma chave só (`verbose`), porque `manual` sem o registro seria parâmetro morto.
- **Comando one-shot de pipeline e daemon de atualização** → SPEC 007.
- Mudar a lógica dos `Catalog`, refresh de cache em runtime ou TTL: continua valendo a skill
  `catalogos-lookup`.
- Mudar a lógica de extração de qualquer script — extractors, `_to_columns` e o `pipeline` do
  `augment` ficam intocados. Esta SPEC mexe na **porta**, não no que acontece atrás dela.
- `fsync`/durabilidade contra queda de energia; backup, rollback ou retenção da carga anterior.
- Adicionar `pytest-django` ou testar os management commands: comando fino não se testa (skill
  `management-commands`), e o alvo aqui é `services/`.

## Testes (TDD)

- `test_todo_runner_de_script_segue_o_contrato` — varrendo `services/scripts/` por descoberta, todo
  **subpacote** expõe um `run()` com a assinatura do `ScriptRunner` (`config` + `verbose`
  keyword-only com default `False`); subpacote sem `run()` reprova, e módulo solto no topo não é
  varrido. Script novo que não se declarou aderente ao `Protocol` — caso cego para o `mypy` —
  quebra a suíte aqui.
- `test_escrita_interrompida_preserva_arquivo_anterior` — com um escritor que levanta no meio, o
  arquivo que já existia continua íntegro, a exceção propaga e nenhum `.tmp` fica para trás.
- `test_diretorio_de_dados_resolvido_na_chamada` — redirecionar o diretório de dados **depois** do
  import passa a valer para o próximo `write_parquet_to_data`/`read_parquet_from_data`, **sem
  patchar módulo de IO nenhum além do ponto único de resolução**. É o comportamento que sustenta o
  fixture `autouse` — o que o `partial` impede hoje, e o que um `from .config import data_dir`
  voltaria a impedir em silêncio.
- `test_run_normaliza_chaves` *(refeito)* — sobre insumos sintéticos no diretório temporário: as
  chaves do dicionário de tipos saem normalizadas no parquet de saída. Mesma asserção de hoje, sem
  tocar a `data/` real nem depender de a base conter "Avenida".
- `test_run_idempotente` *(refeito)* — duas execuções sobre o mesmo insumo sintético produzem as
  mesmas contagens.
- `test_augment_verbose_apura_variacoes_por_tipo` — com `verbose=True` o `AugmentStats` traz a
  contagem de variações por tipo; sem ele, não traz. Fixa que o verbose do `augment` apura e
  devolve, em vez de imprimir.

## Patches

_Nenhum patch registrado até o momento._
