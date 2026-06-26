import json
from functools import partial
from pathlib import Path
from typing import Any

from .config import _DATA_DIR


def read_json_from_folder(folder: Path, filename: str) -> dict[str, Any]:
    with open(folder / filename, encoding="utf-8") as f:
        return json.load(f)


def write_json_to_folder(
    folder: Path, filename: str, data: dict[str, Any]
) -> None:
    with open(folder / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


read_json_from_data: Any = partial(read_json_from_folder, _DATA_DIR)
write_json_to_data: Any = partial(write_json_to_folder, _DATA_DIR)
