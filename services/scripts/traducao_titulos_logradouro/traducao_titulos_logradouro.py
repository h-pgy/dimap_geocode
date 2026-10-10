from typing import cast

from services.utils.io import read_json_from_data, read_parquet_from_data, write_parquet_to_data
from services.utils.normalization import normalize_text

from .models import TraducaoTitulosConfig, TraducaoTitulosStats

COL_SIGLA = "cd_titulo_logradouro"
COL_EXTENSO = "nome_titulo"


def siglas_sem_extenso(dicionario: dict[str, str], input_parquet_name: str) -> list[str]:
    parquet = read_parquet_from_data(input_parquet_name)
    siglas_da_camada = {str(sigla) for sigla in parquet[COL_SIGLA] if sigla}
    return sorted(siglas_da_camada - set(dicionario))


def pipeline(config: TraducaoTitulosConfig) -> TraducaoTitulosStats:
    dicionario = cast(dict[str, str], read_json_from_data(config.input_json_name))
    sem_extenso = siglas_sem_extenso(dicionario, config.input_parquet_name)
    siglas = list(dicionario)
    # O literal compara contra a consulta normalizada: `Cônego` chega ao catálogo como `CONEGO`.
    extensos = [normalize_text(extenso) for extenso in dicionario.values()]
    write_parquet_to_data({COL_SIGLA: siglas, COL_EXTENSO: extensos}, config.output_parquet_name)
    return TraducaoTitulosStats(n_titulos=len(siglas), siglas_sem_extenso=sem_extenso)
