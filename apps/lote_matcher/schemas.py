from pydantic import BaseModel, Field


class LoteSelection(BaseModel):
    setor: str = Field(pattern=r"^\d{1,3}$")
    quadra: str = Field(pattern=r"^\d{1,3}$")
    lote: str = Field(pattern=r"^\d{1,4}$")
    dv: str | None = Field(default=None, pattern=r"^\d{1,2}$")
    tipo_lote: str
