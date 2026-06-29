from .catalog import LogradouroCatalog
from .literal_matcher import LiteralLogradouroMatcher
from .matcher import LogradouroMatcher
from .models import (
    LiteralLogradouroQuery,
    LiteralLogradouroResult,
    LogradouroMatch,
    LogradouroMatchQuery,
    LogradouroMatchResult,
)

_catalog = LogradouroCatalog()
match_logradouro = LogradouroMatcher(catalog=_catalog)
match_logradouro_literal = LiteralLogradouroMatcher(catalog=_catalog)

__all__ = [
    "match_logradouro",
    "match_logradouro_literal",
    "LogradouroMatch",
    "LogradouroMatchQuery",
    "LogradouroMatchResult",
    "LiteralLogradouroQuery",
    "LiteralLogradouroResult",
]
