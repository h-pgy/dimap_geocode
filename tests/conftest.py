from collections.abc import Generator

import pytest

from services.domain.contribuinte_match import ContribuinteCatalog
from services.domain.logradouros_match import LogradouroCatalog


@pytest.fixture(autouse=True)
def _resetar_catalogos_singleton() -> Generator[None, None, None]:
    # Os catálogos são singletons (SPEC infraestrutura/003, Patch 002); sem o reset,
    # o cache TTL populado com dados sintéticos de um teste vazaria para os seguintes.
    LogradouroCatalog.resetar_instancia()
    ContribuinteCatalog.resetar_instancia()
    yield
    LogradouroCatalog.resetar_instancia()
    ContribuinteCatalog.resetar_instancia()
