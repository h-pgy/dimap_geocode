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
    # SPEC user_admin/027: marca a linha quando o toggle "Mostrar servidores exonerados" a revela —
    # mesmo padrão de LinhaUnidade.extinta (SPEC 025).
    exonerado: bool = False


ConsultaServidores = ConsultaListagem[ColunaServidor]
