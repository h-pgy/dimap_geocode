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
    nm_logradouro: str


class NomesLogradourosResult(BaseModel):
    total_unique: int
    output_path: Path
