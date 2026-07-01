import pandas as pd

from .catalog import ContribuinteCatalog
from .models import ContribuinteMatchInput, ContribuinteMatchOutput


class ContribuinteMatcher:
    def __init__(self, catalog: ContribuinteCatalog | None = None) -> None:
        self._catalog = catalog or ContribuinteCatalog()

    def __call__(self, payload: ContribuinteMatchInput) -> list[ContribuinteMatchOutput]:
        return self._pipeline(payload)

    def _pipeline(self, payload: ContribuinteMatchInput) -> list[ContribuinteMatchOutput]:
        df = self._catalog.enderecos_fiscais
        mask = self._build_mask(df, payload)
        return self._mapear_resultados(df[mask].head(payload.limite))

    def _build_mask(self, df: pd.DataFrame, payload: ContribuinteMatchInput) -> pd.Series:
        mask = df["cd_setor_fiscal"].str.startswith(payload.setor)
        if payload.quadra:
            mask &= df["cd_quadra_fiscal"].str.startswith(payload.quadra)
        if payload.lote:
            mask &= df["cd_lote"].str.startswith(payload.lote)
        return mask

    def _mapear_resultados(self, dataframe: pd.DataFrame) -> list[ContribuinteMatchOutput]:
        resultados: list[ContribuinteMatchOutput] = []
        for _, linha in dataframe.iterrows():
            resultados.append(
                ContribuinteMatchOutput(
                    id_poligono=str(linha["cd_identificador"]),
                    setor=str(linha["cd_setor_fiscal"]),
                    quadra=str(linha["cd_quadra_fiscal"]),
                    lote=str(linha["cd_lote"]),
                    digito=str(linha["cd_digito_sql"]) if pd.notna(linha["cd_digito_sql"]) else None,
                    codlog=str(linha["cd_logradouro"]),
                    logradouro=str(linha["nm_logradouro_completo"]),
                    numero=str(linha["cd_numero_porta"]),
                    complemento=str(linha["tx_complemento_endereco"]) if pd.notna(linha["tx_complemento_endereco"]) else None,
                    tipo_quadra=str(linha["cd_tipo_quadra"]),
                    tipo_lote=str(linha["cd_tipo_lote"]),
                )
            )
        return resultados
