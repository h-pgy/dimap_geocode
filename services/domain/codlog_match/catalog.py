import time
from typing import ClassVar

import pandas as pd

from services.utils.cache import ttl_cached_property
from services.utils.io import read_parquet_from_data

NOME_ARQUIVO_PADRAO = "nomes_logradouros.parquet"
DATA_TTL_SECONDS = 24 * 60 * 60  # padronizado com LogradouroCatalog (mesmo parquet)


class CodlogCatalog:
    _instancia: ClassVar["CodlogCatalog | None"] = None

    def __new__(cls, *args: object, **kwargs: object) -> "CodlogCatalog":
        # singleton só na classe exata: subclasses (fakes de teste) constroem normalmente
        if cls is not CodlogCatalog:
            return super().__new__(cls)
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
        return cls._instancia

    @classmethod
    def resetar_instancia(cls) -> None:
        # isolamento de testes: a próxima construção nasce fria
        cls._instancia = None

    def __init__(self, nome_arquivo: str = NOME_ARQUIVO_PADRAO) -> None:
        # __init__ roda a cada "construção" do singleton — só a primeira grava o arquivo
        if not hasattr(self, "_nome_arquivo"):
            self._nome_arquivo = nome_arquivo

    @ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
    def logradouros(self) -> pd.DataFrame:
        df = pd.DataFrame(read_parquet_from_data(self._nome_arquivo))
        df["_codlog5"] = df["codlog"].str[:5]
        return df

    def aquecer(self) -> None:
        print("[CodlogCatalog] aquecendo cache...")
        inicio = time.perf_counter()
        _ = self.logradouros
        duracao = time.perf_counter() - inicio
        print(f"[CodlogCatalog] cache aquecido em {duracao:.2f}s")
