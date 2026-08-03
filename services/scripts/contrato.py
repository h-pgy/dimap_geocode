from typing import Protocol, TypeVar

from pydantic import BaseModel

Cfg = TypeVar("Cfg", bound=BaseModel, contravariant=True)
Res = TypeVar("Res", bound=BaseModel, covariant=True)


class ScriptRunner(Protocol[Cfg, Res]):
    """Todo script de carga entra por aqui: um Config, e as duas chaves do pipeline."""

    def __call__(self, config: Cfg, *, verbose: bool = False, manual: bool = True) -> Res: ...
