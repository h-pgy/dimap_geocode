from enum import StrEnum
from pydantic import BaseModel
from services.domain.listagem_gestao.models.consulta import ConsultaListagem


class ColunaTipoUnidade(StrEnum):
    NOME = "nome"
    NIVEL = "nivel"
    RAIZ = "raiz"
    TITULAR = "titular"
    VEDADOS = "vedados"


class LinhaTipoUnidade(BaseModel):
    """Uma linha já materializada da tabela de tipos de unidade (SPEC user_admin/031)."""

    pk: int
    nome: str
    nivel: int
    pode_ser_raiz: bool
    exige_alta_administracao: bool
    # O requisito do titular já dito em padrão de cargo — é o texto que a coluna filtra e ordena.
    titular: str
    vedados: str
    unidades: int
    extinto: bool = False

    @property
    def raiz(self) -> str:
        return "Sim" if self.pode_ser_raiz else "Não"


ConsultaTiposUnidade = ConsultaListagem[ColunaTipoUnidade]
