from enum import StrEnum
from pydantic import BaseModel
from services.domain.listagem_gestao.models.consulta import ConsultaListagem


class ColunaCargo(StrEnum):
    NOME = "nome"
    PADRAO = "padrao"
    NATUREZA = "natureza"


class LinhaCargo(BaseModel):
    """Uma linha já materializada da tabela de cargos em comissão (SPEC user_admin/029)."""

    pk: int
    nome: str
    padrao: str
    natureza: str
    # Marca a linha quando o toggle "Mostrar cargos extintos" a revela.
    extinto: bool = False


ConsultaCargos = ConsultaListagem[ColunaCargo]
