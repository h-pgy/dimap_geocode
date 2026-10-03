from pathlib import Path

from pydantic import BaseModel

from services.integrations.wfs import WfsConnectionConfig, WfsRetryPolicy


class NomesLogradourosConfig(BaseModel):
    layer_name: str
    conexao: WfsConnectionConfig
    retry: WfsRetryPolicy


class LogradouroNome(BaseModel):
    codlog: str
    tipo_logradouro: str
    titulo: str | None = None
    preposicao: str | None = None
    nm_logradouro: str


class NomesLogradourosResult(BaseModel):
    total_unique: int
    output_path: Path
