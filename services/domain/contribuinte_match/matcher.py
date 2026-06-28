import pandas as pd

from services.utils.cache import ttl_cached_property
from services.utils.io import read_parquet_from_data

from .models import ContribuinteMatchInput, ContribuinteMatchOutput

NOME_ARQUIVO_PADRAO = "enderecos_fiscais.parquet"


class ContribuinteMatcher:
    def __init__(self, nome_arquivo: str = NOME_ARQUIVO_PADRAO) -> None:
        self._nome_arquivo = nome_arquivo

    @ttl_cached_property(ttl_seconds=3600)
    def _dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(read_parquet_from_data(self._nome_arquivo))

    def __call__(self, payload: ContribuinteMatchInput) -> list[ContribuinteMatchOutput]:
        df = self._dataframe
        mask = df["cd_setor_fiscal"].str.startswith(payload.setor)
        if payload.quadra:
            mask &= df["cd_quadra_fiscal"].str.startswith(payload.quadra)
        if payload.lote:
            mask &= df["cd_lote"].str.startswith(payload.lote)
        return self._mapear_resultados(df[mask].head(payload.limite))

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


match_contribuinte = ContribuinteMatcher()
