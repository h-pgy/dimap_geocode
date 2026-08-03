from pathlib import Path

from pydantic import BaseModel

from services.integrations.wfs import WfsConnectionConfig, WfsRetryPolicy


class SegmentosLogradourosConfig(BaseModel):
    layer_name: str
    conexao: WfsConnectionConfig
    retry: WfsRetryPolicy


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
