from pydantic import BaseModel, ConfigDict
from reportlab.lib.colors import Color


class EstiloTraco(BaseModel):
    """O que a `Folha` precisa para traçar uma linha fechada. Sem preenchimento: o selo cerca o que
    está dentro dele, não pinta por cima."""

    # `Color` é do reportlab e não tem schema Pydantic — ver Caveats da SPEC documentos_oficiais/001.
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    cor: Color
    espessura_mm: float
