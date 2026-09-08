from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, SecretStr, field_validator

from .constants import CHAVE_TAG


class EstadoSelo(StrEnum):
    """Os três estados que o ARQUIVO sozinho consegue distinguir. Saber se o documento existe, ou se
    ainda vale, exige o acervo."""

    INTEGRO = "integro"
    VIOLADO = "violado"
    SEM_SELO = "sem_selo"


class SelarInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    pdf: bytes
    # Opaco de propósito: o utilitário sela o que lhe derem, e não conhece a forma do que sela.
    dados: dict[str, Any]
    campos_publicos: tuple[str, ...] = ()
    # `SecretStr` para o segredo não vazar em repr, log de exceção nem traceback.
    segredo: SecretStr
    id_chave: str

    @field_validator("dados")
    @classmethod
    def _sem_chave_reservada(cls, valor: dict[str, Any]) -> dict[str, Any]:
        if CHAVE_TAG in valor:
            raise ValueError(f"`{CHAVE_TAG}` é do mecanismo do selo e não pode vir nos dados.")
        return valor


class DocumentoSelado(BaseModel):
    """O arquivo pronto e o que ficou escrito dentro dele. `tag` sai junto para quem quiser
    guardá-la ao lado do arquivo — o selo, porém, se confere pelo arquivo, nunca pela cópia."""

    model_config = ConfigDict(frozen=True)

    pdf: bytes
    envelope: dict[str, Any]
    tag: str


class ConferirInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    pdf: bytes
    segredo: SecretStr


class ResultadoConferencia(BaseModel):
    """`envelope` e `publicos` vêm nulos quando não há selo. Quando o selo está VIOLADO os dois vêm
    preenchidos — o que está escrito ali é o que permite localizar o original."""

    model_config = ConfigDict(frozen=True)

    estado: EstadoSelo
    envelope: dict[str, Any] | None = None
    publicos: dict[str, Any] | None = None
