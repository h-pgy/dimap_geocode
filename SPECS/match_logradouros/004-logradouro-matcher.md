---
spec: match-logradouros/004
versao: v4
atualizado_em: 2026-06-22
changelog:
  - v1: versão inicial
  - v2: trata entrada sem tipo de logradouro (fast-forward direto para o match de nome)
  - v3: resultado é sempre uma lista de logradouros casados + flag de resultado múltiplo (homônimos)
  - v4: TTL de 24h no cache do catálogo (alinhado ao cron que atualiza os dados)
  - v5: fonte dos tipos passa a ser tipos_logradouro_cache.parquet (nome_tipo + cd_tipo_logradouro);
        dispensa os dois JSONs; remove tipo_nome (sem tradução código→nome)
---

# SPEC match-logradouros/004 — Matcher de Logradouros (texto de input de usuario → codlog)

## User story

Como usuário do sistema, quero poder inputar uma rua/logradouro do jeito que eu sei escrever ele e que o sistema retorne o codlog correspondente sem eu eu ter que saber escrever ele exatamente igual.

Para isso, desenvolver um módulo de domínio que receba texto único (tipo + nome de logradouro) e resolva o **codlog** correspondente via fuzzy matching, para que a aplicação consiga transformar o que o usuário digitou em um identificador exato de logradouro — mesmo quando ele erra o tipo ou a grafia do nome.

## Critérios de aceite

* [ ] Código fonte implementado em `services/domain/logradouros_match`.
* [ ] O `__init__.py` do módulo expõe apenas a instância callable do matcher e os DTOs de entrada
      e saída; submódulos internos não são alcançados de fora.
* [ ] O matcher recebe um DTO Pydantic com o texto único e devolve um DTO Pydantic com o resultado.
* [ ] O texto é quebrado no **primeiro espaço**: o primeiro elemento é o tipo de logradouro e o
      restante (unificado) é o nome do logradouro.
* [ ] Quando o texto **não tem espaço** (o usuário não informou tipo, ex.: `"paulista"`), o
      módulo faz **fast-forward**: pula o match de tipo e resolve o nome diretamente sobre **todos**
      os logradouros, sem filtro de tipo. Nesse caso `match_tipo` é `None` e `ignorou_filtro_tipo`
      é `False` (não houve tipo a ignorar).
* [ ] O tipo é resolvido por match **Levenshtein** contra as variações da coluna `nome_tipo` de
      `data/tipos_logradouro_cache.parquet`, recuperando o **código** do tipo (coluna
      `cd_tipo_logradouro`, ex.: `AV`).
* [ ] Os logradouros de `data/nomes_logradouros.parquet` são filtrados pelo código do tipo (mesma
      coluna `cd_tipo_logradouro`), e o nome é resolvido por match **Jaro-Winkler** sobre esse
      subconjunto.
* [ ] Existe um **threshold** no match de nome: se o melhor score ficar abaixo dele (ou o
      subconjunto do tipo for vazio), o match é refeito sobre **todos** os logradouros, ignorando o
      filtro de tipo.
* [ ] O DTO de saída encapsula os resultados do fuzzy matcher (tipo e nome) e contém **sempre uma
      lista** de logradouros casados (0, 1 ou N) — cada item com **codlog**, **código** do tipo
      (`cd_tipo_logradouro`) e **nome** do logradouro. O consumer sempre lida com a possibilidade de
      mais de um codlog.
* [ ] O DTO expõe um **flag** `resultado_multiplo` (verdadeiro quando a lista tem mais de um item)
      para o front decidir se precisa desambiguar, além do **flag** `ignorou_filtro_tipo` (se houve
      rebusca ignorando o tipo digitado).
* [ ] O matching textual reaproveita `fuzzy_match` (`services.utils.fuzzy_matcher`) — nada de
      reimplementar similaridade nem normalização.
* [ ] O cache do catálogo (variações de tipo, tabela de logradouros e índice por tipo) tem
      **TTL de 24h**: passado o período, a próxima consulta recarrega os parquets de `data/`,
      pegando o que o cron de atualização gravou. Sem TTL/cron a 1ª consulta ainda carrega sob demanda.
* [ ] Tipagem integral; `mypy` limpo.

## Contexto e decisões de arquitetura

**Camada.** Mexe exclusivamente no **domínio** (`services/domain/`). Não toca views, models,
management commands nem integrações externas. Nenhum import de Django (§3.3, §7.3 do CLAUDE.md).

