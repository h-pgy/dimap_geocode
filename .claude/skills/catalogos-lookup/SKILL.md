---
name: catalogos-lookup
description: Como consumir os catálogos cacheados em memória do DIMAP GeoCoder (services/domain/*/catalog.py, singletons aquecidos no startup do processo web). Use SEMPRE que precisar buscar dados das bases oficiais em tempo de request (sugestões, matching, geocodificação) — nunca leia os parquets de data/ diretamente numa view ou domínio, e nunca instancie/acople código novo fora da interface do Catalog.
---

# Catálogos de lookup — `services/domain/*/catalog.py`

Em runtime, os dados oficiais de **logradouros** e **endereços fiscais/lotes** não vêm do banco:
vêm de catálogos em memória, carregados a partir dos parquets de `data/` e **aquecidos** na subida
do processo web (`[LogradouroCatalog] aquecendo cache...` / `[ContribuinteCatalog] aquecendo
cache...` no stdout — não é erro). Cada domínio tem o **seu** `Catalog`; não existe um módulo
central `services/utils/cache.py` de catálogos — esse arquivo só tem o mecanismo genérico de TTL
(`ttl_cached_property`) usado por todos eles.

## Regras inegociáveis

- **Nunca ler `data/*.parquet` direto** em view ou domínio — todo acesso passa por um `Catalog`.
- **Nunca acoplar fora da interface pública do `Catalog`** (métodos como `linhas_por_nome`,
  `enderecos_fiscais_com_chave`, não os `DataFrame`/`dict` internos). Os catálogos in-memory são o
  **desenho definitivo** para este app (Redis foi avaliado e descartado — app de uso interno,
  dados read-only, fuzzy exige corpus in-process). Se um dia houver pressão de memória, o lookup
  migra para o Postgres da stack; código que só usa a interface pública sobrevive a essa troca.
- As **chaves** textuais são geradas com a normalização única (skill `normalize-text`) — qualquer
  consulta normaliza a entrada com a mesma função antes do lookup.
- **Cada `Catalog` é um singleton de fato** (via `__new__`): `XCatalog()` em qualquer ponto do
  código sempre devolve a mesma instância aquecida. Nunca guarde estado próprio pensando que é uma
  cópia isolada — não é.

## O que existe

| Catalog | Onde | Indexa (parquets de `data/`) | Interface pública |
|---|---|---|---|
| `LogradouroCatalog` | `services/domain/logradouros_match/catalog.py` | `tipos_logradouro_cache.parquet` (variações de tipo → código) + `nomes_logradouros.parquet` (codlog/tipo/nome) | `variacoes_tipo`, `codigo_da_variacao(variacao)`, `linhas_do_tipo(codigo)`, `todas_as_linhas()`, `linhas_por_nome(nome, codigo)` |
| `ContribuinteCatalog` | `services/domain/contribuinte_match/catalog.py` | `enderecos_fiscais.parquet` (lotes + endereço fiscal por contribuinte) | `enderecos_fiscais` (DataFrame, prefixo setor/quadra/lote), `enderecos_fiscais_com_chave` (idem + `chave_numero_porta` e `codlog5` prontos para lookup de endereço fiscal exato) |

Não há catálogo próprio para **lotes via WFS** (`lote_geocod` consulta o GeoServer ao vivo por
`CqlFilter`, sem parquet) nem para **codlog** isolado: `CodlogMatcher`
(`services/domain/codlog_match/matcher.py`) ainda lê `nomes_logradouros.parquet` na própria
`ttl_cached_property`, **sem** seguir o padrão `Catalog` e **sem** warmup — é dívida conhecida,
fora de escopo da SPEC que introduziu esse padrão (`SPECS/infraestrutura/003-catalog-eager-warmup.md`).
Se for tocar nesse matcher, não assuma que ele já é um `Catalog` singleton.

## Ciclo de vida

- **Onde aquece:** `services/domain/warmup.py::aquecer_catalogos()` chama
  `logradouro_catalog.aquecer()` e `contribuinte_catalog.aquecer()`. É chamada **só** em
  `config/wsgi.py` e `config/asgi.py`, logo após `application = get_wsgi/asgi_application()` —
  **não** em `AppConfig.ready()`. Isso garante que só processos que servem requests pagam o
  aquecimento: o pai do autoreloader do `runserver` e qualquer management command
  (`migrate`, `shell`, comandos do pipeline) não tocam nisso.
- **TTL:** cada `Catalog` usa `ttl_cached_property` com TTL próprio —
  `LogradouroCatalog` 24h (`DATA_TTL_SECONDS = 24*60*60`), `ContribuinteCatalog` 1h
  (`DATA_TTL_SECONDS = 3600`). Passado o TTL, o próximo acesso relê o parquet **dentro** do ciclo
  de request (lazy) — não há refresh assíncrono.
- **Forçar refresh após rodar o pipeline de dados:** não existe management command dedicado.
  O jeito real é **reiniciar o processo web** (reimporta `config/wsgi.py`/`asgi.py`, que chama
  `aquecer_catalogos()` de novo); sem restart, o catálogo se autoatualiza de forma lazy só quando
  o TTL expira.
- **Em scripts/management commands:** como o warmup não roda fora de wsgi/asgi, qualquer código
  que use um matcher num script paga a leitura do parquet no primeiro acesso (comportamento
  lazy padrão do `ttl_cached_property`) — normal e esperado fora do ciclo web.
- **Em testes:** um fixture `autouse` em `tests/conftest.py` chama
  `LogradouroCatalog.resetar_instancia()` / `ContribuinteCatalog.resetar_instancia()` antes e
  depois de cada teste, para que o cache TTL de um teste não vaze para o próximo. Fakes de teste
  sobem como **subclasses** do `Catalog` real (`class FakeLogradouroCatalog(LogradouroCatalog)`) —
  o singleton só se aplica à classe exata, então uma subclasse constrói normalmente, sem herdar a
  instância única nem virar singleton ela mesma.

## Uso típico

```python
from services.domain.logradouros_match import logradouro_catalog

# sugestão por tipo + nome parcial (já normalizado/tokenizado a montante pelo matcher)
codigo = logradouro_catalog.codigo_da_variacao("AV")
linhas = logradouro_catalog.linhas_do_tipo(codigo)          # todas as linhas do tipo AVENIDA
linhas_exatas = logradouro_catalog.linhas_por_nome("PAULISTA", codigo)
```

```python
from services.domain.contribuinte_match import contribuinte_catalog

# prefixo de contribuinte (setor/quadra/lote) — o matcher monta a mask, não o catalog
df = contribuinte_catalog.enderecos_fiscais
mask = df["cd_setor_fiscal"].str.startswith("001") & df["cd_quadra_fiscal"].str.startswith("002")
resultado = df[mask].head(5)
```

Na prática, quase sempre você **não** chama o `Catalog` direto — você chama o `Matcher` do
domínio (`LogradouroMatcher`, `ContribuinteMatcher`, `EnderecoFiscalMatcher`), que já injeta o
catalog por composição (`catalog: XCatalog | None = None`, default `XCatalog()` → a instância
única) e monta a query/mask correta. Acesse o `Catalog` diretamente só se estiver **escrevendo**
um matcher novo.

## Relação com o pipeline de dados

Os catálogos consomem o que os management commands de extração produzem em `data/`:
`extrair_nomes_logradouros` → `nomes_logradouros.parquet`, `augment_logradouro_types` →
`tipos_logradouro_cache.parquet` (depende do anterior), `extrair_enderecos_fiscais` →
`enderecos_fiscais.parquet`. Se o resultado de uma busca parecer desatualizado, a causa provável é
parquet velho (rodar o comando de novo) ou catálogo aquecido antes do refresh (reiniciar o
processo web).
