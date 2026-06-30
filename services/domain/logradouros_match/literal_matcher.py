from services.utils.normalization import normalize_text

from .catalog import LogradouroCatalog
from .models import (
    LiteralLogradouroQuery,
    LiteralLogradouroResult,
    LogradouroMatchOutput,
    LogradouroRow,
)


class LiteralLogradouroMatcher:
    def __init__(self, catalog: LogradouroCatalog) -> None:
        self._catalog = catalog

    def __call__(self, query: LiteralLogradouroQuery) -> LiteralLogradouroResult:
        return self._pipeline(query)

    def _pipeline(self, query: LiteralLogradouroQuery) -> LiteralLogradouroResult:
        nome = normalize_text(query.nome)
        if not nome:
            return self._build([], query.limite, ignorou=False)
        tipo_informado = bool(query.tipo and query.tipo.strip())
        codigo = self._resolve_tipo(query.tipo)
        if codigo is not None:
            rows = self._match_nome(nome, codigo)
            if rows:
                return self._build(rows, query.limite, ignorou=False)
        rows = self._match_nome(nome, None)
        return self._build(rows, query.limite, ignorou=tipo_informado)

    def _resolve_tipo(self, tipo: str | None) -> str | None:
        if not tipo or not tipo.strip():
            return None
        return self._catalog.codigo_da_variacao(normalize_text(tipo))

    def _match_nome(self, nome: str, codigo: str | None) -> list[LogradouroRow]:
        universo = (
            self._catalog.linhas_do_tipo(codigo) if codigo else self._catalog.todas_as_linhas()
        )
        prefixo = [row for row in universo if row.nm_logradouro.startswith(nome)]
        if prefixo:
            return prefixo
        return [row for row in universo if nome in row.nm_logradouro]

    def _build(
        self, rows: list[LogradouroRow], limite: int, ignorou: bool
    ) -> LiteralLogradouroResult:
        logradouros = [
            LogradouroMatchOutput(
                codlog=row.codlog,
                dv=row.dv,
                tipo_codigo=row.cd_tipo_logradouro,
                nome_logradouro=row.nm_logradouro,
            )
            for row in rows[:limite]
        ]
        return LiteralLogradouroResult(
            logradouros=logradouros,
            ignorou_filtro_tipo=ignorou,
        )
