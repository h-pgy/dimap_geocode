from pathlib import Path

import pandas as pd

from . import config
from .atomic import escrever_atomico


def write_dataframe(quadro: pd.DataFrame, filename: str, folder: Path | str) -> Path:
    path = Path(folder) / filename
    escrever_atomico(path, lambda destino: quadro.to_parquet(destino, index=False))
    return path


def read_dataframe(filename: str, folder: Path | str) -> pd.DataFrame:
    return pd.read_parquet(Path(folder) / filename)


def write_dataframe_to_data(quadro: pd.DataFrame, filename: str) -> Path:
    return write_dataframe(quadro, filename, folder=config.data_dir())


def read_dataframe_from_data(filename: str) -> pd.DataFrame:
    return read_dataframe(filename, folder=config.data_dir())