**Responsabilidade única (§10.1).** O módulo cuida **só** de logradouros — não cruza para lotes ou
endereços. Duas responsabilidades distintas, separadas por composição (§10.4):

1. **Acesso aos dados cacheados (catálogo).** Carrega, uma única vez e em memória, a tabela de
   variações de tipo (`tipos_logradouro_cache.parquet`: `nome_tipo` → `cd_tipo_logradouro`) e a
   tabela de logradouros (`nomes_logradouros.parquet`); expõe as estruturas de lookup que o matcher
   consome (variações como *choices* do tipo, nomes por código de tipo, todos os nomes, e a
   recuperação das linhas — codlog/código/nome — a partir do nome casado). É a
   "interface de lookup ... dict em memória" de §7.3; trocar por Redis no futuro fica isolado aqui.
   O carregamento é **preguiçoso** (na primeira utilização) para não fazer I/O pesado em tempo de
   import, e tem **TTL de 24h**: um cron externo reescreve os arquivos de `data/` a cada 24h, então
   o cache expira no mesmo período e a próxima consulta recarrega os dados atualizados. O TTL é
   provido por um descriptor utilitário reusável (`ttl_cached_property` em `services/utils/cache`),
   já pensando nos catálogos futuros de lote/endereço.
2. **Matcher (classe callable).** Orquestra o pipeline de matching compondo o catálogo + `fuzzy_match`.

**Pipeline do matcher (`__call__` → `_pipeline`, etapas em métodos dedicados, no estilo de
`FuzzyMatcher`/`TextNormalizer`):**

1. **Split** do texto no primeiro espaço → `(tipo_token, nome_token)`. Se **não houver espaço**,
   não há tipo: o token único é o **nome** (`tipo_token = None`) e o pipeline faz **fast-forward**
   para a etapa 5 (match de nome global), pulando o match de tipo.
2. **Match do tipo** (Levenshtein) do `tipo_token` contra as variações (`nome_tipo`) do parquet de
   tipos → resolve o código do tipo (`cd_tipo_logradouro`, ex.: `AV`).
3. **Match do nome** (Jaro-Winkler) do `nome_token` contra os nomes filtrados por aquele código.
4. **Threshold / rebusca:** se o melhor score < threshold (ou o subconjunto for vazio), refaz o
   match de nome sobre **todos** os nomes e marca `ignorou_filtro_tipo = True`.
5. **Match de nome global** (caminho fast-forward, quando não há tipo): match Jaro-Winkler do nome
   sobre **todos** os logradouros, sem filtro; `match_tipo = None` e `ignorou_filtro_tipo = False`.
6. **Recupera as linhas** (codlog, código real, nome) de **todos** os logradouros cujo nome bate
   com o melhor nome casado — no universo ativo (filtrado por tipo, ou todos) — e monta a **lista**
   do DTO de saída. Logradouros homônimos (mesmo nome, codlogs diferentes) produzem múltiplos itens.

**Resultado sempre lista.** Por consistência, o DTO carrega **sempre** uma lista de logradouros
casados, mesmo quando há um único resultado (lista de um item) ou nenhum (lista vazia). O consumer
trata sempre a possibilidade de N codlogs; o flag `resultado_multiplo` indica quando há mais de um,
para o front desambiguar.

**Sem tipo ≠ rebusca.** O flag `ignorou_filtro_tipo` sinaliza apenas a correção por confusão de
tipo (etapa 4). Quando o usuário não informa tipo (fast-forward), não havia filtro a ignorar — o
flag fica `False` e o "não houve tipo" é sinalizado por `match_tipo is None`.

**Tipo reportado vem da linha casada.** Como na rebusca o usuário pode ter errado o tipo, o
`tipo_codigo` **reportado** em cada item é o `cd_tipo_logradouro` real da linha encontrada no parquet
de nomes, não necessariamente o que foi digitado. No caminho sem rebusca os dois coincidem (o
subconjunto já foi filtrado por aquele código). O resultado do match de tipo (Levenshtein) é
preservado em `match_tipo` como metadado de rastreabilidade.

**Normalização (§7.1, §11).** Não há normalização nova: `fuzzy_match` já normaliza query e choices
internamente. As variações de `nome_tipo` e os nomes de logradouro nos parquets já estão
normalizados (maiúsculas, sem acento) e convergem com a entrada do usuário pela mesma
`normalize_text`. Ver skill `fuzzy-matcher`.

