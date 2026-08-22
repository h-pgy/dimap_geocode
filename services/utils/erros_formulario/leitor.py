from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ValidationError
from pydantic_core import ErrorDetails

from .models import ErroBruto, Formulario, LeituraDeFormulario
from .tradutor import TradutorDeRecusa


class LeitorDeFormulario[T: BaseModel]:
    """Callable: o POST cru vira o DTO do formulário, ou a recusa traduzida. É esta peça que tira o
    `ValidationError` do caminho do `PydanticValidationMiddleware` — ver Caveats."""

    def __init__(self, dto: type[T], formulario: Formulario) -> None:
        self.dto = dto
        self.tradutor = TradutorDeRecusa(formulario)

    def __call__(self, valores: Mapping[str, Any]) -> LeituraDeFormulario[T]:
        try:
            return LeituraDeFormulario(dto=self.dto.model_validate(valores))
        except ValidationError as recusa:
            return LeituraDeFormulario(
                recusa=self.tradutor(de_pydantic(recusa.errors()))
            )


def de_pydantic(erros: Sequence[ErrorDetails]) -> tuple[ErroBruto, ...]:
    # `mensagem` fica vazia de propósito: o Pydantic escreve em inglês e por tipo, e quem traduz é
    # o catálogo.
    return tuple(
        ErroBruto(controle=controle_do_campo(str(erro["loc"][0])), tipo=erro["type"])
        for erro in erros
    )


def controle_do_campo(campo: str) -> str:
    """O model diz `unidade`, o DTO diz `unidade_id`, o `<select>` se chama `unidade`: o sufixo cai
    para os três virarem um nome só."""
    return campo.removesuffix("_id")
