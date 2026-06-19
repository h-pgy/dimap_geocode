from pathlib import Path

from pydantic import BaseModel


class NomesLogradourosRequest(BaseModel):
    layer_name: str
    data_folder: Path


class LogradouroNome(BaseModel):
    codlog: str
    cd_tipo_logradouro: str
    nm_logradouro: str


class NomesLogradourosResult(BaseModel):
    total_unique: int
    output_path: Path
