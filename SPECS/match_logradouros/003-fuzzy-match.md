---

spec: match-logradouros/003
versao: v4
atualizado_em: 2026-06-22
changelog:

* v1: versão inicial
* v2: refatoração estrutural do método principal em métodos de pipeline
* v3: revisão textual para adequação ao formato objetivo e formal
* v4: divisão obrigatória dos snippets em submódulos de modelos e classe callable

---

# SPEC match-logradouros/003 — Módulo de Fuzzy Matching

## User story

Como desenvolvedor do domínio, quero um módulo de fuzzy matching segmentado em etapas de pipeline, para calcular a similaridade entre strings e manter a rastreabilidade dos dados antes e após a normalização.

## Critérios de aceite

* [ ] Código fonte implementado no diretório services/utils/fuzzy_matcher.
* [ ] Arquivo de inicialização do módulo exporta apenas a instância fuzzy_match.
* [ ] Estrutura do pacote dividida em submódulos independentes para modelos Pydantic e para a classe callable.
* [ ] Método especial de chamada atua como interface e delega o fluxo para um método de pipeline.
* [ ] Etapas de seleção de algoritmo, normalização de entrada, normalização de opções, execução matemática e formatação de saída possuem métodos dedicados.
* [ ] Função normalize_text processa a string de entrada e a lista de opções antes do cálculo.
* [ ] Algoritmos Levenshtein e Jaro-Winkler suportados via biblioteca RapidFuzz, com Levenshtein como padrão.
* [ ] Exceção NotImplementedError levantada para algoritmos previstos e não implementados.
* [ ] Exceção ValueError levantada para identificadores de algoritmos inválidos.
* [ ] DTO de saída consolida string de entrada original e string de entrada normalizada.
* [ ] DTO de item individual consolida string de referência original e string de referência normalizada.

## Contexto e decisões de arquitetura

O módulo atua na camada de utilitários e suporta as operações do domínio de geocodificação. O processamento independe de componentes do framework web. A delegação do fluxo para métodos internos isola a lógica de limpeza, o cálculo de similaridade e a construção das estruturas de dados de retorno. A persistência das versões brutas e tratadas das strings nos objetos Pydantic provê visibilidade sobre a operação da função de normalização. A biblioteca RapidFuzz executa o cálculo matemático. Para garantir a organização e a manutenibilidade do código, a implementação deve separar os componentes em submódulos específicos, isolando as definições dos modelos Pydantic em um arquivo e a classe callable do pipeline em outro.

## Peças de referência a compor

* `@services/utils/normalization` → `normalize_text`: aplicar na entrada de dados e na base de referência.

## Snippets sugeridos

A organização interna do pacote deve seguir a separação em arquivos distintos dentro do diretório services/utils/fuzzy_matcher.

Submódulo de modelos (ex: models.py):

```python
from pydantic import BaseModel, Field, field_validator, model_validator

class FuzzyMatchItem(BaseModel):
    original_string: str
    cleaned_string: str
    similarity_score: float
    rank_position: int = Field(ge=1)

class FuzzyMatchResult(BaseModel):
    original_query: str
    cleaned_query: str
    matches: list[FuzzyMatchItem]
    algorithm_used: str
    requested_limit: int

    @field_validator("matches")
    @classmethod
    def sort_and_validate_ranks(cls, v: list[FuzzyMatchItem]) -> list[FuzzyMatchItem]:
        if not v:
            return v
        
        v_sorted = sorted(v, key=lambda item: item.rank_position)
        
        for index, item in enumerate(v_sorted):
            expected_rank = index + 1
            if item.rank_position != expected_rank:
                raise ValueError(f"Sequencia de posicoes invalida. Esperado {expected_rank}, encontrado {item.rank_position}.")
                
        return v_sorted

    @model_validator(mode="after")
    def validate_best_match_score(self) -> "FuzzyMatchResult":
        if self.matches:
            highest_score = max(item.similarity_score for item in self.matches)
            if self.matches[0].similarity_score < highest_score:
                raise ValueError("O item na primeira posicao nao possui a maior pontuacao de similaridade.")
        return self

    @property
    def best_match(self) -> FuzzyMatchItem | None:
        if self.matches:
            return self.matches[0]
        return None

```

Submódulo da classe callable (ex: matcher.py):

