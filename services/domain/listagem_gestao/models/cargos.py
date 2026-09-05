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


class ColunaCargoBase(StrEnum):
    SIGLA = "sigla"
    NOME = "nome"


class LinhaCargoBase(BaseModel):
    """Uma linha já materializada da tabela de cargos base (SPEC user_admin/030): sem `padrao` nem
    `natureza`, que cargo base não tem."""

    pk: int
    sigla: str
    nome: str
    extinto: bool = False


ConsultaCargosBase = ConsultaListagem[ColunaCargoBase]
