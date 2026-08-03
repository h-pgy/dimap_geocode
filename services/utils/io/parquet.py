from collections.abc import Mapping, Sequence
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from . import config
from .atomic import escrever_atomico

Columns = Mapping[str, Sequence[object]]


def write_parquet(columns: Columns, filename: str, folder: Path | str) -> Path:
    path = Path(folder) / filename
    escrever_atomico(path, lambda destino: pq.write_table(pa.table(dict(columns)), destino))
    return path


def read_parquet(filename: str, folder: Path | str) -> dict[str, list[object]]:
    path = Path(folder) / filename
    return pq.read_table(path).to_pydict()


def write_parquet_to_data(columns: Columns, filename: str) -> Path:
    return write_parquet(columns, filename, folder=config.data_dir())


def read_parquet_from_data(filename: str) -> dict[str, list[object]]:
    return read_parquet(filename, folder=config.data_dir())
