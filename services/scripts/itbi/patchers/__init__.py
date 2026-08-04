from .base import ItbiPatcher, patch_all
from .cabecalho_acc import ANOS_CABECALHO_ACC, PatcherCabecalhoAcc
from .cabecalho_no_rodape import (
    ANOS_CABECALHO_NO_RODAPE,
    CABECALHOS_CANONICOS,
    PatcherCabecalhoNoRodape,
)
from .typo_pardao import ANOS_TYPO_PARDAO, PatcherTypoPardao

# Os consertos em vigor, na ordem de aplicação: primeiro dar nome às colunas, depois corrigir
# nome errado. Defeito novo entra aqui, e o parser não muda.
PATCHERS_ITBI: tuple[ItbiPatcher, ...] = (
    PatcherCabecalhoNoRodape(),
    PatcherCabecalhoAcc(),
    PatcherTypoPardao(),
)

__all__ = [
    "ItbiPatcher",
    "patch_all",
    "PatcherCabecalhoAcc",
    "PatcherCabecalhoNoRodape",
    "PatcherTypoPardao",
    "ANOS_CABECALHO_ACC",
    "ANOS_CABECALHO_NO_RODAPE",
    "ANOS_TYPO_PARDAO",
    "CABECALHOS_CANONICOS",
    "PATCHERS_ITBI",
]