**Threshold como constante tunável.** Definido como constante `UPPER_CASE` do módulo e injetável no
construtor do matcher (default a partir da constante). Valor inicial empírico, a ser calibrado.

**Contratos (§3.3, §10.4).** Entrada e saída são DTOs Pydantic; o DTO de saída **encapsula** os
`FuzzyMatchResult` (tipo e nome) e oferece acessores de conveniência via `@property`.

## Peças de referência a compor

* `@services/utils/fuzzy_matcher` → `fuzzy_match`: match Levenshtein (tipo) e Jaro-Winkler (nome).
  Já normaliza internamente. Ver skill **fuzzy-matcher**. **Não** reimplementar similaridade.
* `@services/utils/fuzzy_matcher` → `FuzzyMatchResult` / `FuzzyMatchItem`: encapsulados no DTO de saída.
* `@services/utils/io` → `read_parquet_from_data`: carregar os caches parquet de `data/`.
* Dados versionados em `data/` (§11): `tipos_logradouro_cache.parquet` (`nome_tipo` → `cd_tipo_logradouro`,
  com variações de typo já normalizadas) e `nomes_logradouros.parquet` (`codlog`, `cd_tipo_logradouro`,
  `nm_logradouro`). Os dois se ligam pela coluna `cd_tipo_logradouro`.

## Snippets sugeridos

Organização interna em submódulos (direção sugerida, adaptável sem violar §3/§10):
`models.py` (DTOs), `catalog.py` (acesso aos dados/lookup), `matcher.py` (classe callable),
`__init__.py` (exposição).

Submódulo de modelos (`models.py`):

```python
from pydantic import BaseModel, computed_field
from services.utils.fuzzy_matcher import FuzzyMatchResult


class LogradouroMatchQuery(BaseModel):
    texto: str                      # entrada única, ex.: "avenida paulista"
    limite: int = 5                 # quantos matches manter no resultado de nome


class LogradouroRow(BaseModel):     # espelho da linha do parquet (uso interno do catálogo)
    codlog: str
    cd_tipo_logradouro: str
    nm_logradouro: str


class LogradouroMatch(BaseModel):   # um logradouro casado (item da lista de resultado)
    codlog: str                     # PRINCIPAL
    tipo_codigo: str                # código do tipo (cd_tipo_logradouro, ex.: "AV")
    nome_logradouro: str            # nome do logradouro casado


class LogradouroMatchResult(BaseModel):
    match_tipo: FuzzyMatchResult | None  # Levenshtein sobre as variações; None se sem tipo informado
    match_nome: FuzzyMatchResult         # Jaro-Winkler sobre os nomes (resultado final)
    logradouros: list[LogradouroMatch]   # SEMPRE lista (0, 1 ou N — homônimos viram N itens)
    ignorou_filtro_tipo: bool            # houve rebusca ignorando o tipo digitado?

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resultado_multiplo(self) -> bool:    # flag p/ o front desambiguar
        return len(self.logradouros) > 1

    @computed_field  # type: ignore[prop-decorator]
    @property
    def codlogs(self) -> list[str]:
        return [m.codlog for m in self.logradouros]

    @property
    def nome_logradouro(self) -> str | None:
        item = self.match_nome.best_match
        return item.original_string if item else None
```

Submódulo de catálogo (`catalog.py`) — carga preguiçosa e estruturas de lookup em memória:

