from collections.abc import Mapping
from enum import StrEnum
from typing import Generic, Self, TypeVar
from pydantic import BaseModel

ColunaT = TypeVar("ColunaT", bound=StrEnum)


class FiltroColuna(BaseModel, Generic[ColunaT]):
    """Um filtro textual ativo aplicado a uma coluna específica."""

    coluna: ColunaT
    termo: str


class ConsultaListagem(BaseModel, Generic[ColunaT]):
    """Consulta estruturada com filtros cumulativos e ordenação opcional."""

    filtros: list[FiltroColuna[ColunaT]] = []
    ordenar_por: ColunaT | None = None
    descendente: bool = False

    @classmethod
    def de_parametros(
        cls,
        parametros: Mapping[str, str],
        enum_coluna: type[ColunaT],
    ) -> Self:
        """Constrói uma consulta tipada a partir de um dicionário de parâmetros (request.GET)."""
        filtros: list[FiltroColuna[ColunaT]] = []
        for coluna in enum_coluna:
            termo = parametros.get(coluna.value, "").strip()
            if termo:
                filtros.append(FiltroColuna(coluna=coluna, termo=termo))

        ordenar_slug = parametros.get("ordenar_por", "").strip()
        ordenar_por = None
        if ordenar_slug:
            try:
                ordenar_por = enum_coluna(ordenar_slug)
            except ValueError:
                ordenar_por = None

        descendente = parametros.get("descendente") in ("1", "true", "True")
        return cls(filtros=filtros, ordenar_por=ordenar_por, descendente=descendente)
