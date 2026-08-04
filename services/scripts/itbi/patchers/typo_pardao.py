from typing import ClassVar

import pandas as pd

from services.utils.normalization import normalize_text

from .base import ItbiPatcher

# Parte das abas de 2026 — levantado na carga de 2026-08-03.
ANOS_TYPO_PARDAO: tuple[int, ...] = (2026,)

CABECALHO_COM_TYPO: str = "Descrição do pardão (IPTU)"
CABECALHO_CORRETO: str = "Descrição do padrão (IPTU)"


class PatcherTypoPardao(ItbiPatcher):
    """A fonte grafa `padrão` como `pardão` em parte das abas, e a coluna cai fora do
    MAPA_COLUNAS — `padrao_construtivo_desc` sairia nula naquelas abas."""

    anos: ClassVar[tuple[int, ...]] = ANOS_TYPO_PARDAO

    def aplicar(self, aba: pd.DataFrame) -> pd.DataFrame:
        alvo = normalize_text(CABECALHO_COM_TYPO)
        com_typo = [coluna for coluna in aba.columns if normalize_text(str(coluna)) == alvo]
        if not com_typo:
            return aba  # aba do mesmo ano que grafa certo: a maioria
        return aba.rename(columns={coluna: CABECALHO_CORRETO for coluna in com_typo})