```python
from services.utils.cache import ttl_cached_property
from services.utils.io import read_parquet_from_data
from .models import LogradouroRow

TIPOS_CACHE_FILE = "tipos_logradouro_cache.parquet"    # colunas: nome_tipo, cd_tipo_logradouro
NOMES_LOGRADOUROS_FILE = "nomes_logradouros.parquet"
DATA_TTL_SECONDS = 24 * 60 * 60                        # 24h — alinhado ao cron de atualização


class LogradouroCatalog:
    @ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
    def _variacoes(self) -> dict[str, str]:            # nome_tipo (variação) -> cd_tipo_logradouro
        cols = read_parquet_from_data(TIPOS_CACHE_FILE)
        return dict(zip(cols["nome_tipo"], cols["cd_tipo_logradouro"]))

    @ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
    def _rows(self) -> list[LogradouroRow]:
        cols = read_parquet_from_data(NOMES_LOGRADOUROS_FILE)
        return [
            LogradouroRow(codlog=c, cd_tipo_logradouro=t, nm_logradouro=n)
            for c, t, n in zip(cols["codlog"], cols["cd_tipo_logradouro"], cols["nm_logradouro"])
        ]

    @ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
    def _por_tipo(self) -> dict[str, list[LogradouroRow]]:
        indice: dict[str, list[LogradouroRow]] = {}
        for row in self._rows:
            indice.setdefault(row.cd_tipo_logradouro, []).append(row)
        return indice

    @property
    def variacoes_tipo(self) -> list[str]:             # choices p/ o match de tipo
        return list(self._variacoes.keys())

    def codigo_da_variacao(self, variacao: str) -> str | None:
        return self._variacoes.get(variacao)

    def linhas_do_tipo(self, codigo: str) -> list[LogradouroRow]:
        return self._por_tipo.get(codigo, [])

    def todas_as_linhas(self) -> list[LogradouroRow]:
        return self._rows

    def linhas_por_nome(self, nome: str, codigo: str | None) -> list[LogradouroRow]:
        universo = self.linhas_do_tipo(codigo) if codigo else self._rows
        return [row for row in universo if row.nm_logradouro == nome]  # homônimos -> N linhas
```

Submódulo do matcher (`matcher.py`) — callable com pipeline segmentado:

```python
from services.utils.fuzzy_matcher import FuzzyMatchResult, fuzzy_match
from .catalog import LogradouroCatalog
from .models import LogradouroMatch, LogradouroMatchQuery, LogradouroMatchResult

DEFAULT_NAME_SCORE_THRESHOLD = 80.0     # Jaro-Winkler (0..100); calibrar empiricamente


class LogradouroMatcher:
    def __init__(
        self,
        catalog: LogradouroCatalog | None = None,
        name_score_threshold: float = DEFAULT_NAME_SCORE_THRESHOLD,
    ) -> None:
        self._catalog = catalog or LogradouroCatalog()
        self._threshold = name_score_threshold

    def __call__(self, query: LogradouroMatchQuery) -> LogradouroMatchResult:
        return self._pipeline(query)

    def _pipeline(self, query: LogradouroMatchQuery) -> LogradouroMatchResult:
        tipo_token, nome_token = self._split(query.texto)
        if tipo_token is None:                          # fast-forward: sem tipo informado
            match_nome = self._match_nome_global(nome_token, query.limite)
            return self._build_result(None, match_nome, None, ignorou=False)
        match_tipo = self._match_tipo(tipo_token)
        codigo = self._resolve_codigo(match_tipo)
        match_nome, ignorou = self._match_nome(nome_token, codigo, query.limite)
        return self._build_result(match_tipo, match_nome, codigo, ignorou)

    def _split(self, texto: str) -> tuple[str | None, str]:
        partes = texto.strip().split(" ", 1)
        if len(partes) < 2:                             # sem espaço -> sem tipo, só nome
            return None, partes[0] if partes else ""
        return partes[0], partes[1]

    def _match_tipo(self, tipo_token: str) -> FuzzyMatchResult:
        return fuzzy_match(tipo_token, self._catalog.variacoes_tipo, algorithm="levenshtein")

    def _resolve_codigo(self, match_tipo: FuzzyMatchResult) -> str | None:
        melhor = match_tipo.best_match
        return self._catalog.codigo_da_variacao(melhor.original_string) if melhor else None

    def _match_nome(
        self, nome_token: str, codigo: str | None, limite: int
    ) -> tuple[FuzzyMatchResult, bool]:
        choices = [r.nm_logradouro for r in self._catalog.linhas_do_tipo(codigo)] if codigo else []
        resultado = fuzzy_match(nome_token, choices, limit=limite, algorithm="jaro_winkler") if choices else None
        precisa_rebusca = (
            resultado is None
            or resultado.best_match is None
            or resultado.best_match.similarity_score < self._threshold
        )
        if precisa_rebusca:
            return self._match_nome_global(nome_token, limite), codigo is not None
        return resultado, False

    def _match_nome_global(self, nome_token: str, limite: int) -> FuzzyMatchResult:
        todos = [r.nm_logradouro for r in self._catalog.todas_as_linhas()]
        return fuzzy_match(nome_token, todos, limit=limite, algorithm="jaro_winkler")

    def _build_result(self, match_tipo, match_nome, codigo, ignorou) -> LogradouroMatchResult:
        melhor = match_nome.best_match
        filtro = None if ignorou else codigo
        rows = self._catalog.linhas_por_nome(melhor.original_string, filtro) if melhor else []
        logradouros = [
            LogradouroMatch(
                codlog=row.codlog,
                tipo_codigo=row.cd_tipo_logradouro,
                nome_logradouro=row.nm_logradouro,
            )
            for row in rows
        ]
        return LogradouroMatchResult(
            match_tipo=match_tipo,
            match_nome=match_nome,
            logradouros=logradouros,
            ignorou_filtro_tipo=ignorou,
        )


match_logradouro = LogradouroMatcher()
```

