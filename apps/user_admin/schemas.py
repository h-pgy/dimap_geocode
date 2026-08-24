"""
DTOs das páginas administrativas de servidor (SPEC user_admin/013), dos atos de exercício
(SPEC user_admin/015) e do cadastro de servidor (SPEC criacao_usuarios/004). A view constrói o DTO
e deixa o PydanticValidationMiddleware interceptar o ValidationError — nunca try/except na view
(§7.2).
"""

import re
from datetime import date
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, HttpUrl


def _vazio_para_nulo(valor: object) -> object:
    # Controle em branco é ausência, e não o texto vazio: é o que os campos opcionais abaixo leem.
    return None if valor == "" else valor


# Campo de data em branco tem o mesmo significado dos models: prazo indeterminado.
DataOpcional = Annotated[date | None, BeforeValidator(_vazio_para_nulo)]
# O select do cargo em comissão manda "" na opção vazia; para o cadastro, isso é ausência de cargo.
CargoOpcional = Annotated[int | None, BeforeValidator(_vazio_para_nulo)]

PADRAO_RF = r"^\d{7}$"
# Letra unicode dos dois lados de cada separador: sem isso "Ana " e "-Ana" passariam.
PADRAO_NOME = r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)*$"

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
    # SPEC user_admin/022. Default `False` porque o controle é um botão de dois estados: em
    # repouso ele não manda nada, e ausência é "não". Quem pode armá-lo é conferido no ato, não
    # aqui — o DTO não conhece quem assina.
    administrador: bool = False


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
    # SPEC user_admin/022 v3: a marca viaja com o formulário, como no cadastro — é o que amarra a
    # concessão à validação do resto. Default `False` pelo mesmo motivo de lá: o controle é um
    # botão de dois estados, e ausência é "não".
    administrador: bool = False


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


class MudancaDeAdministrador(BaseModel):
    """O ato sobre um servidor que JÁ existe (SPEC user_admin/022) — o das duas telas de servidor e
    o do modal direto."""

    model_config = ConfigDict(frozen=True)

    servidor_id: int
    # Explícito, e não alternância lida do estado atual: dois cliques concorrentes sobre o mesmo
    # servidor decidiriam coisas diferentes, e a operação registrada é o que se quer inequívoco.
    tornar: bool
    # O autor resolvido pela orquestração, nunca o `request`: é contra ele que a recusa de revogar
    # a si mesmo é escrita.
    autor_id: int
