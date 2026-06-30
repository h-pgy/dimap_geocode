import pytest

from services.domain.logradouros_match import (
    LiteralLogradouroQuery,
    LiteralLogradouroResult,
)
from services.domain.logradouros_match.catalog import LogradouroCatalog
from services.domain.logradouros_match.literal_matcher import LiteralLogradouroMatcher
from services.domain.logradouros_match.models import LogradouroRow


# ---------------------------------------------------------------------------
# Catálogo falso injetável (reutiliza o mesmo padrão de test_matcher.py)
# ---------------------------------------------------------------------------


class FakeCatalog(LogradouroCatalog):
    """Catálogo em memória para testes — ignora parquets."""

    def __init__(self, rows: list[LogradouroRow], variacoes: dict[str, str]) -> None:
        self._rows_data = rows
        self._variacoes_data = variacoes

    @property
    def variacoes_tipo(self) -> list[str]:
        return list(self._variacoes_data.keys())

    def codigo_da_variacao(self, variacao: str) -> str | None:
        return self._variacoes_data.get(variacao)

    def linhas_do_tipo(self, codigo: str) -> list[LogradouroRow]:
        return [r for r in self._rows_data if r.cd_tipo_logradouro == codigo]

    def todas_as_linhas(self) -> list[LogradouroRow]:
        return list(self._rows_data)

    def linhas_por_nome(self, nome: str, codigo: str | None) -> list[LogradouroRow]:
        universo = self.linhas_do_tipo(codigo) if codigo else self._rows_data
        return [r for r in universo if r.nm_logradouro == nome]


def _catalog_padrao() -> FakeCatalog:
    rows = [
        LogradouroRow(codlog="000001", dv="0", cd_tipo_logradouro="AV", nm_logradouro="PAULISTA"),
        LogradouroRow(codlog="000002", dv="0", cd_tipo_logradouro="AV", nm_logradouro="BRASIL"),
        LogradouroRow(codlog="000003", dv="0", cd_tipo_logradouro="R", nm_logradouro="DIREITA"),
        LogradouroRow(codlog="000004", dv="0", cd_tipo_logradouro="R", nm_logradouro="AURORA"),
        LogradouroRow(codlog="000007", dv="0", cd_tipo_logradouro="R", nm_logradouro="AURORA"),
        LogradouroRow(codlog="000005", dv="0", cd_tipo_logradouro="AL", nm_logradouro="SANTOS"),
        # prefixos — nomes que começam com "PAUL"
        LogradouroRow(codlog="000006", dv="0", cd_tipo_logradouro="AV", nm_logradouro="PAULINO GUEDES"),
        LogradouroRow(codlog="000008", dv="0", cd_tipo_logradouro="R", nm_logradouro="PAULO AFONSO"),
        # "BRASIL" aparece no meio (não é prefixo) — para testes do fallback substring
        LogradouroRow(codlog="000009", dv="0", cd_tipo_logradouro="R", nm_logradouro="JARDIM BRASIL"),
    ]
    variacoes = {
        "AVENIDA": "AV",
        "AV": "AV",
        "AV.": "AV",
        "RUA": "R",
        "R.": "R",
        "ALAMEDA": "AL",
        "AL": "AL",
    }
    return FakeCatalog(rows=rows, variacoes=variacoes)


def _matcher() -> LiteralLogradouroMatcher:
    return LiteralLogradouroMatcher(catalog=_catalog_padrao())


# ---------------------------------------------------------------------------
# Nome vazio ou em branco → resultado vazio, sem varrer catálogo
# ---------------------------------------------------------------------------


def test_nome_vazio_retorna_lista_vazia() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome=""))
    assert result.logradouros == []


def test_nome_so_espacos_retorna_lista_vazia() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="   "))
    assert result.logradouros == []


def test_nome_vazio_ignorou_false() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome=""))
    assert result.ignorou_filtro_tipo is False


# ---------------------------------------------------------------------------
# Contains sem tipo — substring casa logradouros corretos
# ---------------------------------------------------------------------------


def test_prefixo_casa_logradouro_exato() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="paulista"))
    codlogs = [lg.codlog for lg in result.logradouros]
    assert "000001" in codlogs


