from pathlib import Path

from services.utils.io import read_parquet, write_parquet


def test_write_and_read_roundtrip_with_folder(tmp_path: Path) -> None:
    cols = {"codlog": ["168610", "100000"], "nm_logradouro": ["RAMOS DE AZEVEDO", "DIREITA"]}
    path = write_parquet(cols, "nomes.parquet", folder=tmp_path)
    assert path == Path(tmp_path) / "nomes.parquet"
    assert read_parquet("nomes.parquet", folder=tmp_path) == cols


def test_write_creates_missing_folder(tmp_path: Path) -> None:
    sub = tmp_path / "data"
    write_parquet({"codlog": ["1"]}, "x.parquet", folder=sub)
    assert (sub / "x.parquet").exists()
