from typing import Literal

from pydantic import BaseModel


class AvatarIniciaisInput(BaseModel):
    nome: str
    sobrenome: str
    cor_fundo: str
    cor_tinta: str


class AvatarIniciaisOutput(BaseModel):
    iniciais: str
    svg: str


class ImagemPerfilOutput(BaseModel):
    tipo: Literal["foto", "avatar"]
    valor: str  # URL da foto, ou markup do SVG do avatar
