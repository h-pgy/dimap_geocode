from .catalog import LogradouroCatalog
from .literal_matcher import LiteralLogradouroMatcher
from .matcher import LogradouroMatcher
from .models import (
    LiteralLogradouroQuery,
    LiteralLogradouroResult,
    LogradouroMatchOutput,
    LogradouroMatchQuery,
    LogradouroMatchResult,
    LogradouroRow,
    ResolucaoLogradouroItem,
    ResolucaoLogradouroQuery,
    ResolucaoLogradouroResult,
)

FUZZY_ACCEPT_THRESHOLD = 80.0
FUZZY_MIN_CHARS_SUGESTAO = 4


class LogradouroResolver:
    def __init__(
        self,
        literal: LiteralLogradouroMatcher,
        fuzzy: LogradouroMatcher,
        catalog: LogradouroCatalog,
        threshold: float = FUZZY_ACCEPT_THRESHOLD,
    ) -> None:
        self._literal = literal
        self._fuzzy = fuzzy
        self._catalog = catalog
        self._threshold = threshold

    def __call__(self, query: ResolucaoLogradouroQuery) -> ResolucaoLogradouroResult:
        return self._pipeline(query)

    def _pipeline(self, query: ResolucaoLogradouroQuery) -> ResolucaoLogradouroResult:
        literal = self._tentar_literal(query)
        if literal.logradouros:
            return self._resultado_literal(literal)
        if not self._fuzzy_permitido(query):
            return ResolucaoLogradouroResult(itens=[], usou_fuzzy=False)
        return self._tentar_fuzzy(query)

    def _tentar_literal(self, query: ResolucaoLogradouroQuery) -> LiteralLogradouroResult:
        return self._literal(
            LiteralLogradouroQuery(nome=query.nome, tipo=query.tipo, limite=query.limite)
        )

    def _resultado_literal(self, literal: LiteralLogradouroResult) -> ResolucaoLogradouroResult:
        itens = [
            ResolucaoLogradouroItem(logradouro=logr, score=None) for logr in literal.logradouros
        ]
        return ResolucaoLogradouroResult(
            itens=itens, usou_fuzzy=False, ignorou_filtro_tipo=literal.ignorou_filtro_tipo
        )

    def _fuzzy_permitido(self, query: ResolucaoLogradouroQuery) -> bool:
        return query.modo == "commit" or len(query.nome.strip()) >= FUZZY_MIN_CHARS_SUGESTAO

    def _tentar_fuzzy(self, query: ResolucaoLogradouroQuery) -> ResolucaoLogradouroResult:
        texto = f"{query.tipo} {query.nome}".strip() if query.tipo else query.nome
        resultado = self._fuzzy(LogradouroMatchQuery(texto=texto, limite=query.limite))
        itens = self._itens_do_fuzzy(resultado, query.limite)
        return ResolucaoLogradouroResult(
            itens=itens, usou_fuzzy=True, ignorou_filtro_tipo=resultado.ignorou_filtro_tipo
        )

    def _itens_do_fuzzy(
        self, resultado: LogradouroMatchResult, limite: int
    ) -> list[ResolucaoLogradouroItem]:
        filtro = None if resultado.ignorou_filtro_tipo else self._codigo_do_tipo(resultado)
        itens = [
            ResolucaoLogradouroItem(logradouro=self._to_output(row), score=match.similarity_score)
            for match in resultado.match_nome.matches
            if match.similarity_score >= self._threshold
            for row in self._catalog.linhas_por_nome(match.original_string, filtro)
        ]
        return itens[:limite]

    def _codigo_do_tipo(self, resultado: LogradouroMatchResult) -> str | None:
        melhor_tipo = resultado.match_tipo.best_match if resultado.match_tipo else None
        return self._catalog.codigo_da_variacao(melhor_tipo.original_string) if melhor_tipo else None

    def _to_output(self, row: LogradouroRow) -> LogradouroMatchOutput:
        return LogradouroMatchOutput(
            codlog=row.codlog,
            dv=row.dv,
            tipo_codigo=row.tipo_logradouro,
            nome_logradouro=row.nm_logradouro,
        )
