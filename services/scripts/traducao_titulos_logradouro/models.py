from pydantic import BaseModel

from .constants import (
    OUTPUT_PARQUET_NAME,
    PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL,
    TRADUCAO_TITULOS_MANUAL,
)


class TraducaoTitulosConfig(BaseModel):
    input_json_name: str = TRADUCAO_TITULOS_MANUAL
    input_parquet_name: str = PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL
    output_parquet_name: str = OUTPUT_PARQUET_NAME


class TraducaoTitulosStats(BaseModel):
    n_titulos: int
    siglas_sem_extenso: list[str] = []
