import os
from collections.abc import Callable
from pathlib import Path


def escrever_atomico(path: Path, escrever: Callable[[Path], object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    # MESMA pasta (rename atômico exige mesmo filesystem) e PID no nome: o daemon da SPEC 007 e um
    # comando manual podem escrever o mesmo artefato ao mesmo tempo sem compartilhar temporário.
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        escrever(tmp)
        os.replace(tmp, path)  # POSIX: atômico e sobrescreve o destino
    except BaseException:
        tmp.unlink(missing_ok=True)  # não deixa sobra em data/
        raise
    return path
