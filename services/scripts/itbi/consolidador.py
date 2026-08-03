from pathlib import Path

import pandas as pd

from services.utils.io import read_dataframe

from .constants import PADRAO_NOME_PARQUET
from .disco import anos_em_disco
from .exceptions import ItbiCargaVaziaError
from .models import ConsolidacaoItbi, ConsolidacaoStats


class ItbiConsolidador:
    """ETAPA 3: parquets por ano → parquet único.

    Não interpreta nada: os insumos já vêm com o esquema final, escritos por esta carga ou por
    uma anterior. É isso que impede o parquet de encolher quando o portal despublica um ano ou
    quando a planilha nova vem quebrada.
    """

    def __call__(self, parseados: Path) -> ConsolidacaoItbi:
        return self.pipeline(parseados)

    def pipeline(self, parseados: Path) -> ConsolidacaoItbi:
        por_ano = self._carregar(parseados)
        dados = pd.concat(por_ano.values(), ignore_index=True)
        return ConsolidacaoItbi(
            stats=ConsolidacaoStats(
                anos_no_parquet=sorted(por_ano),
                total_records=len(dados),
            ),
            dados=dados,
            linhas_por_ano={ano: len(quadro) for ano, quadro in por_ano.items()},
        )

    def _carregar(self, parseados: Path) -> dict[int, pd.DataFrame]:
        arquivos = anos_em_disco(parseados, PADRAO_NOME_PARQUET)
        if not arquivos:
            raise ItbiCargaVaziaError("nenhum ano parseado em disco: parquet anterior preservado")
        return {
            ano: read_dataframe(arquivo.name, folder=parseados)
            for ano, arquivo in sorted(arquivos.items())
        }
