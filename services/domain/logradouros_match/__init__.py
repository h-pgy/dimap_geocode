from .catalog import LogradouroCatalog
from .literal_matcher import LiteralLogradouroMatcher
from .matcher import LogradouroMatcher
from .models import (
    LiteralLogradouroQuery,
    LiteralLogradouroResult,
    LogradouroMatchOutput,
    LogradouroMatchQuery,
    LogradouroMatchResult,
    ResolucaoLogradouroItem,
    ResolucaoLogradouroQuery,
    ResolucaoLogradouroResult,
)
from .resolver import LogradouroResolver

_catalog = LogradouroCatalog()
match_logradouro = LogradouroMatcher(catalog=_catalog)
match_logradouro_literal = LiteralLogradouroMatcher(catalog=_catalog)
logradouro_catalog = _catalog
resolver_logradouro = LogradouroResolver(
    literal=match_logradouro_literal,
    fuzzy=match_logradouro,
    catalog=_catalog,
)

__all__ = [
    "match_logradouro",
    "match_logradouro_literal",
    "resolver_logradouro",
    "logradouro_catalog",
    "LogradouroMatchOutput",
    "LogradouroMatchQuery",
    "LogradouroMatchResult",
    "LiteralLogradouroQuery",
    "LiteralLogradouroResult",
    "ResolucaoLogradouroQuery",
    "ResolucaoLogradouroItem",
    "ResolucaoLogradouroResult",
]
