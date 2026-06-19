from pathlib import Path

from pydantic import BaseModel


class SegmentosLogradourosRequest(BaseModel):
    layer_name: str


class SegmentoLogradouro(BaseModel):
    codlog: str
    cd_identificador: str
    cd_numero_inicial_par: str | None = None
    cd_numero_final_par: str | None = None
    cd_numero_inicial_impar: str | None = None
    cd_numero_final_impar: str | None = None


class SegmentosLogradourosResult(BaseModel):
    total_segments: int
    output_path: Path
