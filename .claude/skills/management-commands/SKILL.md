---
name: management-commands
description: Padrão de management commands e do pipeline de dados do DIMAP GeoCoder. Use ao criar/alterar um comando do manage.py ou ao rodar o pipeline de cargas (bases oficiais → variações/cache → restart do web) — o comando é sempre fino (parsing + leitura de settings + chamada ao script de services/scripts + feedback) e a lógica vive no script.
---

# Management commands — comando fino, lógica no script

## A regra (inegociável, CLAUDE.md §6.4)

O comando é a **fronteira entre o Django e o domínio**, e faz só o que essa fronteira exige:

- **parsing de argumentos** (`add_arguments`);
- **leitura de `settings`**, traduzida nos DTOs de configuração que o script pede;
- **chamada ao `run()`** do script em `services/scripts/`;
- **feedback no stdout**, formatando o DTO de resultado.

Nenhuma regra de negócio, nenhum IO, nenhum cálculo no comando — se você precisou de um `if` sobre
o dado, ele é do script. O comando é o **único** lugar do pipeline que conhece Django; scripts
**nunca** rodam durante request/response.

## O padrão

Exemplo real (`apps/address_geocoder/management/commands/extrair_segmentos_logradouros.py`):

```python
from argparse import ArgumentParser

from django.conf import settings
from django.core.management.base import BaseCommand

from services.integrations.wfs import build_connection_config, build_retry_policy
from services.scripts.segmentos_logradouros import SegmentosLogradourosConfig, run


class Command(BaseCommand):
    help = "Extrai ... do WFS para data/segmentos_logradouros.parquet."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        config = SegmentosLogradourosConfig(
            layer_name=settings.WFS_LAYER_LOGRADOUROS,
            conexao=build_connection_config(settings),
            retry=build_retry_policy(settings),
        )
        result = run(config, verbose=bool(options["verbose"]))
        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído. {result.total_segments} segmentos salvos em {result.output_path}"
            )
        )
```

Nem todo comando tem essa cara — há comandos sem `settings`, sem argumentos, sem rede, e haverá
comandos que não extraem nada. O que **não** varia:

- **Quem lê `settings` é o comando** (§3.3). O que o script precisa de configuração — camada, CRS,
  conexão, política de retry — entra como campo do `...Config`, montado **inteiro** pelo comando.
- **Use os factories da integração** quando houver (`build_connection_config`,
  `build_retry_policy` de `services.integrations.wfs`); não remonte DTOs de config campo a campo.
- **Tipagem integral** (§7.2): `parser: ArgumentParser`, `*args: object, **options: object`,
  `-> None`. `mypy` e `ruff` limpos.
- **`run()` devolve um DTO Pydantic**; o comando **formata**, não recalcula. Se o script tem algo a
  dizer (contagens, itens não mapeados, avisos), isso vai no DTO de resultado — **o script não
  escreve em stdout**, quem decide o que vira `SUCCESS`/`WARNING` na tela é o comando.
- **Todo comando do pipeline expõe `--verbose`** e repassa ao `run()` (SPEC ingestao_dados/006) —
  extrações do GeoSampa levam minutos e sem isso não há sinal de progresso. Verbose não é
  "imprimir mais": é o script **apurar e devolver mais** no DTO de resultado (ex.: contagem de
  variações por tipo do `augment`); quem imprime continua sendo o comando.

## O contrato `ScriptRunner` (SPEC ingestao_dados/006)

**Todo `run()` de script de carga entra por uma assinatura só**, declarada como `Protocol` genérico
em `services/scripts/contrato.py`:

```python
def run(config: XConfig, *, verbose: bool = False) -> XResult: ...
```

- **`config` é o único parâmetro posicional** e é um DTO Pydantic — o que hoje entraria solto por
  parâmetro (conexão WFS, política de retry, nomes de arquivo) é **campo do `Config`**: sem default
  o que o comando lê de `settings`; **com** default o que é constante do próprio script (assim o
  comando não precisa importar constante do script só para devolvê-la).
- **`verbose` é sempre keyword-only, com default `False`.**
- Cada `runner.py` declara aderência ao protocolo, e o `mypy` confere:
  ```python
  _contrato: ScriptRunner[XConfig, XResult] = run
  ```
