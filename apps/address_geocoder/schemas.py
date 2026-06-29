from pydantic import BaseModel, Field


class EnderecoSelection(BaseModel):
    codlog: str = Field(pattern=r"^\d{1,5}$")
    numero: str
