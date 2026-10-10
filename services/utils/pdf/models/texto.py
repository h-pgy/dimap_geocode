from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from reportlab.lib.colors import Color


class Alinhamento(StrEnum):
    ESQUERDA = "esquerda"
    CENTRO = "centro"
    DIREITA = "direita"


class EstiloTexto(BaseModel):
    """O que a `Folha` precisa para escrever uma linha. Os valores vêm de quem chama, nunca daqui."""

    # `Color` é do reportlab e não tem schema Pydantic — ver Caveats da SPEC documentos_oficiais/001.
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    fonte: str
    corpo_pt: float
    cor: Color
