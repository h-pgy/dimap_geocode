from .augment_tipos_logradouro import OUTPUT_PARQUET_NAME, pipeline
from .constants import PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL, TIPOS_LOGRADOURO_AUMENTADO_MANUAL
from .models import AugmentStats


def run(
    input_json_name: str = TIPOS_LOGRADOURO_AUMENTADO_MANUAL,
    input_parquet_name: str = PARQUET_NOMES_LOGRADOURO_BASE_ORIGINAL,
    output_parquet_name: str = OUTPUT_PARQUET_NAME,
) -> AugmentStats:
    return pipeline(
        input_json_name=input_json_name,
        input_parquet_name=input_parquet_name,
        output_parquet_name=output_parquet_name,
    )
