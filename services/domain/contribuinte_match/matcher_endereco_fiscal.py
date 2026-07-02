import pandas as pd

from .catalog import ContribuinteCatalog
from .parser import mapear_resultados
from .models import ContribuinteMatchOutput, EnderecoFiscalMatchInput


class EnderecoFiscalMatcher:
    def __init__(self, catalog: ContribuinteCatalog | None = None) -> None:
        self._catalog = catalog or ContribuinteCatalog()

    def __call__(self, payload: EnderecoFiscalMatchInput) -> list[ContribuinteMatchOutput]:
        return self._pipeline(payload)

    def _pipeline(self, payload: EnderecoFiscalMatchInput) -> list[ContribuinteMatchOutput]:
        df = self._catalog.enderecos_fiscais_com_chave
        mask = self._build_mask(df, payload)
        return mapear_resultados(df[mask].head(payload.limite))

    def _build_mask(self, df: pd.DataFrame, payload: EnderecoFiscalMatchInput) -> pd.Series:
        # numero_padronizado JÁ é a chave (feita no parse) — o matcher não normaliza nada.
        # isin contra codlog5 (coluna preparada no catalog): cd_logradouro tem 6 dígitos
        # (codlog+DV) no parquet e os matchers de logradouro devolvem codlog de 5.
        return df["codlog5"].isin(payload.codlogs) & df["chave_numero_porta"].str.startswith(
            payload.numero_padronizado
        )
