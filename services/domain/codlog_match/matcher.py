import pandas as pd

from services.utils.cache import ttl_cached_property
from services.utils.io import read_parquet_from_data

from .models import CodlogMatchInput, CodlogMatchOutput

NOME_ARQUIVO_PADRAO = "nomes_logradouros.parquet"


class CodlogMatcher:
    def __init__(self, nome_arquivo: str = NOME_ARQUIVO_PADRAO) -> None:
        self._nome_arquivo = nome_arquivo

    @ttl_cached_property(ttl_seconds=3600)
    def _dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame(read_parquet_from_data(self._nome_arquivo))
        df["_codlog5"] = df["codlog"].str[:5]
        return df

    def __call__(self, payload: CodlogMatchInput) -> list[CodlogMatchOutput]:
        df = self._filtrar(payload.input_codlog)
        return self._mapear_resultados(df.head(payload.limite))

    def _filtrar(self, input_codlog: str) -> pd.DataFrame:
        if len(input_codlog) < 5:
            return self._dataframe[self._dataframe["_codlog5"].str.startswith(input_codlog)]
        return self._dataframe[self._dataframe["_codlog5"] == input_codlog]

    def _mapear_resultados(self, dataframe: pd.DataFrame) -> list[CodlogMatchOutput]:
        resultados: list[CodlogMatchOutput] = []
        for _, linha in dataframe.iterrows():
            resultados.append(
                CodlogMatchOutput(
                    codlog=str(linha["codlog"])[:5],
                    dv=str(linha["codlog"])[5],
                    tipo_logradouro=str(linha["cd_tipo_logradouro"]),
                    nome_logradouro=str(linha["nm_logradouro"]),
                )
            )
        return resultados


match_codlog = CodlogMatcher()
