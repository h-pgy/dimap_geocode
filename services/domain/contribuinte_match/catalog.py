import time

import pandas as pd

from services.utils.cache import ttl_cached_property
from services.utils.io import read_parquet_from_data

NOME_ARQUIVO_PADRAO = "enderecos_fiscais.parquet"
DATA_TTL_SECONDS = 3600


class ContribuinteCatalog:
    def __init__(self, nome_arquivo: str = NOME_ARQUIVO_PADRAO) -> None:
        self._nome_arquivo = nome_arquivo

    @ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
    def enderecos_fiscais(self) -> pd.DataFrame:
        return pd.DataFrame(read_parquet_from_data(self._nome_arquivo))

    def aquecer(self) -> None:
        print("[ContribuinteCatalog] aquecendo cache...")
        inicio = time.perf_counter()
        _ = self.enderecos_fiscais
        duracao = time.perf_counter() - inicio
        print(f"[ContribuinteCatalog] cache aquecido em {duracao:.2f}s")
