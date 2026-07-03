import pandas as pd

from .models import ContribuinteMatchOutput


def mapear_resultados(dataframe: pd.DataFrame) -> list[ContribuinteMatchOutput]:
    """DataFrame de enderecos_fiscais -> ContribuinteMatchOutput. Compartilhada entre matchers."""
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
