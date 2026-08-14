"""
DTOs da listagem de servidores (SPEC user_admin/013): a linha já materializada, os filtros por
coluna e a consulta que a interface manda ao domínio.
"""

from enum import StrEnum

from pydantic import BaseModel


class ColunaServidor(StrEnum):
    """As colunas que respondem — filtram e ordenam. Situação e ações não têm peça no cabeçalho."""

    NOME = "nome"
    RF = "rf"
    UNIDADE = "unidade"
    CARGO = "cargo"
    COMISSAO = "comissao"


class LinhaServidor(BaseModel):
    pk: int
    nome: str
    rf: str
    unidade: str
    # A página da unidade (SPEC user_admin/016) é alcançada por este pk; o filtro e a ordenação
    # seguem casando pelo texto da sigla.
    unidade_pk: int
    # Hex já resolvido na borda do app: o domínio não conhece o design system.
    cor_unidade: str
    cargo: str
    comissao: str
    impedido: bool


class FiltroColuna(BaseModel):
    coluna: ColunaServidor
    termo: str


class ConsultaServidores(BaseModel):
    filtros: list[FiltroColuna] = []
    ordenar_por: ColunaServidor | None = None
    descendente: bool = False
