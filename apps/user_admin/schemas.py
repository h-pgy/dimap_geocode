"""
DTOs das páginas administrativas (SPEC user_admin/012 e 013), dos atos de exercício
(SPEC user_admin/015) e do cadastro de servidor (SPEC criacao_usuarios/004). A view constrói o DTO
e deixa o PydanticValidationMiddleware interceptar o ValidationError — nunca try/except na view
(§7.2).
"""

import re
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

PADRAO_RF = r"^\d{7}$"
# Letra unicode dos dois lados de cada separador: sem isso "Ana " e "-Ana" passariam.
PADRAO_NOME = r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)*$"

PARAMETRO_ORDENAR_POR = "ordenar_por"
PARAMETRO_DESCENDENTE = "descendente"


def _so_digitos(valor: object) -> object:
    return re.sub(r"\D", "", valor) if isinstance(valor, str) else valor


def _espacos_colapsados(valor: object) -> object:
    return " ".join(valor.split()) if isinstance(valor, str) else valor


def _caixa_baixa(valor: object) -> object:
    return valor.strip().lower() if isinstance(valor, str) else valor


# O RF é o USERNAME_FIELD: a forma guardada é a única que o login vai poder pedir.
RegistroFuncional = Annotated[
    str,
    BeforeValidator(_so_digitos),
    Field(min_length=1, pattern=PADRAO_RF),
]
NomeDePessoa = Annotated[
    str,
    BeforeValidator(_espacos_colapsados),
    Field(min_length=1, max_length=100, pattern=PADRAO_NOME),
]
SobrenomeDePessoa = Annotated[
    str,
    BeforeValidator(_espacos_colapsados),
    Field(min_length=1, max_length=150, pattern=PADRAO_NOME),
]
# Duas grafias do mesmo endereço não podem conviver como dois cadastros: a unicidade é do banco, e
# ela compara texto.
EmailDeServidor = Annotated[EmailStr, BeforeValidator(_caixa_baixa)]


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

    rf: RegistroFuncional
    nome: NomeDePessoa
    sobrenome: SobrenomeDePessoa
    email: EmailDeServidor
    unidade_id: int
    cargo_base_id: int
    cargo_comissao_id: CargoOpcional = None
    # Resolvida na orquestração a partir do request: nem o domínio nem o cadastro sabem em que host
    # o sistema roda.
    url_acesso: HttpUrl


class EdicaoServidor(BaseModel):
    """Quem o constrói é o `LeitorDeFormulario`, e não a view — construí-lo aqui entregaria a
    recusa ao `PydanticValidationMiddleware`, cuja resposta o HTMX troca no alvo da requisição, que
    é o poço do modal (SPEC formularios/001, Caveats). Sem `url_acesso`: editar não manda e-mail
    nenhum (SPEC criacao_usuarios/005)."""

    model_config = ConfigDict(frozen=True)

    servidor_id: int
    rf: RegistroFuncional
    nome: NomeDePessoa
    sobrenome: SobrenomeDePessoa
    email: EmailDeServidor
    unidade_id: int
    cargo_base_id: int
    cargo_comissao_id: CargoOpcional = None


class NovoSuperusuario(BaseModel):
    """Nomeia unidade e cargos por sigla, e não por id: quem digita na linha de comando não tem id
    em mãos (SPEC criacao_usuarios/006)."""

    model_config = ConfigDict(frozen=True)

    rf: RegistroFuncional
    nome: NomeDePessoa
    sobrenome: SobrenomeDePessoa
    email: EmailDeServidor
    unidade_sigla: str
    cargo_base_sigla: str
    cargo_comissao_nome: str
    e_titular: bool = False


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
