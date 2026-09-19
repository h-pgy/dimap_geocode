import json

from pydantic import BaseModel


class AvisoDeLimpeza(BaseModel):
    pergunta: str
    contagem: str  # o que vai sair, como se lê no badge: "12 lotes na tela"


class Limpeza(BaseModel):
    url: str  # rota já resolvida pela orquestração
    vals: dict[str, str] = {}  # o que a rota precisa para achar o estado (a chave do conjunto)
    aviso: AvisoDeLimpeza | None  # None: não há o que perder, e o ✕ fecha sem perguntar

    @property
    def hx_vals(self) -> str:
        # O template só interpola: o JSON do hx-vals sai daqui, escapado pelo autoescape do Django.
        return json.dumps(self.vals)
