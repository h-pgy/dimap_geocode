from .catalog import ContribuinteCatalog
from .matcher_contribuinte import ContribuinteMatcher
from .matcher_endereco_fiscal import EnderecoFiscalMatcher
from .models import ContribuinteMatchInput, ContribuinteMatchOutput, EnderecoFiscalMatchInput

_catalog = ContribuinteCatalog()
match_contribuinte = ContribuinteMatcher(catalog=_catalog)
match_endereco_fiscal = EnderecoFiscalMatcher(catalog=_catalog)
contribuinte_catalog = _catalog

__all__ = [
    "ContribuinteCatalog",
    "ContribuinteMatcher",
    "EnderecoFiscalMatcher",
    "match_contribuinte",
    "match_endereco_fiscal",
    "contribuinte_catalog",
    "ContribuinteMatchInput",
    "ContribuinteMatchOutput",
    "EnderecoFiscalMatchInput",
]
