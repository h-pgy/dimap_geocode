from collections.abc import Mapping, Sequence
from functools import partial
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .config import _DATA_DIR

Columns = Mapping[str, Sequence[object]]


def write_parquet(columns: Columns, filename: str, folder: Path | str) -> Path:
    path = Path(folder) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(dict(columns)), path)
    return path


def read_parquet(filename: str, folder: Path | str) -> dict[str, list[object]]:
    path = Path(folder) / filename
    return pq.read_table(path).to_pydict()


write_parquet_to_data = partial(write_parquet, folder=_DATA_DIR)
read_parquet_from_data = partial(read_parquet, folder=_DATA_DIR)
