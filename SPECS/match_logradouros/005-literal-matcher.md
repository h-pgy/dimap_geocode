---
spec: match-logradouros/005
versao: v2
atualizado_em: 2026-06-28
implementado: true
changelog:
  - v1: versão inicial
  - v2: remove sugestão opcional de linhas_contendo_nome no catálogo — contains é responsabilidade do matcher
---

# SPEC match-logradouros/005 — Matcher literal de logradouros (contains, para sugestões)

- [x] **Implementada** <!-- marque [x] e ponha implementado: true quando o código for entregue -->

## User story

Como usuário digitando o nome de uma rua na barra de pesquisa, quero ver sugestões de logradouros
cujo nome **contém** o que já digitei — opcionalmente restritas a um **tipo de logradouro** que eu
tenha informado — para escolher rapidamente o logradouro certo a cada tecla, sem depender de fuzzy
matching nem de digitar o nome inteiro.

Esta iteração adiciona o **matcher mais simples** do domínio de logradouros: um match **literal**
por substring (`contains` / `in`), pensado para **sugestões durante a digitação**. Diferente do
matcher fuzzy da match-logradouros/004 (Levenshtein + Jaro-Winkler), aqui não há similaridade nem
threshold — só verificação de "o texto digitado está contido no nome do logradouro". Também
**refatora a inicialização do pacote** para que o catálogo seja instanciado **uma única vez** e
**compartilhado** entre os dois matchers (fuzzy e literal), evitando duplicar dados em memória.

## Critérios de aceite

- [ ] Existe um novo módulo `literal_matcher.py` em `services/domain/logradouros_match/` com a classe
      **callable** `LiteralLogradouroMatcher`, no mesmo estilo segmentado de `LogradouroMatcher`.
- [ ] A classe **recebe o `LogradouroCatalog` no `__init__`** (injeção por composição) e o utiliza
      como única fonte de dados — **não** instancia catálogo próprio.
- [ ] O DTO de **input** tem um atributo **`nome`** (str, **obrigatório**) e um atributo
      **`tipo`** (str, **opcional**, default `None`), além de um `limite` de sugestões.
- [ ] O match de nome é **literal por substring**: uma linha do catálogo é sugerida quando o **nome
      digitado (normalizado) está contido** no `nm_logradouro` da linha (`normalize(query.nome) in
      row.nm_logradouro`). Sem fuzzy, sem threshold.
- [ ] Quando o **`tipo` é informado**, ele é resolvido a um **código** (`cd_tipo_logradouro`) via o
      catálogo, e o universo de busca fica **restrito a esse tipo** antes do filtro por substring.
- [ ] Quando o **`tipo` não é informado**, **não resolve a um código** (variação desconhecida), **ou**
      o filtro por tipo + substring **dá vazio**, o tipo é **ignorado** e a busca por substring é
      refeita sobre **todos** os logradouros.
- [ ] O DTO de **output** carrega **sempre uma lista** de logradouros casados (0, 1 ou N), cada item
      com **codlog**, **código do tipo** e **nome** — reutilizando o `LogradouroMatch` já existente —
      e um **flag** `ignorou_filtro_tipo` (verdadeiro quando um tipo foi informado mas a busca acabou
      ignorando-o).
- [ ] A lista de sugestões respeita o **`limite`** do DTO de input.
- [ ] A normalização do texto digitado (nome e tipo) usa **exclusivamente** `normalize_text`
      (`services.utils.normalization`) — nenhuma limpeza nova; os nomes/variações do catálogo já estão
      normalizados na ingestão pela mesma função, então a comparação converge.
- [ ] O `__init__.py` do pacote instancia o **catálogo uma única vez** e instancia **ambos** os
      matchers (fuzzy e literal) **compartilhando** essa instância; expõe as instâncias callable
      (`match_logradouro` e o novo `match_logradouro_literal`) e os DTOs. A instanciação a nível de
      módulo sai de `matcher.py`.
- [ ] Submódulos internos não são alcançados de fora (import pelo nível superior do pacote).
- [ ] Tipagem integral; `mypy` limpo.

## Contexto e decisões de arquitetura

**Camada.** Mexe exclusivamente no **domínio** (`services/domain/logradouros_match/`). Não toca
views, models, management commands nem integrações. Nenhum import de Django (§3.3, §7.3).

**Responsabilidade única (§10.1).** O módulo continua cuidando **só** de logradouros. O novo matcher
é uma responsabilidade distinta do fuzzy (estratégia de match diferente: literal vs. similaridade),
mas **compartilha** a mesma camada de acesso a dados (catálogo) por **composição** (§10.4) — sem
herança. O literal é deliberadamente o mais simples: `contains`, sem score nem threshold.

