from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, field_serializer, field_validator

from .constants import FORMATO_DATA


class MetadadoArquivo(BaseModel):
    """Uma entrada do JSON de metadados — duas linhas do tempo no mesmo registro."""

    arquivo: str
    # Última TENTATIVA: carimbada sempre, deu certo ou não.
    status: Literal["sucesso", "falha"]
    last_run: datetime
    manual: bool
    erro: str | None = None
    traceback: str | None = None
    # Última ESCRITA bem-sucedida: devolvidas intactas quando a tentativa falha.
    last_successful_run: datetime | None = None
    registros: int | None = None
    # O que só o script sabe sobre a carga (ex.: o que falhou por ano). Chega pronto para JSON:
    # o módulo não conhece o DTO de resultado de script nenhum.
    detalhes: dict[str, Any] | None = None

    @field_validator("last_run", "last_successful_run", mode="before")
    @classmethod
    def _parsear_data(cls, valor: object) -> object:
        if isinstance(valor, str):
            return datetime.strptime(valor, FORMATO_DATA)
        return valor

    @field_serializer("last_run", "last_successful_run")
    def _formatar_data(self, valor: datetime | None) -> str | None:
        if valor is None:
            return None
        return valor.strftime(FORMATO_DATA)
