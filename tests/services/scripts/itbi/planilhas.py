"""Planilhas sintéticas do ITBI — o insumo dos testes das etapas 2 e 3."""

from collections.abc import Collection, Mapping
from pathlib import Path

import pandas as pd

from services.scripts.itbi import COLUNAS_DATA, COLUNAS_NUMERICAS, MAPA_COLUNAS


def _valor(saida: str, linha: int) -> object:
    if saida in COLUNAS_NUMERICAS:
        return float(linha + 1)
    if saida in COLUNAS_DATA:
        # Dia dentro do mês para qualquer número de linhas — data inválida derrubaria a aba.
        return f"2026-01-{linha % 28 + 1:02d}"
    return f"{saida}-{linha}"


def aba_completa(linhas: int = 2) -> pd.DataFrame:
    """Aba com TODOS os cabeçalhos do MAPA_COLUNAS — o ponto de partida das divergências."""
    return pd.DataFrame(
        {
            cabecalho: [_valor(saida, linha) for linha in range(linhas)]
            for cabecalho, saida in MAPA_COLUNAS.items()
        }
    )


def _com_titulo_no_fim(quadro: pd.DataFrame) -> pd.DataFrame:
    titulo = pd.DataFrame([list(quadro.columns)], columns=quadro.columns)
    return pd.concat([quadro, titulo], ignore_index=True)


def escrever_xlsx(
    destino: Path,
    abas: Mapping[str, pd.DataFrame],
    cabecalho_no_rodape: Collection[str] = (),
) -> Path:
    """`cabecalho_no_rodape` reproduz as abas em que o portal pôs a linha de título no fim."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(destino, engine="openpyxl") as writer:
        for nome, quadro in abas.items():
            if nome in cabecalho_no_rodape:
                quadro = _com_titulo_no_fim(quadro)
            quadro.to_excel(
                writer,
                sheet_name=nome,
                index=False,
                header=nome not in cabecalho_no_rodape,
            )
    return destino