```python
from typing import Literal
from rapidfuzz import fuzz, distance
from services.utils.normalization import normalize_text
from .models import FuzzyMatchItem, FuzzyMatchResult

class FuzzyMatcher:
    def __call__(
        self,
        query: str,
        choices: list[str],
        limit: int = 5,
        algorithm: Literal["levenshtein", "jaro_winkler"] = "levenshtein"
    ) -> FuzzyMatchResult:
        return self._pipeline(query, choices, limit, algorithm)

    def _pipeline(
        self,
        query: str,
        choices: list[str],
        limit: int,
        algorithm: str
    ) -> FuzzyMatchResult:
        cleaned_query = self._normalize_query(query)
        cleaned_choices = self._normalize_choices(choices)
        scorer = self._get_scorer(algorithm)
        raw_matches = self._execute_matching(
            cleaned_query,
            cleaned_choices,
            choices,
            scorer,
            algorithm
        )
        return self._build_result_dto(
            query,
            cleaned_query,
            limit,
            algorithm,
            raw_matches
        )

    def _normalize_query(self, query: str) -> str:
        return normalize_text(query)

    def _normalize_choices(self, choices: list[str]) -> list[str]:
        return [normalize_text(choice) for choice in choices]

    def _get_scorer(self, algorithm: str):
        if algorithm == "levenshtein":
            return fuzz.ratio
        elif algorithm == "jaro_winkler":
            return distance.JaroWinkler.normalized_similarity
        elif algorithm in ["hamming", "damerau_levenshtein"]:
            raise NotImplementedError("Algoritmo de distancia nao implementado.")
        else:
            raise ValueError("Algoritmo de distancia desconhecido ou invalido.")

    def _execute_matching(
        self,
        cleaned_query: str,
        cleaned_choices: list[str],
        choices: list[str],
        scorer,
        algorithm: str
    ) -> list[tuple[float, str, str]]:
        results = []
        for original, cleaned in zip(choices, cleaned_choices):
            score = scorer(cleaned_query, cleaned)
            if algorithm == "jaro_winkler":
                score = score * 100
            results.append((score, original, cleaned))
        results.sort(key=lambda x: x[0], reverse=True)
        return results

    def _build_result_dto(
        self,
        original_query: str,
        cleaned_query: str,
        limit: int,
        algorithm: str,
        raw_matches: list[tuple[float, str, str]]
    ) -> FuzzyMatchResult:
        top_results = raw_matches[:limit]
        match_items = [
            FuzzyMatchItem(
                original_string=original,
                cleaned_string=cleaned,
                similarity_score=score,
                rank_position=index + 1
            )
            for index, (score, original, cleaned) in enumerate(top_results)
        ]
        return FuzzyMatchResult(
            original_query=original_query,
            cleaned_query=cleaned_query,
            matches=match_items,
            algorithm_used=algorithm,
            requested_limit=limit
        )

fuzzy_match = FuzzyMatcher()

```

Arquivo de inicialização do pacote (**init**.py):

```python
from .matcher import fuzzy_match

__all__ = ["fuzzy_match"]

```

## Fora de escopo

Implementação de cache. Implementação de persistência em banco de dados. Implementação de algoritmos adicionais. Integração com views, models ou rotas da aplicação web.

## Notas de teste

Testar cálculo de Levenshtein com entrada Avenida Paulista e opções AV PAULISTA e RUA DIREITA, para validar o impacto da normalização no escore final. Testar cálculo de Jaro-Winkler com entrada Rua Direita e opções RUA DIREITA e RUA ESQUERDA, para checar a ordenação resultante. Verificar os campos de rastreabilidade de entrada e saída nos objetos de resultado de ambos os testes. Fornecer identificador inválido de algoritmo para validar o lançamento de ValueError. Fornecer identificador de algoritmo não implementado para validar o lançamento de NotImplementedError.

## Patches

* 2026-06-22 (v2): segrega o método principal em rotinas de pipeline e adiciona propriedades de rastreabilidade nas estruturas Pydantic.
* 2026-06-22 (v3): revisa a estrutura textual para aderência ao padrão objetivo e formal.
* 2026-06-22 (v4): divide a apresentação dos snippets sugeridos em submódulos de modelos e de lógica de matching.