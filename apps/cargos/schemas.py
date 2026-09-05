"""
DTOs das telas dos dois catálogos de cargo (SPECs user_admin/029 e 030). A view constrói o DTO e
deixa o `PydanticValidationMiddleware` interceptar o `ValidationError` — nunca `try/except` na view
(§7.2). Os atos que gravam (`NovaCargo`, `EdicaoCargo`, `NovaCargoBase`, `EdicaoCargoBase`) fogem
dessa regra de propósito: a recusa deles volta como o próprio formulário, e é por isso que passam
pelo `LeitorDeFormulario` em vez do middleware (SPEC formularios/001). Extinguir e reativar recebem
o cargo já resolvido pela rota — sem DTO próprio, porque não há campo algum a validar (§6).
"""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints


def _de_checkbox(valor: object) -> object:
    # Checkbox HTML manda "on" quando marcado e simplesmente não manda a chave quando não —
    # o default do campo (`False`) já resolve a ausência; isto só traduz a presença.
    return valor in ("on", True)


def _nivel_ou_nulo(valor: object) -> object:
    # O select some da tela quando a natureza é alta administração; o que chega então é "".
    return None if valor in (None, "") else valor


NomeDeCargo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
SiglaDeCargo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
NivelOpcional = Annotated[int | None, BeforeValidator(_nivel_ou_nulo)]
Checkbox = Annotated[bool, BeforeValidator(_de_checkbox)]


class NovaCargo(BaseModel):
    model_config = ConfigDict(frozen=True)

    nome: NomeDeCargo
    sigla: SiglaDeCargo
    nivel: NivelOpcional = None
    e_chefia: Checkbox = False
    alta_administracao: Checkbox = False


class EdicaoCargo(BaseModel):
    """Mesmos campos de `NovaCargo`, com o id do cargo editado."""

    model_config = ConfigDict(frozen=True)

    cargo_id: int
    nome: NomeDeCargo
    sigla: SiglaDeCargo
    nivel: NivelOpcional = None
    e_chefia: Checkbox = False
    alta_administracao: Checkbox = False


class NovaCargoBase(BaseModel):
    """Cargo base não tem natureza nem nível (SPEC user_admin/030): só identificação."""

    model_config = ConfigDict(frozen=True)

    nome: NomeDeCargo
    sigla: SiglaDeCargo


class EdicaoCargoBase(BaseModel):
    model_config = ConfigDict(frozen=True)

    cargo_id: int
    nome: NomeDeCargo
    sigla: SiglaDeCargo
