import json
from pathlib import Path
from typing import Any

from . import config
from .atomic import escrever_atomico


def read_json_from_folder(folder: Path, filename: str) -> dict[str, Any]:
    with open(folder / filename, encoding="utf-8") as f:
        return json.load(f)


def write_json_to_folder(
    folder: Path,
    filename: str,
    data: dict[str, Any],
) -> None:
    path = folder / filename
    conteudo = json.dumps(data, ensure_ascii=False, indent=2)
    escrever_atomico(path, lambda destino: destino.write_text(conteudo, encoding="utf-8"))


def read_json_from_data(filename: str) -> dict[str, Any]:
    return read_json_from_folder(config.data_dir(), filename)


def write_json_to_data(filename: str, data: dict[str, Any]) -> None:
    write_json_to_folder(config.data_dir(), filename, data)
