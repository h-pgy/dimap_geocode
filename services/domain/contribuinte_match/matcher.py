import pandas as pd

from services.utils.io import read_parquet_from_data

from .models import ContribuinteMatchInput, ContribuinteMatchOutput

NOME_ARQUIVO_PADRAO = "enderecos_fiscais.parquet"


class ContribuinteMatcher:
    def __init__(self, nome_arquivo: str = NOME_ARQUIVO_PADRAO) -> None:
        self._dataframe: pd.DataFrame = pd.DataFrame(read_parquet_from_data(nome_arquivo))

    def __call__(self, payload: ContribuinteMatchInput) -> list[ContribuinteMatchOutput]:
        if payload.lote:
            df = self._busca_lote(payload.setor, payload.quadra, payload.lote)  # type: ignore[arg-type]
        elif payload.quadra:
            df = self._busca_quadra(payload.setor, payload.quadra).head(payload.limite)
        else:
            df = self._busca_setor(payload.setor).head(payload.limite)
        return self._mapear_resultados(df)

    def _busca_setor(self, setor: str) -> pd.DataFrame:
        return self._dataframe[self._dataframe["cd_setor_fiscal"] == setor]

    def _busca_quadra(self, setor: str, quadra: str) -> pd.DataFrame:
        df = self._busca_setor(setor)
        return df[df["cd_quadra_fiscal"] == quadra]

    def _busca_lote(self, setor: str, quadra: str, lote: str) -> pd.DataFrame:
        df = self._busca_quadra(setor, quadra)
        return df[df["cd_lote"] == lote]

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
