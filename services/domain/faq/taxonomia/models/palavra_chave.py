from typing import Self

from pydantic import BaseModel, Field, computed_field, model_validator

PROFUNDIDADE_PALAVRA_CHAVE = 3


class PalavraChave(BaseModel):
    """Termo de busca ausente do texto da FAQ (sigla, jargão). Com `pai`, especializa o termo acima."""

    id: int | None = None
    nome: str = Field(min_length=2, max_length=60)
    pai: "PalavraChave | None" = None
    relacionadas: list[int] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def caminho(self) -> list[str]:
        return [*(self.pai.caminho if self.pai is not None else []), self.nome]

    @model_validator(mode="after")
    def _tres_niveis(self) -> Self:
        if len(self.caminho) > PROFUNDIDADE_PALAVRA_CHAVE:
            raise ValueError("Palavra-chave tem no máximo três níveis.")
        if self.id is not None and self.id in self.relacionadas:
            raise ValueError("Uma palavra-chave não se relaciona consigo mesma.")
        return self