def test_prefixo_paul_casa_multiplos() -> None:
    # "PAUL" é prefixo de PAULISTA, PAULINO GUEDES e PAULO AFONSO — todos retornados via prefixo
    result = _matcher()(LiteralLogradouroQuery(nome="paul", limite=10))
    codlogs = {lg.codlog for lg in result.logradouros}
    assert {"000001", "000006", "000008"} == codlogs


def test_sem_tipo_ignorou_false() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="paul"))
    assert result.ignorou_filtro_tipo is False


# ---------------------------------------------------------------------------
# Prefixo vs. substring — comportamento v3
# ---------------------------------------------------------------------------


def test_prefixo_encontrado_exclui_substring() -> None:
    # "BRASIL" é prefixo de BRASIL (000002); JARDIM BRASIL (000009) tem "BRASIL" no meio.
    # Quando o prefixo dá resultado, o substring NÃO é aplicado.
    result = _matcher()(LiteralLogradouroQuery(nome="brasil", limite=10))
    codlogs = {lg.codlog for lg in result.logradouros}
    assert "000002" in codlogs
    assert "000009" not in codlogs


def test_fallback_substring_quando_nenhum_prefixo_casa() -> None:
    # "ISTA" não é prefixo de nenhum logradouro, mas está contido em PAULISTA.
    # O fallback para substring deve encontrá-lo.
    result = _matcher()(LiteralLogradouroQuery(nome="ista", limite=10))
    codlogs = {lg.codlog for lg in result.logradouros}
    assert "000001" in codlogs


# ---------------------------------------------------------------------------
# Contains com tipo — restringe universo antes do filtro por substring
# ---------------------------------------------------------------------------


def test_tipo_av_filtra_universo_para_paul() -> None:
    # Só AVs com PAUL: PAULISTA (000001) e PAULINO GUEDES (000006)
    result = _matcher()(LiteralLogradouroQuery(nome="paul", tipo="av", limite=10))
    codlogs = {lg.codlog for lg in result.logradouros}
    assert codlogs == {"000001", "000006"}


def test_tipo_av_nao_ignorou_quando_ha_resultado() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="paul", tipo="av"))
    assert result.ignorou_filtro_tipo is False


def test_tipo_avenida_variacao_resolve_para_av() -> None:
    # "avenida" deve resolver ao código "AV" via variacoes
    result = _matcher()(LiteralLogradouroQuery(nome="paul", tipo="avenida", limite=10))
    codlogs = {lg.codlog for lg in result.logradouros}
    assert codlogs == {"000001", "000006"}


# ---------------------------------------------------------------------------
# Fallback sem tipo — quando tipo+substring dá vazio
# ---------------------------------------------------------------------------


def test_tipo_rua_com_paulista_da_vazio_e_faz_fallback() -> None:
    # PAULISTA só existe como AV; busca com tipo=rua dá vazia → fallback sem tipo
    result = _matcher()(LiteralLogradouroQuery(nome="paulista", tipo="rua", limite=10))
    codlogs = {lg.codlog for lg in result.logradouros}
    assert "000001" in codlogs


def test_fallback_sem_tipo_seta_ignorou_true() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="paulista", tipo="rua"))
    assert result.ignorou_filtro_tipo is True


# ---------------------------------------------------------------------------
# Tipo desconhecido (não resolve a código) → fallback, ignorou=True
# ---------------------------------------------------------------------------


def test_tipo_invalido_nao_resolve_codigo() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="paulista", tipo="viela"))
    assert result.ignorou_filtro_tipo is True


def test_tipo_invalido_ainda_acha_logradouro_por_substring() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="paulista", tipo="viela", limite=10))
    codlogs = {lg.codlog for lg in result.logradouros}
    assert "000001" in codlogs


# ---------------------------------------------------------------------------
# Limite de sugestões
# ---------------------------------------------------------------------------


def test_limite_trunca_resultado() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="paul", limite=2))
    assert len(result.logradouros) <= 2


def test_limite_um_retorna_no_maximo_um_item() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="paul", limite=1))
    assert len(result.logradouros) == 1


# ---------------------------------------------------------------------------
# Normalização — acento e caixa não impedem o match
# ---------------------------------------------------------------------------


