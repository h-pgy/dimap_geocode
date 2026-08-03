from pathlib import Path

import pytest

from services.utils.io import config, read_parquet_from_data, write_parquet_to_data


def test_diretorio_de_dados_resolvido_na_chamada(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destino = tmp_path / "outro_data"
    # Patch APENAS no ponto único de resolução, depois do import: se parquet.py e json.py
    # tivessem cada um sua ligação para data_dir, o redirecionamento não alcançaria os
    # escritores e a suíte seguiria escrevendo na data/ real — passando.
    monkeypatch.setattr(config, "data_dir", lambda: destino)

    colunas = {"codlog": ["168610"]}
    caminho = write_parquet_to_data(colunas, "nomes.parquet")

    assert caminho == destino / "nomes.parquet"
    assert read_parquet_from_data("nomes.parquet") == colunas
