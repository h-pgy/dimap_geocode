from pydantic import BaseModel


class FalhaBaseOficial(BaseModel):
    motivo: str  # o que a base oficial não encontrou, pronto para o aviso
