from enum import StrEnum
from pydantic import BaseModel
from services.domain.listagem_gestao.models.consulta import ConsultaListagem


class ColunaServidor(StrEnum):
    NOME = "nome"
    RF = "rf"
    UNIDADE = "unidade"
    CARGO = "cargo"
    COMISSAO = "comissao"


class LinhaServidor(BaseModel):
    """Uma linha já materializada da tabela de servidores."""

    pk: int
    nome: str
    rf: str
    unidade: str
    unidade_pk: int
    cor_unidade: str
    cargo: str
    comissao: str
    impedido: bool


ConsultaServidores = ConsultaListagem[ColunaServidor]
