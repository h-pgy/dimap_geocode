"""
Testes do EnderecoFiscalMatcher (SPEC 010): match por codlog (exato, contra a coluna
`codlog5`) + número de porta (prefixo, contra a coluna cacheada `chave_numero_porta`).
O matcher NÃO normaliza — recebe `numero_padronizado` já pronto.
"""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from services.domain.contribuinte_match import (
    ContribuinteCatalog,
    EnderecoFiscalMatcher,
    EnderecoFiscalMatchInput,
)

# cd_logradouro tem 6 dígitos (codlog+DV); cd_numero_porta traz alfanumérico, "sem número"
# gravado como "SEM NÚMERO" e nulos.
_DADOS_FAKE: dict[str, list[object]] = {
    "cd_identificador":        ["ID001",       "ID002",       "ID003",       "ID004",  "ID005"],
    "cd_setor_fiscal":         ["001",         "001",         "001",         "002",    "001"],
    "cd_quadra_fiscal":        ["002",         "002",         "003",         "001",    "002"],
    "cd_lote":                 ["0001",        "0002",        "0003",        "0001",   "0004"],
    "cd_digito_sql":           [None,          "01",          None,          "02",     None],
    "cd_logradouro":           ["048046",      "048046",      "048046",      "099999", "048046"],
    "nm_logradouro_completo":  ["AV PAULISTA", "AV PAULISTA", "AV PAULISTA", "RUA X",  "AV PAULISTA"],
    "cd_numero_porta":         ["100",         "10A",         "SEM NÚMERO",  "100",    None],
    "tx_complemento_endereco": [None,          "APTO 1",      None,          None,     None],
    "cd_tipo_quadra":          ["U",           "U",           "U",           "U",      "U"],
    "cd_tipo_lote":            ["F",           "F",           "F",           "F",      "F"],
    "cd_condominio":           ["00",          "07",          "00",          "00",     "00"],
}


@pytest.fixture
def catalog() -> Generator[ContribuinteCatalog, None, None]:
    with patch(
        "services.domain.contribuinte_match.catalog.read_parquet_from_data",
        return_value=_DADOS_FAKE,
    ):
        yield ContribuinteCatalog()


@pytest.fixture
def matcher(catalog: ContribuinteCatalog) -> EnderecoFiscalMatcher:
    return EnderecoFiscalMatcher(catalog=catalog)


def _ids(matcher: EnderecoFiscalMatcher, **kwargs: object) -> list[str]:
    return [r.id_poligono for r in matcher(EnderecoFiscalMatchInput(**kwargs))]  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Colunas preparadas no catalog (codlog5 + chave_numero_porta canonizada)
# ---------------------------------------------------------------------------


class TestColunasDoCatalog:
    def test_codlog5_trunca_para_5_digitos(self, catalog: ContribuinteCatalog) -> None:
        df = catalog.enderecos_fiscais_com_chave
        assert list(df["codlog5"]) == ["04804", "04804", "04804", "09999", "04804"]

    def test_chave_numero_porta_ja_sai_canonizada(self, catalog: ContribuinteCatalog) -> None:
        # "SEM NÚMERO" vira o token canônico "SN"; nulo vira "" (fillna antes da chave)
        df = catalog.enderecos_fiscais_com_chave
        assert list(df["chave_numero_porta"]) == ["100", "10A", "SN", "100", ""]

    def test_preserva_cd_numero_porta_original(self, catalog: ContribuinteCatalog) -> None:
        # a coluna original é preservada (a chave é ACRESCENTADA, não sobrescreve)
        df = catalog.enderecos_fiscais_com_chave
        assert df.loc[df["cd_identificador"] == "ID003", "cd_numero_porta"].iloc[0] == "SEM NÚMERO"

    def test_is_condominio_true_sse_cd_condominio_diferente_de_zero(
        self, catalog: ContribuinteCatalog
    ) -> None:
        # cd_condominio = ["00", "07", "00", "00", "00"]  →  só ID002 é condomínio
        df = catalog.enderecos_fiscais
        assert list(df["is_condominio"]) == [False, True, False, False, False]

    def test_is_condominio_propagada_para_df_com_chave(
        self, catalog: ContribuinteCatalog
    ) -> None:
        # enderecos_fiscais_com_chave é um .copy() — herda a coluna is_condominio
        df = catalog.enderecos_fiscais_com_chave
        assert df.loc[df["cd_identificador"] == "ID002", "is_condominio"].iloc[0]


