from pydantic import BaseModel, Field


class LogradouroSelection(BaseModel):
    codlog: str = Field(pattern=r"^\d{1,5}$")
    digito_verificador: str = Field(pattern=r"^\d$")
