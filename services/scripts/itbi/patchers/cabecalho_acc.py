from typing import ClassVar

import pandas as pd

from services.utils.normalization import normalize_text

from .base import ItbiPatcher

# 2019–2022 inteiros, NOV/DEZ-2023 e FEV/MAI/SET-2024 — levantado na primeira carga completa.
ANOS_CABECALHO_ACC: tuple[int, ...] = (2019, 2020, 2021, 2022, 2023, 2024)

CABECALHO_ERRADO: str = "ACC (IPTU)"
CABECALHO_CORRETO: str = "Descrição do padrão (IPTU)"
# O `.1` é como o pandas desempata dois cabeçalhos iguais: é a assinatura do defeito.
CABECALHO_DUPLICADO: str = "ACC (IPTU).1"


class PatcherCabecalhoAcc(ItbiPatcher):
    """A fonte grafa `Descrição do padrão (IPTU)` como `ACC (IPTU)`, duplicando o nome da coluna
    seguinte — e a descrição do padrão, que é texto, cai na coluna numérica do ano de construção."""

    anos: ClassVar[tuple[int, ...]] = ANOS_CABECALHO_ACC

    def aplicar(self, aba: pd.DataFrame) -> pd.DataFrame:
        por_normalizado = {normalize_text(str(coluna)): coluna for coluna in aba.columns}
        duplicado = por_normalizado.get(normalize_text(CABECALHO_DUPLICADO))
        errado = por_normalizado.get(normalize_text(CABECALHO_ERRADO))
        if duplicado is None or errado is None:
            return aba  # aba sã do mesmo ano: nada a consertar
        return aba.rename(
            columns={
                errado: CABECALHO_CORRETO,
                duplicado: CABECALHO_ERRADO,
            }
        )
