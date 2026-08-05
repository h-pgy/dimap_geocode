from pydantic import BaseModel


class AvatarIniciaisInput(BaseModel):
    nome: str
    sobrenome: str
    cor_fundo: str
    cor_tinta: str


class AvatarIniciaisOutput(BaseModel):
    iniciais: str
    svg: str
