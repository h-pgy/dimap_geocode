import pandas as pd

from .catalog import ContribuinteCatalog
from .models import ContribuinteMatchInput, ContribuinteMatchOutput
from .parser import mapear_resultados


class ContribuinteMatcher:
    def __init__(self, catalog: ContribuinteCatalog | None = None) -> None:
        self._catalog = catalog or ContribuinteCatalog()

    def __call__(self, payload: ContribuinteMatchInput) -> list[ContribuinteMatchOutput]:
        return self._pipeline(payload)

    def _pipeline(self, payload: ContribuinteMatchInput) -> list[ContribuinteMatchOutput]:
        df = self._catalog.enderecos_fiscais
        mask = self._build_mask(df, payload)
        return mapear_resultados(df[mask].head(payload.limite))

    def _build_mask(self, df: pd.DataFrame, payload: ContribuinteMatchInput) -> pd.Series:
        mask = df["cd_setor_fiscal"].str.startswith(payload.setor)
        if payload.quadra:
            mask &= df["cd_quadra_fiscal"].str.startswith(payload.quadra)
        if payload.lote:
            mask &= df["cd_lote"].str.startswith(payload.lote)
        return mask
