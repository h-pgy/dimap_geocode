from pydantic import BaseModel


class SecaoResultado(BaseModel):
    titulo: str
    html: str
