from pydantic import BaseModel


class GavetaNaTela(BaseModel):
    chave: str


class PedidoDeCena(BaseModel):
    chave: str
