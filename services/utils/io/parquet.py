from collections.abc import Mapping, Sequence
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

Columns = Mapping[str, Sequence[object]]


def write_parquet(columns: Columns, filename: str, folder: Path | str) -> Path:
    path = Path(folder) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(dict(columns)), path)
    return path


def read_parquet(filename: str, folder: Path | str) -> dict[str, list[object]]:
    path = Path(folder) / filename
    return pq.read_table(path).to_pydict()
