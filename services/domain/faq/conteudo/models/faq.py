from enum import StrEnum
from typing import Self

from pydantic import (
    BaseModel,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from services.domain.faq.taxonomia import PalavraChave, Tema
from services.utils.frases import FormatadorDeFrases
from services.utils.normalization import normalize_text

from .links import LinkReferencia

formatar_pergunta = FormatadorDeFrases(ultimo="?")


class Visibilidade(StrEnum):
    PUBLICA = "publica"
    INTERNA = "interna"


class Situacao(StrEnum):
    RASCUNHO = "rascunho"
    PUBLICADA = "publicada"
    EXCLUIDA = "excluida"


class Pergunta(BaseModel):
    """Uma forma de fazer a pergunta. A identidade é a `chave`, não o texto."""

    texto: str = Field(min_length=5, max_length=300)

    @field_validator("texto", mode="before")
    @classmethod
    def _formatar(cls, valor: object) -> object:
        return formatar_pergunta(valor) if isinstance(valor, str) else valor

    @computed_field  # type: ignore[prop-decorator]
    @property
    def chave(self) -> str:
        return normalize_text(self.texto)


class Resposta(BaseModel):
    """Conteúdo que responde às perguntas: texto markdown, links de referência e anexos."""

    markdown: str = Field(min_length=1)
    links: list[LinkReferencia] = []
    # Ids de Anexo; o vínculo não tem atributos.
    anexos: list[int] = []

    @field_validator("markdown", mode="before")
    @classmethod
    def _nao_vazia(cls, valor: str) -> str:
        if not valor or not valor.strip():
            raise ValueError("A resposta não pode ficar em branco.")
        return valor


class Faq(BaseModel):
    id: int | None = None
    pergunta: Pergunta
    variacoes: list[Pergunta] = []
    resposta: Resposta
    tema: Tema
    palavras_chave: list[PalavraChave] = []
    visibilidade: Visibilidade = Visibilidade.PUBLICA
    situacao: Situacao = Situacao.RASCUNHO
    autor_id: int | None = None
    relacionadas: list[int] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def eh_do_sistema(self) -> bool:
        return self.autor_id is None

    @model_validator(mode="after")
    def _perguntas_distintas(self) -> Self:
        chaves = [self.pergunta.chave, *(v.chave for v in self.variacoes)]
        if len(chaves) != len(set(chaves)):
            raise ValueError("A mesma pergunta aparece duas vezes nesta FAQ.")
        if self.id is not None and self.id in self.relacionadas:
            raise ValueError("Uma FAQ não se relaciona consigo mesma.")
        return self
