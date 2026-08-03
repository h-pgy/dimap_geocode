from pydantic import BaseModel

from .constants import (
    OUTPUT_PARQUET_NAME,
    PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL,
    TIPOS_LOGRADOURO_AUMENTADO_MANUAL,
)


class AugmentConfig(BaseModel):
    input_json_name: str = TIPOS_LOGRADOURO_AUMENTADO_MANUAL
    input_parquet_name: str = PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL
    output_parquet_name: str = OUTPUT_PARQUET_NAME


class AugmentStats(BaseModel):
    n_original: int
    n_variacoes: int
    n_total: int
    tipos_nao_mapeados: list[str] = []
    # só apurado quando verbose: {"AVENIDA": 47, ...} — quem imprime é o comando
    variacoes_por_tipo: dict[str, int] | None = None
