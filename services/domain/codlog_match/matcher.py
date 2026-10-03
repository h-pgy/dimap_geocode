import pandas as pd

from .catalog import CodlogCatalog
from .models import CodlogMatchInput, CodlogMatchOutput


def _opcional(valor: str | float | None) -> str | None:
    # O DataFrame troca a ausência por NaN; `str()` a transformaria em "nan".
    return None if pd.isna(valor) else str(valor)


class CodlogMatcher:
    def __init__(self, catalog: CodlogCatalog | None = None) -> None:
        self._catalog = catalog or CodlogCatalog()

    def __call__(self, payload: CodlogMatchInput) -> list[CodlogMatchOutput]:
        return self._pipeline(payload)

    def _pipeline(self, payload: CodlogMatchInput) -> list[CodlogMatchOutput]:
        df = self._filtrar(payload.input_codlog)
        return self._mapear_resultados(df.head(payload.limite))

    def _filtrar(self, input_codlog: str) -> pd.DataFrame:
        df = self._catalog.logradouros
        if len(input_codlog) < 5:
            return df[df["_codlog5"].str.startswith(input_codlog)]
        return df[df["_codlog5"] == input_codlog]

    def _mapear_resultados(self, dataframe: pd.DataFrame) -> list[CodlogMatchOutput]:
        resultados: list[CodlogMatchOutput] = []
        for _, linha in dataframe.iterrows():
            resultados.append(
                CodlogMatchOutput(
                    codlog=str(linha["codlog"])[:5],
                    dv=str(linha["codlog"])[5],
                    tipo_logradouro=str(linha["cd_tipo_logradouro"]),
                    titulo=_opcional(linha["cd_titulo_logradouro"]),
                    preposicao=_opcional(linha["tx_preposicao_logradouro"]),
                    nome_logradouro=str(linha["nm_logradouro"]),
                )
            )
        return resultados
