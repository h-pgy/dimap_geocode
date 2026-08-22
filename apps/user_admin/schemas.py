"""
DTOs das páginas administrativas (SPEC user_admin/012 e 013), dos atos de exercício
(SPEC user_admin/015) e do cadastro de servidor (SPEC criacao_usuarios/004). A view constrói o DTO
e deixa o PydanticValidationMiddleware interceptar o ValidationError — nunca try/except na view
(§7.2).
"""

from collections.abc import Mapping
from datetime import date
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, HttpUrl

from services.domain.servidores_listagem import (
    ColunaServidor,
    ConsultaServidores,
    FiltroColuna,
)


def _vazio_para_nulo(valor: object) -> object:
    # O select da unidade superior manda "" na opção raiz; para o domínio, raiz é ausência de pai.
    return None if valor == "" else valor


PaiOpcional = Annotated[int | None, BeforeValidator(_vazio_para_nulo)]
# Campo de data em branco tem o mesmo significado dos models: prazo indeterminado.
DataOpcional = Annotated[date | None, BeforeValidator(_vazio_para_nulo)]
# O select do cargo em comissão manda "" na opção vazia; para o cadastro, isso é ausência de cargo.
CargoOpcional = Annotated[int | None, BeforeValidator(_vazio_para_nulo)]

PARAMETRO_ORDENAR_POR = "ordenar_por"
PARAMETRO_DESCENDENTE = "descendente"


class SelecaoUnidadePai(BaseModel):
    pai: PaiOpcional = None


class NovoImpedimento(BaseModel):
    tipo: int
    data_inicio: date
    data_fim: DataOpcional = None


class NovoServidor(BaseModel):
    """Quem o constrói é o `LeitorDeFormulario` de `apps/user_admin/formularios.py`, e não a view —
    e-mail torto e id não-numérico morrem aqui, antes de virar consulta, e a recusa volta como o
    próprio formulário (SPEC formularios/001)."""

    model_config = ConfigDict(frozen=True)

    rf: str = Field(min_length=1, max_length=20)
    nome: str = Field(min_length=1, max_length=100)
    sobrenome: str = Field(min_length=1, max_length=150)
    email: EmailStr
    unidade_id: int
    cargo_base_id: int
    cargo_comissao_id: CargoOpcional = None
    # Resolvida na orquestração a partir do request: nem o domínio nem o cadastro sabem em que host
    # o sistema roda.
    url_acesso: HttpUrl


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


def consulta_de_servidores(parametros: Mapping[str, str]) -> ConsultaServidores:
    """Traduz a query string da listagem no DTO do domínio: um filtro por coluna que respondeu."""
    filtros = [
        FiltroColuna(coluna=coluna, termo=parametros[coluna])
        for coluna in ColunaServidor
        if parametros.get(coluna, "").strip()
    ]
    # model_validate porque os valores chegam como texto: coluna inválida vira ValidationError e o
    # PydanticValidationMiddleware responde por ela.
    return ConsultaServidores.model_validate(
        {
            "filtros": filtros,
            # Cabeçalho em repouso manda campo vazio; para o domínio, é ausência de ordenação.
            "ordenar_por": parametros.get(PARAMETRO_ORDENAR_POR) or None,
            "descendente": parametros.get(PARAMETRO_DESCENDENTE) or False,
        }
    )
