import time
from typing import ClassVar, cast

from services.utils.cache import ttl_cached_property
from services.utils.io import read_parquet_from_data

from .models import LogradouroRow

TIPOS_CACHE_FILE = "tipos_logradouro_cache.parquet"
NOMES_LOGRADOUROS_FILE = "nomes_logradouros.parquet"
DATA_TTL_SECONDS = 24 * 60 * 60


class LogradouroCatalog:
    _instancia: ClassVar["LogradouroCatalog | None"] = None

    def __new__(cls, *args: object, **kwargs: object) -> "LogradouroCatalog":
        # singleton só na classe exata: subclasses (fakes de teste) constroem normalmente
        if cls is not LogradouroCatalog:
            return super().__new__(cls)
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
        return cls._instancia

    @classmethod
    def resetar_instancia(cls) -> None:
        # isolamento de testes: a próxima construção nasce fria
        cls._instancia = None

    @ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
    def _variacoes(self) -> dict[str, str]:
        cols = read_parquet_from_data(TIPOS_CACHE_FILE)
        nomes = cast(list[str], cols["nome_tipo"])
        codigos = cast(list[str], cols["cd_tipo_logradouro"])
        return dict(zip(nomes, codigos))

    @ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
    def _rows(self) -> list[LogradouroRow]:
        cols = read_parquet_from_data(NOMES_LOGRADOUROS_FILE)
        codlogs = cast(list[str], cols["codlog"])
        tipos = cast(list[str], cols["cd_tipo_logradouro"])
        nomes = cast(list[str], cols["nm_logradouro"])
        return [
            LogradouroRow(codlog=c[:5], dv=c[5], tipo_logradouro=t, nm_logradouro=n)
            for c, t, n in zip(codlogs, tipos, nomes)
        ]

    @ttl_cached_property(ttl_seconds=DATA_TTL_SECONDS)
    def _por_tipo(self) -> dict[str, list[LogradouroRow]]:
        indice: dict[str, list[LogradouroRow]] = {}
        for row in self._rows:
            indice.setdefault(row.tipo_logradouro, []).append(row)
        return indice

    @property
    def variacoes_tipo(self) -> list[str]:
        return list(self._variacoes.keys())

    def codigo_da_variacao(self, variacao: str) -> str | None:
        return self._variacoes.get(variacao)

    def linhas_do_tipo(self, codigo: str) -> list[LogradouroRow]:
        return self._por_tipo.get(codigo, [])

    def todas_as_linhas(self) -> list[LogradouroRow]:
        return self._rows

    def linhas_por_nome(self, nome: str, codigo: str | None) -> list[LogradouroRow]:
        universo = self.linhas_do_tipo(codigo) if codigo else self._rows
        return [row for row in universo if row.nm_logradouro == nome]

    def aquecer(self) -> None:
        print("[LogradouroCatalog] aquecendo cache...")
        inicio = time.perf_counter()
        _ = self._variacoes
        _ = self._por_tipo
        duracao = time.perf_counter() - inicio
        print(f"[LogradouroCatalog] cache aquecido em {duracao:.2f}s")