def test_nome_com_acento_casa_normalizado() -> None:
    # "paulísta" → normalize_text → "PAULISTA" → casa com PAULISTA
    result = _matcher()(LiteralLogradouroQuery(nome="paulísta", limite=10))
    codlogs = {lg.codlog for lg in result.logradouros}
    assert "000001" in codlogs


def test_nome_minusculo_casa_normalizado() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="paulista"))
    assert len(result.logradouros) >= 1


def test_tipo_minusculo_resolve_variacao() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="paul", tipo="av", limite=10))
    codlogs = {lg.codlog for lg in result.logradouros}
    assert "000001" in codlogs


# ---------------------------------------------------------------------------
# Homônimos — múltiplos codlogs com mesmo nome
# ---------------------------------------------------------------------------


def test_homonimos_retorna_todos_os_codlogs() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="aurora", limite=10))
    codlogs = {lg.codlog for lg in result.logradouros}
    assert {"000004", "000007"} == codlogs


def test_homonimos_com_tipo_restrito_retorna_dois() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="aurora", tipo="rua", limite=10))
    assert len(result.logradouros) == 2


def test_homonimos_limite_respeita_teto() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="aurora", limite=1))
    assert len(result.logradouros) == 1


# ---------------------------------------------------------------------------
# DTO de saída — campos obrigatórios presentes em cada item
# ---------------------------------------------------------------------------


def test_item_tem_codlog() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="paulista"))
    assert result.logradouros[0].codlog == "000001"


def test_item_tem_tipo_codigo() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="paulista"))
    assert result.logradouros[0].tipo_codigo == "AV"


def test_item_tem_nome_logradouro() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="paulista"))
    assert result.logradouros[0].nome_logradouro == "PAULISTA"


def test_resultado_e_sempre_lista() -> None:
    result = _matcher()(LiteralLogradouroQuery(nome="xyz_inexistente"))
    assert isinstance(result.logradouros, list)
    assert result.logradouros == []


# ---------------------------------------------------------------------------
# Integração com dados reais
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIntegracaoDadosReais:
    """Testes contra os parquets reais em data/. Marcados para eventual separação."""

    def test_paul_sem_tipo_acha_paulista(self) -> None:
        from services.domain.logradouros_match import match_logradouro_literal

        result = match_logradouro_literal(LiteralLogradouroQuery(nome="paul", limite=20))
        nomes = [lg.nome_logradouro for lg in result.logradouros]
        assert any("PAUL" in n for n in nomes)
        assert result.ignorou_filtro_tipo is False

    def test_paul_com_tipo_av_restringe_a_avenidas(self) -> None:
        from services.domain.logradouros_match import match_logradouro_literal

        result = match_logradouro_literal(LiteralLogradouroQuery(nome="paul", tipo="av", limite=20))
        assert all(lg.tipo_codigo == "AV" for lg in result.logradouros)
        assert result.ignorou_filtro_tipo is False

    def test_paulista_com_tipo_rua_retorna_ruas(self) -> None:
        # No dado real há Ruas com "PAULISTA" no nome (ex.: BANDEIRA PAULISTA).
        # O filtro funciona → ignorou=False e todos os resultados são tipo R.
        from services.domain.logradouros_match import match_logradouro_literal

        result = match_logradouro_literal(
            LiteralLogradouroQuery(nome="paulista", tipo="rua", limite=10)
        )
        assert result.ignorou_filtro_tipo is False
        assert all(lg.tipo_codigo == "R" for lg in result.logradouros)

    def test_tipo_inexistente_ignora_filtro(self) -> None:
        # Tipo que não existe nas variações → código não resolve → fallback sem tipo.
        from services.domain.logradouros_match import match_logradouro_literal

        result = match_logradouro_literal(
            LiteralLogradouroQuery(nome="paulista", tipo="viela", limite=10)
        )
        assert result.ignorou_filtro_tipo is True
        assert len(result.logradouros) > 0

    def test_catalogo_compartilhado_mesma_instancia(self) -> None:
        from services.domain.logradouros_match import match_logradouro, match_logradouro_literal

        assert match_logradouro._catalog is match_logradouro_literal._catalog  # type: ignore[attr-defined]
