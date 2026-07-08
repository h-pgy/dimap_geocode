---
name: management-commands
description: Padrão de management commands e do pipeline de dados do DIMAP GeoCoder. Use ao criar/alterar um comando do manage.py ou ao rodar o pipeline de cargas (bases oficiais → variações → cache) — o comando é sempre fino (parsing + chamada ao script de services/scripts + feedback) e a lógica vive no script.
---

> **RASCUNHO — validar contra o código antes de promover a `.claude/skills/`.**
> Este conteúdo absorve o §8 do CLAUDE.md atual. Fontes: `apps/*/management/commands/` e
> `services/scripts/`.

# Management commands — comando fino, lógica no script

## A regra (inegociável, do CLAUDE.md)

O comando **só** faz três coisas: parsing de argumentos, chamada ao script em
`services/scripts/`, feedback no stdout. Nenhuma regra de negócio no comando. Scripts nunca
rodam durante request/response.

## Padrão

```python
from django.core.management.base import BaseCommand
from services.scripts import load_logradouros


class Command(BaseCommand):
    help = "Carrega os logradouros oficiais da PMSP a partir do GeoSampa."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--source", type=str, default="geosampa")

    def handle(self, *args: object, **options: object) -> None:
        total = load_logradouros.run(source=options["source"])
        self.stdout.write(self.style.SUCCESS(f"{total} logradouros carregados."))
```

Quando o script consome integrações (WFS/WMS), **é o comando que lê o `settings`** e injeta os
DTOs de config no script — o domínio nunca lê settings (ver skill `wfs-fetcher`, seção
"Orquestração", que traz o padrão real de `extrair_nomes_logradouros`).

## O pipeline de dados (ordem importa)

```
1. cargas das bases oficiais   (logradouros, endereços fiscais, lotes → data/*.parquet)
2. geração de variações        (sobre logradouros e endereços fiscais; nunca sobre lotes)
3. refresh do cache de lookup  (o que os catálogos em memória consomem — skill catalogos-lookup)
```

TODO: tabela com os comandos reais existentes (nome do comando → script → artefato em `data/`):

| Comando | Script | Produz |
|---|---|---|
| `extrair_nomes_logradouros` (TODO: confirmar) | `services/scripts/logradouros` | `data/nomes_logradouros.parquet` |
| TODO | `services/scripts/segmentos_logradouros` | `data/segmentos_logradouros.parquet` |
| TODO | `services/scripts/enderecos_fiscais` | `data/enderecos_fiscais.parquet` |
| TODO | `services/scripts/augment_tipos_logradouro` | `data/tipos_logradouro_aumentado.json` / `_cache.parquet` |

## Onde criar

Em `management/commands/` do **app de domínio mais próximo do dado** (ex.: extração de
logradouros vive em `apps/logradouro_matcher`). Execução sempre via `uv run python manage.py
<comando>`.
