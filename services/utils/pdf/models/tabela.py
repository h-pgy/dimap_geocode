from pydantic import BaseModel, ConfigDict

from .texto import Alinhamento


class Coluna(BaseModel):
    """O que toda coluna tem é alinhamento; é a largura que separa os dois subtipos."""

    model_config = ConfigDict(frozen=True)

    alinhamento: Alinhamento = Alinhamento.ESQUERDA


class ColunaFixa(Coluna):
    """Largura que não depende da página: código, data, valor."""

    largura_mm: float


class ColunaFluida(Coluna):
    """Peso sobre o que sobra depois das fixas. Quanto é isso, só a página sabe."""

    peso: float = 1.0


class Grade(BaseModel):
    """A tabela em números — é tudo que uma regra precisa para mirar as células certas."""

    model_config = ConfigDict(frozen=True)

    colunas: int
    linhas_cabecalho: int
    linhas_corpo: int


# O comando de `TableStyle`: ("BACKGROUND", (coluna, linha), (coluna, linha), valor).
type ComandoTabela = tuple[object, ...]
