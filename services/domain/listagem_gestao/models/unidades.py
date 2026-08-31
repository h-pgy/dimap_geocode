from enum import StrEnum
from pydantic import BaseModel
from services.domain.listagem_gestao.models.consulta import ConsultaListagem


class ColunaUnidade(StrEnum):
    SIGLA = "sigla"
    NOME = "nome"
    TIPO = "tipo"
    TITULAR = "titular"
    PAI = "pai"


class LinhaUnidade(BaseModel):
    """Uma linha já materializada da tabela de unidades."""

    pk: int
    sigla: str
    nome: str
    tipo: str
    exige_alta_administracao: bool
    cor_hex: str
    titular_pk: int | None = None
    titular_nome: str | None = None
    pai_pk: int | None = None
    pai_sigla: str | None = None
    # SPEC user_admin/025: marca a linha quando o toggle "Mostrar unidades extintas" a revela.
    extinta: bool = False

    @property
    def titular(self) -> str:
        return self.titular_nome or ""

    @property
    def pai(self) -> str:
        return self.pai_sigla or ""


ConsultaUnidades = ConsultaListagem[ColunaUnidade]
