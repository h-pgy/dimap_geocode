from typing import Self

from pydantic import BaseModel, Field, model_validator


class Tema(BaseModel):
    """Assunto que agrupa FAQs. Com `pai`, é subtema. São no máximo dois níveis."""

    nome: str = Field(min_length=2, max_length=80)
    pai: "Tema | None" = None
    ordem: int = 0

    @model_validator(mode="after")
    def _dois_niveis(self) -> Self:
        if self.pai is not None and self.pai.pai is not None:
            raise ValueError("Subtema não pode ter subtema.")
        return self
