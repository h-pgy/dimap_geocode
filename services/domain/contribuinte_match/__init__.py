from .catalog import ContribuinteCatalog
from .matcher import ContribuinteMatcher
from .models import ContribuinteMatchInput, ContribuinteMatchOutput

_catalog = ContribuinteCatalog()
match_contribuinte = ContribuinteMatcher(catalog=_catalog)
contribuinte_catalog = _catalog

__all__ = [
    "ContribuinteCatalog",
    "ContribuinteMatcher",
    "match_contribuinte",
    "contribuinte_catalog",
    "ContribuinteMatchInput",
    "ContribuinteMatchOutput",
]
