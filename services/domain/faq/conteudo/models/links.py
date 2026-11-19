from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl, UrlConstraints


class LinkDoSistema(BaseModel):
    """Endereço do próprio sistema citado na resposta. Guarda só o caminho, que sobrevive à troca de ambiente."""

    tipo: Literal["sistema"] = "sistema"
    # O regex do Pydantic não tem lookahead: "/x" ou "/", nunca "//x".
    caminho: str = Field(pattern=r"^/([^/]|$)", max_length=500)

    @property
    def href(self) -> str:
        return self.caminho


class LinkExterno(BaseModel):
    tipo: Literal["externo"] = "externo"
    url: Annotated[HttpUrl, UrlConstraints(max_length=500)]

    @property
    def href(self) -> str:
        return str(self.url)


class LinkReferencia(BaseModel):
    """Link citado pela resposta, para o leitor seguir. Do sistema ou externo é decidido pela resolução."""

    titulo: str = Field(min_length=2, max_length=120)
    destino: Annotated[LinkDoSistema | LinkExterno, Field(discriminator="tipo")]