**Catálogo compartilhado (motivação central da refatoração).** Hoje `matcher.py` instancia
`match_logradouro = LogradouroMatcher()` no nível de módulo, criando seu **próprio** catálogo. Com
dois matchers, manter cada um com seu catálogo **duplicaria** em memória as tabelas de logradouros e
o índice por tipo. A decisão é mover a instanciação para o **`__init__.py` do pacote**: cria-se **um**
`LogradouroCatalog` e ele é injetado nos dois matchers. Assim os dois compartilham o mesmo cache em
memória (com o mesmo TTL de 24h da match-logradouros/004) — alinhado à §7.3 ("interface de lookup …
dict em memória"). Para isso, `LiteralLogradouroMatcher.__init__` recebe o catálogo como parâmetro
(injeção obrigatória); o `LogradouroMatcher` já aceita o catálogo por parâmetro, então passa a recebê-lo
do `__init__.py` em vez de criar o seu.

**Pipeline do matcher literal (`__call__` → `_pipeline`, etapas em métodos dedicados):**

1. **Normaliza** o nome digitado com `normalize_text`. Se o nome normalizado for **vazio**, devolve
   resultado vazio (não faz sentido sugerir tudo a cada keyup sem texto).
2. **Resolve o tipo** (se informado): normaliza o `tipo` e busca o **código** correspondente no
   catálogo (`codigo_da_variacao`). Tipo ausente/em branco ou variação desconhecida → sem código.
3. **Busca com tipo** (se houver código): filtra as linhas **daquele tipo** mantendo as cujo
   `nm_logradouro` **contém** o nome digitado. Se houver resultado, é o desfecho
   (`ignorou_filtro_tipo = False`).
4. **Fallback sem tipo:** se não havia código, ou a busca com tipo deu **vazia**, refaz o filtro por
   substring sobre **todas** as linhas. `ignorou_filtro_tipo` é **True** apenas quando um tipo havia
   sido informado mas a busca final o ignorou; quando nenhum tipo foi informado, é **False** (não
   havia filtro a ignorar — análogo ao fast-forward da match-logradouros/004).
5. **Monta o resultado:** aplica o `limite`, converte as linhas em `LogradouroMatch` e devolve o DTO.

**`contains` é lógica de domínio.** A verificação `nome in row.nm_logradouro` fica no **matcher**
(domínio), compondo os acessores brutos do catálogo (`linhas_do_tipo`, `todas_as_linhas`).

**Normalização (§7.1, §11).** Os `nm_logradouro` e as variações de tipo nos parquets **já estão
normalizados** (maiúsculas, sem acento) pela `normalize_text` na ingestão. Logo, normaliza-se apenas
a **entrada** (nome e tipo) com a **mesma** `normalize_text` e compara-se contra os valores já
normalizados do catálogo — sem renormalizar candidatos a cada consulta. Reaproveitar a função é
inegociável (skill `normalize-text`).

**Contratos (§3.3, §10.4).** Entrada e saída são DTOs Pydantic; o item da lista reutiliza
`LogradouroMatch` (mesmo contrato do matcher fuzzy), de modo que o consumer trate sugestões de ambos
os matchers de forma uniforme.

## Peças de referência a compor

- `@services/domain/logradouros_match` → `LogradouroCatalog` (`catalog.py`): **mesma** instância
  injetada nos dois matchers; usar `codigo_da_variacao`, `linhas_do_tipo` e `todas_as_linhas`.
- `@services/domain/logradouros_match` → `LogradouroMatch` (`models.py`): reutilizar como item da
  lista de saída (codlog / tipo_codigo / nome_logradouro).
- `@services/domain/logradouros_match` → `LogradouroMatcher` (`matcher.py`): já aceita catálogo por
  parâmetro; passa a recebê-lo do `__init__.py` (remoção da instanciação a nível de módulo).
- `@services/utils/normalization` → `normalize_text`: normalizar nome e tipo digitados (skill
  `normalize-text`). **Não** criar função de limpeza nova.

## Snippets sugeridos

DTOs adicionais (`models.py`) — input e output do matcher literal:

```python
class LiteralLogradouroQuery(BaseModel):
    nome: str                       # texto digitado (substring do nome do logradouro)
    tipo: str | None = None         # tipo opcional (ex.: "rua", "av"); restringe o universo
    limite: int = 5                 # nº máximo de sugestões


class LiteralLogradouroResult(BaseModel):
    logradouros: list[LogradouroMatch]   # SEMPRE lista (0, 1 ou N)
    ignorou_filtro_tipo: bool            # tipo informado, mas a busca o ignorou?
```

Matcher literal (`literal_matcher.py`) — callable, catálogo injetado, pipeline segmentado:

```python
from services.utils.normalization import normalize_text

from .catalog import LogradouroCatalog
from .models import (
    LiteralLogradouroQuery,
    LiteralLogradouroResult,
    LogradouroMatch,
    LogradouroRow,
)


class LiteralLogradouroMatcher:
    def __init__(self, catalog: LogradouroCatalog) -> None:
        self._catalog = catalog

    def __call__(self, query: LiteralLogradouroQuery) -> LiteralLogradouroResult:
        return self._pipeline(query)

    def _pipeline(self, query: LiteralLogradouroQuery) -> LiteralLogradouroResult:
        nome = normalize_text(query.nome)
        if not nome:
            return self._build([], query.limite, ignorou=False)
        tipo_informado = bool(query.tipo and query.tipo.strip())
        codigo = self._resolve_tipo(query.tipo)
        if codigo is not None:
            rows = self._contendo(nome, codigo)
            if rows:
                return self._build(rows, query.limite, ignorou=False)
        rows = self._contendo(nome, None)               # fallback: ignora o tipo
        return self._build(rows, query.limite, ignorou=tipo_informado)

    def _resolve_tipo(self, tipo: str | None) -> str | None:
        if not tipo or not tipo.strip():
            return None
        return self._catalog.codigo_da_variacao(normalize_text(tipo))

    def _contendo(self, nome: str, codigo: str | None) -> list[LogradouroRow]:
        universo = (
            self._catalog.linhas_do_tipo(codigo) if codigo else self._catalog.todas_as_linhas()
        )
        return [row for row in universo if nome in row.nm_logradouro]

    def _build(
        self, rows: list[LogradouroRow], limite: int, ignorou: bool
    ) -> LiteralLogradouroResult:
        logradouros = [
            LogradouroMatch(
                codlog=row.codlog,
                tipo_codigo=row.cd_tipo_logradouro,
                nome_logradouro=row.nm_logradouro,
            )
            for row in rows[:limite]
        ]
        return LiteralLogradouroResult(
            logradouros=logradouros,
            ignorou_filtro_tipo=ignorou,
        )
```

Inicialização do pacote (`__init__.py`) — catálogo único compartilhado pelos dois matchers:

```python
from .catalog import LogradouroCatalog
from .literal_matcher import LiteralLogradouroMatcher
from .matcher import LogradouroMatcher
from .models import (
    LiteralLogradouroQuery,
    LiteralLogradouroResult,
    LogradouroMatch,
    LogradouroMatchQuery,
    LogradouroMatchResult,
)

_catalog = LogradouroCatalog()                       # instância única, compartilhada em memória
match_logradouro = LogradouroMatcher(catalog=_catalog)
match_logradouro_literal = LiteralLogradouroMatcher(catalog=_catalog)

__all__ = [
    "match_logradouro",
    "match_logradouro_literal",
    "LogradouroMatch",
    "LogradouroMatchQuery",
    "LogradouroMatchResult",
    "LiteralLogradouroQuery",
    "LiteralLogradouroResult",
]
```

Em `matcher.py`, remover a linha `match_logradouro = LogradouroMatcher()` (a instância passa a nascer
no `__init__.py`).

## Fora de escopo

- Roteamento por **regex** da busca simples (apps/search) e a view que aciona as sugestões via HTMX.
- Decidir **qual** matcher (literal vs. fuzzy) cada caminho da UX usa — esta SPEC só entrega o matcher
  literal e o catálogo compartilhado.
- Views, *management commands*, persistência Django e renderização de partials.
- Resolver a **geometria/linha** a partir do codlog.
- Ranqueamento/ordenação das sugestões por relevância (prefixo antes de meio, etc.) — aqui a ordem é
  a do catálogo, apenas truncada pelo `limite`.
- Migração do cache de lookup para Redis.
- Testes unitários (ver Notas de teste).

## Notas de teste

- `nome="paul"`, `tipo=None` → sugere logradouros cujo nome contém `PAUL` (ex.: `PAULISTA`),
  `ignorou_filtro_tipo == False`.
- `nome="paul"`, `tipo="av"` → restringe ao tipo `AV` e filtra por substring; resultado não vazio →
  `ignorou_filtro_tipo == False`.
- `nome="paul"`, `tipo="rua"` (PAULISTA é AV) → filtro com tipo dá vazio → refaz sem tipo, acha
  `AV PAULISTA`, `ignorou_filtro_tipo == True`.
- `tipo` desconhecido/inválido (não resolve a código) com nome que casa → busca sem tipo,
  `ignorou_filtro_tipo == True`.
- `nome=""` (ou só espaços) → lista vazia, sem varrer o catálogo inteiro.
- `limite=3` com muitos candidatos → no máximo 3 itens na lista.
- Normalização: `nome="paulísta"` casa `PAULISTA` (acento/maiúscula resolvidos por `normalize_text`).
- Homônimos: nome que casa com múltiplos codlogs → vários itens na lista (respeitado o `limite`).
- Catálogo compartilhado: `match_logradouro` e `match_logradouro_literal` referenciam a **mesma**
  instância de `LogradouroCatalog` (sem duplicar os dados em memória).

## Patches

_Nenhum patch registrado até o momento._