- **Um teste varre `services/scripts/` por descoberta** (`tests/services/scripts/test_contrato.py`)
  e falha se algum `run()` divergir — pega o caso que o `mypy` não pega: um `runner.py` que
  simplesmente esqueceu de se declarar aderente ao `Protocol`. A regra é **estrutural**: todo
  **subpacote** de `services/scripts/` é script de carga e expõe `run()`; **módulo solto** no topo
  (`contrato.py`, e o que vier depois) é infraestrutura do pipeline e não é varrido — não é lista
  de exceção, é a estrutura de diretórios.

Escrever um runner novo é **compor** este contrato — nunca inventar uma assinatura diferente
"porque este script é diferente"; o que varia entre scripts é o `Config`, nunca a forma do `run()`.

## Anatomia do script (`services/scripts/<nome>/`)

| Arquivo | Conteúdo |
|---|---|
| `models.py` | DTOs Pydantic: `...Config` (input, aderente ao `ScriptRunner`) e `...Result` (output). §7.1: DTO nas duas pontas. |
| `extractor.py` | A lógica: **classe callable**, recebendo suas dependências **por composição** no `__init__` e tipadas como `Callable` — não como a classe concreta. É o que torna o teste barato. |
| `constants.py` | Constantes do script, quando houver. |
| `runner.py` | `run()`: a fachada do script — monta as dependências, chama o extractor, persiste e devolve o `...Result`. Aqui mora a declaração `_contrato: ScriptRunner[...] = run`. |
| `__init__.py` | **Só reexporta** (`run`, `OUTPUT_FILENAME`, símbolos públicos em `__all__`) — **nunca implementa** (§7.2). |

A escrita usa os helpers de `services.utils.io` (`write_parquet_to_data`, `write_json_to_data`), que
já resolvem `data/` **e escrevem atomicamente** (temporário próprio do processo, promovido por
`os.replace` — quem lê nunca vê um arquivo pela metade). Não monte `Path` para `data/` nem no
script nem no comando, e não passe a pasta de destino pelo `...Config`.

## Depois de rodar (§6.4: cargas → variações → cache)

Os comandos formam um **pipeline encadeado** — os que geram variações e caches consomem os parquets
das cargas. Antes de rodar um, veja de que artefato de `data/` ele depende (está no `...Request` ou
nas constantes do script): rodar fora de ordem não costuma quebrar, produz cache a partir de dado
velho, que é pior.

**Nenhum comando faz refresh de cache em runtime, e não deve fazer.** Os catálogos são singletons
aquecidos na subida do processo web; para o site enxergar o parquet novo, **reinicie o processo** —
sem isso a releitura só acontece quando o TTL expira. Ver skill `catalogos-lookup`.

Execução sempre via `uv run python manage.py <comando>` (§8).

## Testes (§9)

O alvo é o **script**, não o comando: `tests/services/scripts/<nome>/test_extractor.py`, exercitando
o extractor com um **fake** no lugar da dependência injetada (uma função que devolve fixtures).
Como o extractor depende de um `Callable`, o teste não precisa de rede, de Django nem de banco.
Comando fino não se testa — não há comportamento próprio nele para fixar.

**Nenhum teste escreve na `data/` real** (SPEC ingestao_dados/006): um fixture `autouse` em
`tests/conftest.py` redireciona `write_parquet_to_data`/`write_json_to_data`/`read_parquet_from_data`
para um diretório temporário, exceto para testes marcados `@pytest.mark.integration` (que leem os
parquets reais por definição e nunca escrevem). Teste de `run()` monta seus próprios insumos
sintéticos com os mesmos helpers de `services.utils.io` — nunca lê nem reescreve o parquet/JSON
versionado de produção.

## Erros comuns

- Instanciar cliente de integração ou ler `data/` **direto no comando** — a lógica migra pro comando
  e deixa de ser testável sem Django.
- Ler `settings` **dentro** de `services/` — quebra §3.3.
- Hardcodar nome de camada, CRS ou caminho de `data/` no script.
- Fazer o script imprimir em stdout.
- Criar um comando de "refresh de cache" ou disparar aquecimento a partir de um comando.
