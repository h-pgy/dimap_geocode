from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

LIMITE_HISTORICO = 5


class TipoGaveta(StrEnum):
    """Os tipos de gaveta lateral: é o tipo que escolhe o glifo."""

    LOTE = "lote"
    ENDERECO = "endereco"
    ENDERECO_EXTERNO = "endereco_externo"
    LOGRADOURO = "logradouro"
    DESENHOS = "desenhos"

    @property
    def rotulo(self) -> str:
        return ROTULO_POR_TIPO[self]


ROTULO_POR_TIPO = {
    TipoGaveta.LOTE: "Lote fiscal",
    TipoGaveta.ENDERECO: "Endereço",
    TipoGaveta.ENDERECO_EXTERNO: "Endereço externo",
    TipoGaveta.LOGRADOURO: "Logradouro",
    TipoGaveta.DESENHOS: "Desenhos no mapa",
}


class Etiqueta(BaseModel):
    """Como uma gaveta lateral se identifica e se resume numa linha."""

    model_config = ConfigDict(frozen=True)

    chave: str = Field(min_length=1)  # a mesma do `data-gaveta`: mesma chave, mesma gaveta
    tipo: TipoGaveta
    resumo: str = Field(min_length=1)


class Cena(BaseModel):
    """O que o voltar devolve como estava: a gaveta já renderizada e o desenho dela no mapa."""

    gaveta: str  # o HTML da gaveta; o domínio não o lê
    mapa: dict[str, Any]  # o payload do mapa: geometria, cor e enquadramento


class ItemHistorico(BaseModel):
    """Uma gaveta do histórico."""

    etiqueta: Etiqueta
    cena: Cena | None = None  # None: espelho do mapa, que não se guarda — pede-se de novo a ele


class HistoricoGaveta(BaseModel):
    """As últimas gavetas abertas, da mais recente à mais antiga, uma por chave."""

    itens: tuple[ItemHistorico, ...] = Field(default=(), max_length=LIMITE_HISTORICO)

    @model_validator(mode="after")
    def _uma_por_chave(self) -> Self:
        chaves = [item.etiqueta.chave for item in self.itens]
        if len(chaves) != len(set(chaves)):
            raise ValueError("O histórico repete uma gaveta.")
        return self

    def de_chave(self, chave: str) -> ItemHistorico | None:
        return next((item for item in self.itens if item.etiqueta.chave == chave), None)

    def fora(self, chave: str) -> tuple[ItemHistorico, ...]:
        """O histórico menos a gaveta que está na tela: o primeiro é o destino do voltar."""
        return tuple(item for item in self.itens if item.etiqueta.chave != chave)
