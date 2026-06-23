from services.utils.fuzzy_matcher import FuzzyMatchResult, fuzzy_match

from .catalog import LogradouroCatalog
from .models import LogradouroMatch, LogradouroMatchQuery, LogradouroMatchResult

DEFAULT_NAME_SCORE_THRESHOLD = 80.0


class LogradouroMatcher:
    def __init__(
        self,
        catalog: LogradouroCatalog | None = None,
        name_score_threshold: float = DEFAULT_NAME_SCORE_THRESHOLD,
    ) -> None:
        self._catalog = catalog or LogradouroCatalog()
        self._threshold = name_score_threshold

    def __call__(self, query: LogradouroMatchQuery) -> LogradouroMatchResult:
        return self._pipeline(query)

    def _pipeline(self, query: LogradouroMatchQuery) -> LogradouroMatchResult:
        tipo_token, nome_token = self._split(query.texto)
        if tipo_token is None:
            match_nome = self._match_nome_global(nome_token, query.limite)
            return self._build_result(None, match_nome, None, ignorou=False)
        match_tipo = self._match_tipo(tipo_token)
        codigo = self._resolve_codigo(match_tipo)
        match_nome, ignorou = self._match_nome(nome_token, codigo, query.limite)
        return self._build_result(match_tipo, match_nome, codigo, ignorou)

    def _split(self, texto: str) -> tuple[str | None, str]:
        partes = texto.strip().split(" ", 1)
        if len(partes) < 2:
            return None, partes[0] if partes else ""
        return partes[0], partes[1]

    def _match_tipo(self, tipo_token: str) -> FuzzyMatchResult:
        return fuzzy_match(tipo_token, self._catalog.variacoes_tipo, algorithm="levenshtein")

    def _resolve_codigo(self, match_tipo: FuzzyMatchResult) -> str | None:
        melhor = match_tipo.best_match
        return self._catalog.codigo_da_variacao(melhor.original_string) if melhor else None

    def _match_nome(
        self, nome_token: str, codigo: str | None, limite: int
    ) -> tuple[FuzzyMatchResult, bool]:
        choices = [r.nm_logradouro for r in self._catalog.linhas_do_tipo(codigo)] if codigo else []
        if not choices:
            return self._match_nome_global(nome_token, limite), codigo is not None
        resultado = fuzzy_match(nome_token, choices, limit=limite, algorithm="jaro_winkler")
        if resultado.best_match is None or resultado.best_match.similarity_score < self._threshold:
            return self._match_nome_global(nome_token, limite), codigo is not None
        return resultado, False

    def _match_nome_global(self, nome_token: str, limite: int) -> FuzzyMatchResult:
        todos = [r.nm_logradouro for r in self._catalog.todas_as_linhas()]
        return fuzzy_match(nome_token, todos, limit=limite, algorithm="jaro_winkler")

    def _build_result(
        self,
        match_tipo: FuzzyMatchResult | None,
        match_nome: FuzzyMatchResult,
        codigo: str | None,
        ignorou: bool,
    ) -> LogradouroMatchResult:
        melhor = match_nome.best_match
        filtro = None if ignorou else codigo
        rows = self._catalog.linhas_por_nome(melhor.original_string, filtro) if melhor else []
        logradouros = [
            LogradouroMatch(
                codlog=row.codlog,
                tipo_codigo=row.cd_tipo_logradouro,
                nome_logradouro=row.nm_logradouro,
            )
            for row in rows
        ]
        return LogradouroMatchResult(
            match_tipo=match_tipo,
            match_nome=match_nome,
            logradouros=logradouros,
            ignorou_filtro_tipo=ignorou,
        )


match_logradouro = LogradouroMatcher()
