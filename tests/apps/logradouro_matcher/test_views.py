import pandas as pd
import pytest
from bs4 import BeautifulSoup

import apps.logradouro_matcher.views as views
from apps.search.secoes import SecaoResultado
from services.domain.codlog_match import CodlogMatcher
from services.domain.codlog_match.catalog import CodlogCatalog
from services.domain.logradouros_match.catalog import (
    NOMES_LOGRADOUROS_FILE,
    TIPOS_CACHE_FILE,
    TITULOS_CACHE_FILE,
    LogradouroCatalog,
)
from services.domain.logradouros_match.literal_matcher import LiteralLogradouroMatcher
from services.domain.logradouros_match.matcher import LogradouroMatcher
from services.domain.logradouros_match.resolver import LogradouroResolver
from services.domain.roteamento_busca import CodlogParse, LogradouroParse
from services.utils.io import write_parquet_to_data

LUIS_ANTONIO = "AV BRIG LUIS ANTONIO"

# ---------------------------------------------------------------------------
# Catálogos com a linha da AV BRIG LUIS ANTONIO
# ---------------------------------------------------------------------------

_NOMES: dict[str, list[object]] = {
    "codlog": ["121657"],
    "cd_tipo_logradouro": ["AV"],
    "cd_titulo_logradouro": ["BRIG"],
    "tx_preposicao_logradouro": [None],
    "nm_logradouro": ["LUIS ANTONIO"],
}


class FakeCodlogCatalog(CodlogCatalog):
    """Subclasse escapa do singleton (o bypass do __new__ é só para a classe base)."""

    def __init__(self, dados: dict[str, list[object]]) -> None:
        self._dados = dados

    @property
    def logradouros(self) -> pd.DataFrame:
        df = pd.DataFrame(self._dados)
        df["_codlog5"] = df["codlog"].str[:5]
        return df


def _instalar_catalogos(monkeypatch: pytest.MonkeyPatch) -> None:
    # Parquets no diretório temporário (fixture _isolar_diretorio_de_dados do conftest), lidos
    # pelo catálogo de verdade — nasce frio pelo reset do singleton no conftest.
    write_parquet_to_data(_NOMES, NOMES_LOGRADOUROS_FILE)
    write_parquet_to_data({"nome_tipo": ["AV"], "cd_tipo_logradouro": ["AV"]}, TIPOS_CACHE_FILE)
    write_parquet_to_data(
        {"cd_titulo_logradouro": ["BRIG"], "nome_titulo": ["BRIGADEIRO"]},
        TITULOS_CACHE_FILE,
    )
    catalogo = LogradouroCatalog()
    resolver = LogradouroResolver(
        literal=LiteralLogradouroMatcher(catalog=catalogo),
        fuzzy=LogradouroMatcher(catalog=catalogo),
        catalog=catalogo,
    )
    monkeypatch.setattr(views, "match_codlog", CodlogMatcher(catalog=FakeCodlogCatalog(_NOMES)))
    monkeypatch.setattr(views, "resolver_logradouro", resolver)


def _nome_na_sugestao(secao: SecaoResultado | None) -> str:
    assert secao is not None
    nome = BeautifulSoup(secao.html, "html.parser").select_one("li.suggestion-item .font-medium")
    assert nome is not None
    return nome.get_text(strip=True)


# ---------------------------------------------------------------------------
# Sugestões de logradouro: o nome completo, o mesmo da gaveta
# ---------------------------------------------------------------------------


def test_sugestoes_mostram_o_nome_completo_do_logradouro(monkeypatch: pytest.MonkeyPatch) -> None:
    _instalar_catalogos(monkeypatch)

    por_codlog = views.secao_codlog(CodlogParse(codlog="12165", digito_verificador="7"))
    por_nome = views.secao_logradouro(LogradouroParse(tipo_logradouro="av", nome="luis antonio"))

    assert _nome_na_sugestao(por_codlog) == LUIS_ANTONIO
    assert _nome_na_sugestao(por_nome) == LUIS_ANTONIO
