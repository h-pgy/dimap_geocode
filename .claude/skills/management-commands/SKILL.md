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
from services.scripts.segmentos_logradouros import SegmentosLogradourosRequest, run


class Command(BaseCommand):
    help = "Extrai ... do WFS para data/segmentos_logradouros.parquet."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        config = build_connection_config(settings)
        retry_policy = build_retry_policy(settings)
        request = SegmentosLogradourosRequest(layer_name=settings.WFS_LAYER_LOGRADOUROS)
        result = run(config, request, retry_policy=retry_policy, verbose=bool(options["verbose"]))
        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído. {result.total_segments} segmentos salvos em {result.output_path}"
            )
        )
```

Nem todo comando tem essa cara — há comandos sem `settings`, sem argumentos, sem rede, e haverá
comandos que não extraem nada. O que **não** varia:

- **Quem lê `settings` é o comando** (§3.3). O que o script precisa de configuração — camada, CRS,
  caminho — entra como campo do `...Request`.
- **Use os factories da integração** quando houver (`build_connection_config`,
  `build_retry_policy` de `services.integrations.wfs`); não remonte DTOs de config campo a campo.
- **Tipagem integral** (§7.2): `parser: ArgumentParser`, `*args: object, **options: object`,
  `-> None`. `mypy` e `ruff` limpos.
- **`run()` devolve um DTO Pydantic**; o comando **formata**, não recalcula. Se o script tem algo a
  dizer (contagens, itens não mapeados, avisos), isso vai no DTO de resultado — **o script não
  escreve em stdout**, quem decide o que vira `SUCCESS`/`WARNING` na tela é o comando.
- **Rotina longa expõe `--verbose`** e repassa ao script; extrações do GeoSampa levam minutos e sem
  isso não há sinal de progresso.

## Anatomia do script (`services/scripts/<nome>/`)

| Arquivo | Conteúdo |
|---|---|
| `models.py` | DTOs Pydantic: `...Request` (input) e `...Result` (output). §7.1: DTO nas duas pontas. |
| `extractor.py` | A lógica: **classe callable**, recebendo suas dependências **por composição** no `__init__` e tipadas como `Callable` — não como a classe concreta. É o que torna o teste barato. |
| `constants.py` | Constantes do script, quando houver. |
| `runner.py` | `run()`: a fachada do script — monta as dependências, chama o extractor, persiste e devolve o `...Result`. |
| `__init__.py` | **Só reexporta** (`run`, `OUTPUT_FILENAME`, símbolos públicos em `__all__`) — **nunca implementa** (§7.2). |

A escrita usa os helpers de `services.utils.io` (`write_parquet_to_data`, `write_json_to_data`), que
já resolvem `data/` — não monte `Path` para `data/` nem no script nem no comando, e não passe a
pasta de destino pelo `...Request`.

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

## Erros comuns

- Instanciar cliente de integração ou ler `data/` **direto no comando** — a lógica migra pro comando
  e deixa de ser testável sem Django.
- Ler `settings` **dentro** de `services/` — quebra §3.3.
- Hardcodar nome de camada, CRS ou caminho de `data/` no script.
- Fazer o script imprimir em stdout.
- Criar um comando de "refresh de cache" ou disparar aquecimento a partir de um comando.