# ---------------------------------------------------------------------------
# Match por prefixo de número + codlog exato
# ---------------------------------------------------------------------------


class TestMatch:
    def test_prefixo_pega_100_e_10a(self, matcher: EnderecoFiscalMatcher) -> None:
        # numero_padronizado="1" casa "100" e "10A" por prefixo (mesmo codlog)
        assert _ids(matcher, codlogs=["04804"], numero_padronizado="1") == ["ID001", "ID002"]

    def test_numero_exato(self, matcher: EnderecoFiscalMatcher) -> None:
        assert _ids(matcher, codlogs=["04804"], numero_padronizado="100") == ["ID001"]

    def test_sem_numero_casa_imovel_sem_numero(self, matcher: EnderecoFiscalMatcher) -> None:
        # digitar "s/n" (chave "SN") acha o imóvel gravado como "SEM NÚMERO"
        assert _ids(matcher, codlogs=["04804"], numero_padronizado="SN") == ["ID003"]

    def test_codlog_fora_da_lista_nao_vaza(self, matcher: EnderecoFiscalMatcher) -> None:
        assert _ids(matcher, codlogs=["77777"], numero_padronizado="100") == []

    def test_isin_com_varios_codlogs(self, matcher: EnderecoFiscalMatcher) -> None:
        # a lista de codlogs usa isin: casa nos dois codlogs distintos
        assert _ids(matcher, codlogs=["04804", "09999"], numero_padronizado="100") == [
            "ID001",
            "ID004",
        ]

    def test_limite_respeitado(self, matcher: EnderecoFiscalMatcher) -> None:
        assert _ids(matcher, codlogs=["04804"], numero_padronizado="1", limite=1) == ["ID001"]

    def test_linha_com_porta_nula_nunca_casa(self, matcher: EnderecoFiscalMatcher) -> None:
        # ID005 tem chave "" — nenhum numero_padronizado (min_length=1) o alcança por prefixo
        todos = _ids(matcher, codlogs=["04804"], numero_padronizado="1", limite=10)
        assert "ID005" not in todos


# ---------------------------------------------------------------------------
# Número exibido = original da base (não a chave normalizada)
# ---------------------------------------------------------------------------


class TestNumeroExibido:
    def test_numero_vem_original_da_base(self, matcher: EnderecoFiscalMatcher) -> None:
        r = matcher(EnderecoFiscalMatchInput(codlogs=["04804"], numero_padronizado="SN"))[0]
        assert r.numero == "SEM NÚMERO"  # original, não "SN"
        assert r.codlog == "048046"  # cd_logradouro de 6 dígitos, como está no output

    def test_alfanumerico_exibido_como_gravado(self, matcher: EnderecoFiscalMatcher) -> None:
        r = matcher(EnderecoFiscalMatchInput(codlogs=["04804"], numero_padronizado="10A"))[0]
        assert r.numero == "10A"


# ---------------------------------------------------------------------------
# Contrato de entrada
# ---------------------------------------------------------------------------


class TestContratoEntrada:
    def test_rejeita_lista_de_codlogs_vazia(self) -> None:
        with pytest.raises(ValidationError):
            EnderecoFiscalMatchInput(codlogs=[], numero_padronizado="100")

    def test_rejeita_numero_padronizado_vazio(self) -> None:
        with pytest.raises(ValidationError):
            EnderecoFiscalMatchInput(codlogs=["04804"], numero_padronizado="")

    def test_rejeita_limite_zero(self) -> None:
        with pytest.raises(ValidationError):
            EnderecoFiscalMatchInput(codlogs=["04804"], numero_padronizado="100", limite=0)
