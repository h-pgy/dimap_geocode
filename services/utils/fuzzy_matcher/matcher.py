from typing import Literal

from rapidfuzz import distance, fuzz

from services.utils.normalization import normalize_text

from .models import FuzzyMatchItem, FuzzyMatchResult


class FuzzyMatcher:
    def __call__(
        self,
        query: str,
        choices: list[str],
        limit: int = 5,
        algorithm: Literal["levenshtein", "jaro_winkler"] = "levenshtein",
    ) -> FuzzyMatchResult:
        return self._pipeline(query, choices, limit, algorithm)

    def _pipeline(
        self,
        query: str,
        choices: list[str],
        limit: int,
        algorithm: str,
    ) -> FuzzyMatchResult:
        cleaned_query = self._normalize_query(query)
        cleaned_choices = self._normalize_choices(choices)
        scorer = self._get_scorer(algorithm)
        raw_matches = self._execute_matching(cleaned_query, cleaned_choices, choices, scorer, algorithm)
        return self._build_result_dto(query, cleaned_query, limit, algorithm, raw_matches)

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
        algorithm: str,
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
        raw_matches: list[tuple[float, str, str]],
    ) -> FuzzyMatchResult:
        top_results = raw_matches[:limit]
        match_items = [
            FuzzyMatchItem(
                original_string=original,
                cleaned_string=cleaned,
                similarity_score=score,
                rank_position=index + 1,
            )
            for index, (score, original, cleaned) in enumerate(top_results)
        ]
        return FuzzyMatchResult(
            original_query=original_query,
            cleaned_query=cleaned_query,
            matches=match_items,
            algorithm_used=algorithm,
            requested_limit=limit,
        )


fuzzy_match = FuzzyMatcher()
