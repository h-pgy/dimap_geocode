---
name: catalogos-lookup
description: Como consumir os catálogos cacheados em memória do DIMAP GeoCoder (services/utils/cache.py e catálogos de logradouros/endereços/lotes com warmup eager). Use SEMPRE que precisar buscar dados das bases oficiais em tempo de request (sugestões, matching, geocodificação) — nunca leia os parquets de data/ diretamente numa view ou domínio, e nunca acople código novo fora da interface de lookup.
---

> **RASCUNHO — validar contra o código antes de promover a `.claude/skills/`.**
> Fontes: `services/utils/cache.py`, SPEC `SPECS/infraestrutura/003-catalog-eager-warmup.md`
> e os pontos de consumo em `services/domain/*`.

# Catálogos de lookup — `services.utils.cache`

Em runtime, os dados oficiais (logradouros, endereços fiscais, lotes) **não vêm do banco**: vêm
de catálogos em memória, carregados a partir dos parquets de `data/` com **warmup eager** na
subida do processo (é o `[LogradouroCatalog] aquecendo cache...` que aparece no stdout — não é
erro).

## Regras inegociáveis

- **Nunca ler `data/*.parquet` direto** em view ou domínio — todo acesso passa pelo catálogo.
- **Nunca acoplar fora da interface de lookup.** Os catálogos in-memory são o **desenho
  definitivo** (Redis foi avaliado e descartado em 2026-07-07 — app de uso interno, dados
  read-only, fuzzy exige corpus in-process; ver `revisao_srd/01-diagnostico.md` §7). A interface
  ainda importa: se um dia houver pressão de memória, lookups exatos/prefixo migram para o
  PostgreSQL da stack — código acoplado à estrutura interna do dict/DataFrame quebra essa saída.
- As **chaves** dos catálogos são geradas com a normalização única (`normalize-text`) — qualquer
  consulta textual normaliza a entrada com a mesma função antes do lookup.

## O que existe

TODO: mapear e documentar cada catálogo e sua interface pública:

| Catálogo | O que indexa | Interface (métodos/callable) |
|---|---|---|
| `LogradouroCatalog` (TODO: nome exato) | variações de nome → codlog | TODO |
| catálogo de endereços fiscais | TODO | TODO |
| catálogo de lotes/contribuintes | TODO | TODO |
| `tipos_logradouro` (data/tipos_logradouro_cache.parquet) | TODO | TODO |

## Ciclo de vida

TODO: documentar o warmup eager (onde é disparado — AppConfig.ready? — e o que ele custa),
como forçar refresh após rodar o pipeline de dados, e o comportamento em testes (o aquecimento
roda no `manage.py shell`/pytest? como evitar/paguar esse custo?).

## Uso típico

```python
# TODO: exemplo real de consulta de sugestão (prefixo de contribuinte, nome parcial de rua)
```

## Relação com o pipeline de dados

Os catálogos consomem o que os scripts de `services/scripts/` produzem em `data/` (cargas →
variações → cache; ver skill `management-commands`). Se o resultado de uma busca parecer
desatualizado, a causa provável é parquet velho ou warmup anterior ao refresh.
