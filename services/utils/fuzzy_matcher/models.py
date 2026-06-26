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
                raise ValueError(
                    f"Sequencia de posicoes invalida. Esperado {expected_rank}, encontrado {item.rank_position}."
                )

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
