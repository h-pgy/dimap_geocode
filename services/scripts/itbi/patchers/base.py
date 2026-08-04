from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import ClassVar

import pandas as pd


class ItbiPatcher(ABC):
    """Conserto de um defeito conhecido da planilha, restrito aos anos em que ele ocorre.

    Contrato único: recebe DataFrame, devolve DataFrame. Um patcher não lê arquivo, não conhece
    o portal e não guarda estado — é isso que faz o teste dele ser uma entrada e uma saída.
    """

    #: Restringir por ano é o que impede o conserto de mascarar mudança de esquema legítima.
    anos: ClassVar[tuple[int, ...]]

    def __call__(self, aba: pd.DataFrame, ano: int) -> pd.DataFrame:
        if not self.admite(ano):
            return aba
        return self.aplicar(aba)

    def admite(self, ano: int) -> bool:
        return ano in self.anos

    @abstractmethod
    def aplicar(self, aba: pd.DataFrame) -> pd.DataFrame:
        """O conserto. Aba sã de um ano admitido tem que passar intacta."""


def patch_all(
    aba: pd.DataFrame,
    ano: int,
    patchers: Sequence[ItbiPatcher],
) -> pd.DataFrame:
    for patcher in patchers:
        aba = patcher(aba, ano)
    return aba
