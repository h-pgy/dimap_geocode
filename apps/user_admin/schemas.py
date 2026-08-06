"""
DTOs das páginas administrativas (SPEC user_admin/012). A view constrói o DTO e deixa o
PydanticValidationMiddleware interceptar o ValidationError — nunca try/except na view (§7.2).
"""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator


def _vazio_para_nulo(valor: object) -> object:
    # O select da unidade superior manda "" na opção raiz; para o domínio, raiz é ausência de pai.
    return None if valor == "" else valor


PaiOpcional = Annotated[int | None, BeforeValidator(_vazio_para_nulo)]


class SelecaoUnidadePai(BaseModel):
    pai: PaiOpcional = None
