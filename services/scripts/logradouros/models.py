from pathlib import Path

from pydantic import BaseModel


class NomesLogradourosRequest(BaseModel):
    layer_name: str


class LogradouroNome(BaseModel):
    codlog: str
    tipo_logradouro: str
    nm_logradouro: str


class NomesLogradourosResult(BaseModel):
    total_unique: int
    output_path: Path
