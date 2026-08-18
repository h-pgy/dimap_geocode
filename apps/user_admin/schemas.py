"""
DTOs das páginas administrativas (SPEC user_admin/012 e 013) e dos atos de exercício
(SPEC user_admin/015). A view constrói o DTO e deixa o PydanticValidationMiddleware interceptar o
ValidationError — nunca try/except na view (§7.2).
"""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, BeforeValidator


def _vazio_para_nulo(valor: object) -> object:
    # O select da unidade superior manda "" na opção raiz; para o domínio, raiz é ausência de pai.
    return None if valor == "" else valor


PaiOpcional = Annotated[int | None, BeforeValidator(_vazio_para_nulo)]
# Campo de data em branco tem o mesmo significado dos models: prazo indeterminado.
DataOpcional = Annotated[date | None, BeforeValidator(_vazio_para_nulo)]

PARAMETRO_ORDENAR_POR = "ordenar_por"
PARAMETRO_DESCENDENTE = "descendente"


class SelecaoUnidadePai(BaseModel):
    pai: PaiOpcional = None


class NovoImpedimento(BaseModel):
    tipo: int
    data_inicio: date
    data_fim: DataOpcional = None


class NovaSubstituicao(BaseModel):
    substituto: int
    # A tela manda as datas já propostas; em branco continua valendo, porque é assim que o andaime
    # designa sem repetir o cálculo da lacuna.
    data_inicio: DataOpcional = None
    data_fim: DataOpcional = None


class TrocaDeSubstituto(BaseModel):
    substituto: int
    # "Assume em" — obrigatório, porque é a véspera dela que encerra a substituição que sai.
    data_inicio: date
    data_fim: DataOpcional = None
