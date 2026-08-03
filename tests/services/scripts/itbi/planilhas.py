"""Planilhas sintéticas do ITBI — o insumo dos testes das etapas 2 e 3."""

from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from services.scripts.itbi import COLUNAS_DATA, COLUNAS_NUMERICAS, MAPA_COLUNAS


def _valor(saida: str, linha: int) -> object:
    if saida in COLUNAS_NUMERICAS:
        return float(linha + 1)
    if saida in COLUNAS_DATA:
        return f"2026-01-{linha + 10:02d}"
    return f"{saida}-{linha}"


def aba_completa(linhas: int = 2) -> pd.DataFrame:
    """Aba com TODOS os cabeçalhos do MAPA_COLUNAS — o ponto de partida das divergências."""
    return pd.DataFrame(
        {
            cabecalho: [_valor(saida, linha) for linha in range(linhas)]
            for cabecalho, saida in MAPA_COLUNAS.items()
        }
    )


def escrever_xlsx(destino: Path, abas: Mapping[str, pd.DataFrame]) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(destino, engine="openpyxl") as writer:
        for nome, quadro in abas.items():
            quadro.to_excel(writer, sheet_name=nome, index=False)
    return destino
