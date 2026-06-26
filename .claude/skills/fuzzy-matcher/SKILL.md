---
name: fuzzy-matcher
description: Como usar o módulo de fuzzy matching do DIMAP GeoCoder (services.utils.fuzzy_matcher). Use esta skill SEMPRE que o código precisar calcular similaridade entre strings ou ranquear opções por proximidade textual — nunca use rapidfuzz diretamente nem reimplemente o matching.
---

# Fuzzy Matcher — `services.utils.fuzzy_matcher`

## Regra inegociável

**Nunca chame `rapidfuzz` diretamente nem escreva lógica de matching.** O módulo já encapsula o
algoritmo, a normalização e a estrutura de retorno. Qualquer comparação fuzzy passa por aqui.

Importe **sempre pelo nível superior** `services.utils.fuzzy_matcher` — não alcance submódulos
internos (`.matcher`, `.models`).

## O que é exportado

```python
from services.utils.fuzzy_matcher import fuzzy_match
```

`fuzzy_match` é uma instância callable de `FuzzyMatcher`. Recebe a query e a lista de opções,
devolve um `FuzzyMatchResult` Pydantic com os resultados ranqueados.

## Assinatura

```python
fuzzy_match(
    query: str,
    choices: list[str],
    limit: int = 5,
    algorithm: Literal["levenshtein", "jaro_winkler"] = "levenshtein",
) -> FuzzyMatchResult
```

| Parâmetro   | Descrição                                                                 |
|-------------|---------------------------------------------------------------------------|
| `query`     | String de entrada do usuário (será normalizada internamente)              |
| `choices`   | Lista de candidatos a comparar (cada um será normalizado internamente)    |
| `limit`     | Quantos resultados retornar (padrão: 5)                                   |
| `algorithm` | `"levenshtein"` (padrão) ou `"jaro_winkler"`                             |

A normalização (`normalize_text`) é aplicada internamente à query e a cada choice. Não
pré-normalize os valores antes de passar — o módulo faz isso.

## Estrutura de retorno

```
FuzzyMatchResult
├─ original_query: str        — query como foi recebida
├─ cleaned_query: str         — query após normalização
├─ matches: list[FuzzyMatchItem]  — ranqueados por score (desc), até `limit`
│    ├─ original_string: str  — choice como foi recebida
│    ├─ cleaned_string: str   — choice após normalização
│    ├─ similarity_score: float  — 0..100
│    └─ rank_position: int    — começa em 1
├─ algorithm_used: str
├─ requested_limit: int
└─ best_match: FuzzyMatchItem | None  — atalho para matches[0]
```

## Uso

```python
from services.utils.fuzzy_matcher import fuzzy_match

# uso básico — Levenshtein, top-5
result = fuzzy_match("Avenida Paulista", ["AV PAULISTA", "RUA DIREITA", "AV IPIRANGA"])

# acessar o melhor resultado
if result.best_match:
    print(result.best_match.original_string)   # "AV PAULISTA"
    print(result.best_match.similarity_score)  # ex.: 81.48

# iterar todos os resultados ranqueados
for item in result.matches:
    print(item.rank_position, item.original_string, item.similarity_score)

# rastreabilidade: ver o que foi normalizado
print(result.original_query)   # "Avenida Paulista"
print(result.cleaned_query)    # "AVENIDA PAULISTA"

# Jaro-Winkler com limite customizado
result = fuzzy_match("Rua Direita", choices, limit=3, algorithm="jaro_winkler")
```

## Algoritmos disponíveis

| Identificador   | Implementado | Quando usar                                              |
|-----------------|:------------:|----------------------------------------------------------|
| `levenshtein`   | sim (padrão) | Erros de digitação, abreviações, variações de escrita    |
| `jaro_winkler`  | sim          | Prefixos em comum têm peso maior; bom para nomes de rua  |
| `hamming`       | não          | Levanta `NotImplementedError`                            |
| `damerau_levenshtein` | não  | Levanta `NotImplementedError`                            |
| qualquer outro  | —            | Levanta `ValueError`                                     |

## Rastreabilidade

Os campos `original_*` e `cleaned_*` preservam as versões antes e depois da normalização, tanto
na query quanto em cada item. Use-os para exibir o valor original ao usuário e para depurar o
impacto da normalização no score.
