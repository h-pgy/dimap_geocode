from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Orientacao(StrEnum):
    RETRATO = "retrato"
    PAISAGEM = "paisagem"


class Posicao(StrEnum):
    """Onde a marca se pinta. FUNDO é a exceção: não reserva área e é pintada ANTES do corpo."""

    SUPERIOR = "superior"
    INFERIOR = "inferior"
    FUNDO = "fundo"


class TamanhoPagina(BaseModel):
    """A folha já orientada."""

    model_config = ConfigDict(frozen=True)

    largura_mm: float
    altura_mm: float


class FormatoPagina(BaseModel):
    """O papel antes de orientado: é `orientar()` que decide qual lado vira largura."""

    model_config = ConfigDict(frozen=True)

    menor_lado_mm: float
    maior_lado_mm: float

    def orientar(self, orientacao: Orientacao) -> TamanhoPagina:
        if orientacao is Orientacao.RETRATO:
            return TamanhoPagina(largura_mm=self.menor_lado_mm, altura_mm=self.maior_lado_mm)
        return TamanhoPagina(largura_mm=self.maior_lado_mm, altura_mm=self.menor_lado_mm)


A4 = FormatoPagina(menor_lado_mm=210.0, maior_lado_mm=297.0)
A3 = FormatoPagina(menor_lado_mm=297.0, maior_lado_mm=420.0)


class Margens(BaseModel):
    """A moldura que o corpo não invade."""

    model_config = ConfigDict(frozen=True)

    esquerda_mm: float
    direita_mm: float
    superior_mm: float
    inferior_mm: float


class Faixa(BaseModel):
    """O retângulo que pertence a UMA marca. Ela pinta aqui dentro e não conhece o resto da página."""

    model_config = ConfigDict(frozen=True)

    esquerda_mm: float
    topo_mm: float
    largura_mm: float
    altura_mm: float