Arquivo de inicialização (`__init__.py`):

```python
from .matcher import match_logradouro
from .models import LogradouroMatch, LogradouroMatchQuery, LogradouroMatchResult

__all__ = [
    "match_logradouro",
    "LogradouroMatch",
    "LogradouroMatchQuery",
    "LogradouroMatchResult",
]
```

Utilitário de TTL (`services/utils/cache`) — descriptor reusável, expõe só `ttl_cached_property`:

```python
import time
from collections.abc import Callable
from typing import Any, Generic, TypeVar, overload

T = TypeVar("T")


class TTLCachedProperty(Generic[T]):
    def __init__(self, func: Callable[[Any], T], ttl_seconds: float) -> None:
        self._func = func
        self._ttl = ttl_seconds
        self._attr = f"_ttlcache_{func.__name__}"     # (valor, expira_em) por instância
        self.__doc__ = func.__doc__

    def __set_name__(self, owner: type, name: str) -> None:
        self._attr = f"_ttlcache_{name}"

    @overload
    def __get__(self, instance: None, owner: type) -> "TTLCachedProperty[T]": ...
    @overload
    def __get__(self, instance: object, owner: type) -> T: ...
    def __get__(self, instance: object | None, owner: type) -> "TTLCachedProperty[T] | T":
        if instance is None:
            return self
        agora = time.monotonic()
        cache = instance.__dict__.get(self._attr)
        if cache is not None and cache[1] > agora:
            return cache[0]
        valor = self._func(instance)
        instance.__dict__[self._attr] = (valor, agora + self._ttl)
        return valor


def ttl_cached_property(
    ttl_seconds: float,
) -> Callable[[Callable[[Any], T]], TTLCachedProperty[T]]:
    def decorator(func: Callable[[Any], T]) -> TTLCachedProperty[T]:
        return TTLCachedProperty(func, ttl_seconds)
    return decorator
```

## Fora de escopo

* Roteamento por **regex** da busca simples (apps/search) e a busca detalhada de campos segmentados.
* Views, *management commands* e persistência Django.
* Resolver a **geometria/linha** a partir do codlog (entrega posterior do roadmap).
* **Sugestões assíncronas** durante a digitação (match exato/prefixo por keyup).
* Migração do cache de lookup para Redis.
* Testes unitários (ver Notas de teste).

## Notas de teste

* `"avenida paulista"` → `codlog == "156566"`, `tipo_codigo == "AV"`, `ignorou_filtro_tipo == False`.
* Tipo digitado errado: `"rua paulista"` (PAULISTA é AV) — espera-se que o score baixo no
  subconjunto `R` dispare a rebusca; resultado acha `AV PAULISTA`, `ignorou_filtro_tipo == True`,
  `tipo_codigo == "AV"`.
* Variação de tipo com typo: `"avnda paulista"` resolve o código `AV` via Levenshtein.
* Sem tipo (fast-forward): `"paulista"` (sem espaço) → `match_tipo is None`,
  `ignorou_filtro_tipo == False`, match de nome sobre todos os logradouros; acha `AV PAULISTA`,
  `codlog == "156566"`, `tipo_codigo == "AV"` (tipo vindo da linha casada).
* Homônimos (ex.: `"rua abaete"` — `ABAETE` aparece com dois codlogs no tipo `R`) — a lista
  `logradouros` tem **dois** itens (ambos os codlogs), `resultado_multiplo == True`.
* Resultado único (ex.: `"avenida paulista"`) — lista de **um** item, `resultado_multiplo == False`.
* Rastreabilidade: `match_tipo` e `match_nome` preservados no DTO; `nome_logradouro` (property) bate
  com `match_nome.best_match.original_string`.
* TTL do catálogo: com `ttl_seconds` curto, alterar o arquivo em `data/` e confirmar que, após
  expirar, uma nova consulta reflete o dado atualizado (antes de expirar, mantém o cache).

## Patches

* (nenhum até o momento)
