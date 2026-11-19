from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from services.domain.listagem_gestao.models.consulta import ConsultaListagem


class ColunaFaq(StrEnum):
    PERGUNTA = "pergunta"
    TEMA = "tema"
    SITUACAO = "situacao"
    VISIBILIDADE = "visibilidade"
    AUTOR = "autor"
    EDITADO_POR = "editado_por"
    EDITADO_EM = "editado_em"


class LinhaFaq(BaseModel):
    """Uma linha já materializada da tabela de FAQs da área de edição."""

    pk: int
    pergunta: str
    tema: str
    situacao: str
    visibilidade: str
    autor: str
    editado_por: str
    editado_em: datetime | None
    eh_do_sistema: bool
    excluida: bool


ConsultaFaqs = ConsultaListagem[ColunaFaq]
