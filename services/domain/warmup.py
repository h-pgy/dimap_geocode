from services.domain.codlog_match import codlog_catalog
from services.domain.contribuinte_match import contribuinte_catalog
from services.domain.logradouros_match import logradouro_catalog


def aquecer_catalogos() -> None:
    logradouro_catalog.aquecer()
    contribuinte_catalog.aquecer()
    codlog_catalog.aquecer()
