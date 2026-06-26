from unittest.mock import patch

import pytest

from services.domain.logradouros_match.catalog import LogradouroCatalog
from services.domain.logradouros_match.models import LogradouroRow


# ---------------------------------------------------------------------------
# Dados sintéticos usados nos testes
# ---------------------------------------------------------------------------


_TIPOS_DATA = {
    "nome_tipo": ["AVENIDA", "AV", "AV.", "RUA", "R.", "ALAMEDA"],
    "cd_tipo_logradouro": ["AV", "AV", "AV", "R", "R", "AL"],
}

_NOMES_DATA = {
    "codlog": ["000001", "000002", "000003", "000004", "000005"],
    "cd_tipo_logradouro": ["AV", "AV", "R", "R", "AL"],
    "nm_logradouro": ["PAULISTA", "BRASIL", "PAULISTA", "DIREITA", "SANTOS"],
}


def _catalog_com_dados_sinteticos() -> LogradouroCatalog:
    def fake_read(filename: str) -> dict[str, list[object]]:
        if "tipos" in filename:
            return {k: list(v) for k, v in _TIPOS_DATA.items()}  # type: ignore[arg-type]
        return {k: list(v) for k, v in _NOMES_DATA.items()}  # type: ignore[arg-type]

    with patch("services.domain.logradouros_match.catalog.read_parquet_from_data", side_effect=fake_read):
        c = LogradouroCatalog()
        # força a carga das três propriedades dentro do patch
        _ = c.variacoes_tipo
        _ = c.todas_as_linhas()
        _ = c.linhas_do_tipo("AV")
    return c


# ---------------------------------------------------------------------------
# variacoes_tipo — lista de choices para o match de tipo
# ---------------------------------------------------------------------------


def test_variacoes_tipo_retorna_todas_as_chaves() -> None:
    c = _catalog_com_dados_sinteticos()
    assert set(c.variacoes_tipo) == {"AVENIDA", "AV", "AV.", "RUA", "R.", "ALAMEDA"}


def test_variacoes_tipo_retorna_lista() -> None:
    c = _catalog_com_dados_sinteticos()
    assert isinstance(c.variacoes_tipo, list)


# ---------------------------------------------------------------------------
# codigo_da_variacao — resolve variação → código
# ---------------------------------------------------------------------------


def test_codigo_da_variacao_resolve_abreviacao() -> None:
    c = _catalog_com_dados_sinteticos()
    assert c.codigo_da_variacao("AV") == "AV"


def test_codigo_da_variacao_resolve_nome_por_extenso() -> None:
    c = _catalog_com_dados_sinteticos()
    assert c.codigo_da_variacao("AVENIDA") == "AV"


def test_codigo_da_variacao_retorna_none_para_variacao_inexistente() -> None:
    c = _catalog_com_dados_sinteticos()
    assert c.codigo_da_variacao("XXXXXX") is None


# ---------------------------------------------------------------------------
# linhas_do_tipo — filtra rows pelo código do tipo
# ---------------------------------------------------------------------------


def test_linhas_do_tipo_retorna_apenas_linhas_do_codigo() -> None:
    c = _catalog_com_dados_sinteticos()
    linhas = c.linhas_do_tipo("AV")
    assert all(r.cd_tipo_logradouro == "AV" for r in linhas)
    assert len(linhas) == 2


def test_linhas_do_tipo_retorna_lista_vazia_para_codigo_inexistente() -> None:
    c = _catalog_com_dados_sinteticos()
    assert c.linhas_do_tipo("ZZ") == []


# ---------------------------------------------------------------------------
# todas_as_linhas — retorna todos os rows
# ---------------------------------------------------------------------------


def test_todas_as_linhas_retorna_quantidade_correta() -> None:
    c = _catalog_com_dados_sinteticos()
    assert len(c.todas_as_linhas()) == 5


def test_todas_as_linhas_retorna_logradouro_rows() -> None:
    c = _catalog_com_dados_sinteticos()
    for row in c.todas_as_linhas():
        assert isinstance(row, LogradouroRow)


# ---------------------------------------------------------------------------
# linhas_por_nome — recupera homônimos
# ---------------------------------------------------------------------------


def test_linhas_por_nome_com_filtro_de_tipo() -> None:
    c = _catalog_com_dados_sinteticos()
    # PAULISTA existe em AV (codlog 000001) e R (codlog 000003); filtro em AV retorna só 000001
    linhas = c.linhas_por_nome("PAULISTA", "AV")
    assert len(linhas) == 1
    assert linhas[0].codlog == "000001"


def test_linhas_por_nome_sem_filtro_retorna_homonimos() -> None:
    c = _catalog_com_dados_sinteticos()
    # sem filtro de tipo, PAULISTA aparece nos dois tipos
    linhas = c.linhas_por_nome("PAULISTA", None)
    codlogs = {r.codlog for r in linhas}
    assert codlogs == {"000001", "000003"}


def test_linhas_por_nome_retorna_vazio_quando_nao_encontra() -> None:
    c = _catalog_com_dados_sinteticos()
    assert c.linhas_por_nome("INEXISTENTE", None) == []


# ---------------------------------------------------------------------------
# Cache — a propriedade não é recomputada enquanto o TTL não expira
# ---------------------------------------------------------------------------


def test_rows_cached_nao_recarrega_dentro_do_ttl() -> None:
    chamadas: list[str] = []

    def fake_read(filename: str) -> dict[str, list[object]]:
        chamadas.append(filename)
        if "tipos" in filename:
            return {k: list(v) for k, v in _TIPOS_DATA.items()}  # type: ignore[arg-type]
        return {k: list(v) for k, v in _NOMES_DATA.items()}  # type: ignore[arg-type]

    with patch("services.domain.logradouros_match.catalog.read_parquet_from_data", side_effect=fake_read):
        c = LogradouroCatalog()
        _ = c.todas_as_linhas()
        _ = c.todas_as_linhas()

    nomes_calls = [f for f in chamadas if "nomes" in f]
    assert len(nomes_calls) == 1
