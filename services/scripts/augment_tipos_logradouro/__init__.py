from .augment_tipos_logradouro import (
    AugmentStats,
    OUTPUT_PARQUET_NAME,
    pipeline
)

from .constants import (
    TIPOS_LOGRADOURO_AUMENTADO_MANUAL,
    PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL,
    QWERTY_ABNT2_NEIGHBORS
)

from .models import AugmentStats

from .gerar_variacoes_typos_qwerty import (
    gerar_variacoes_nome,
)

__all__ = [
    "run",
    "AugmentStats",
    "OUTPUT_PARQUET_NAME",
    "gerar_variacoes_nome",
    "QWERTY_ABNT2_NEIGHBORS",
]


def run(
        input_json_name: str = TIPOS_LOGRADOURO_AUMENTADO_MANUAL,
        input_parquet_name: str = PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL,
        output_parquet_name: str = OUTPUT_PARQUET_NAME,
    ) -> AugmentStats:


    return pipeline(
        input_json_name=input_json_name,
        input_parquet_name=input_parquet_name,
        output_parquet_name=output_parquet_name
    )









