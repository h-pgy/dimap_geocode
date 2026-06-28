from pydantic import BaseModel, Field, model_validator


class ContribuinteMatchInput(BaseModel):
    setor: str = Field(pattern=r"^\d{1,3}$")
    quadra: str | None = Field(default=None, pattern=r"^\d{1,3}$")
    lote: str | None = Field(default=None, pattern=r"^\d{1,4}$")
    dv: str | None = Field(default=None, pattern=r"^\d{1,2}$")
    limite: int = Field(default=5, gt=0)

    @model_validator(mode="after")
    def _validar_dependencia_quadra_lote(self) -> "ContribuinteMatchInput":
        if self.lote and not self.quadra:
            raise ValueError("A quadra deve ser informada quando o lote for preenchido.")
        return self


class ContribuinteMatchOutput(BaseModel):
    id_poligono: str
    setor: str
    quadra: str
    lote: str
    digito: str | None
    codlog: str
    logradouro: str
    numero: str
    complemento: str | None
    tipo_quadra: str
    tipo_lote: str
