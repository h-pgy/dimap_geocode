import pytest

from services.domain.logradouros_match import LogradouroMatch, LogradouroMatchQuery, LogradouroMatchResult
from services.domain.logradouros_match.catalog import LogradouroCatalog
from services.domain.logradouros_match.matcher import DEFAULT_NAME_SCORE_THRESHOLD, LogradouroMatcher
from services.domain.logradouros_match.models import LogradouroRow


# ---------------------------------------------------------------------------
# Catálogo falso injetável
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
        LogradouroRow(codlog="000001", cd_tipo_logradouro="AV", nm_logradouro="PAULISTA"),
        LogradouroRow(codlog="000002", cd_tipo_logradouro="AV", nm_logradouro="BRASIL"),
        LogradouroRow(codlog="000003", cd_tipo_logradouro="R", nm_logradouro="DIREITA"),
        # homônimos: AURORA com dois codlogs dentro do mesmo tipo R
        LogradouroRow(codlog="000004", cd_tipo_logradouro="R", nm_logradouro="AURORA"),
        LogradouroRow(codlog="000007", cd_tipo_logradouro="R", nm_logradouro="AURORA"),
        LogradouroRow(codlog="000005", cd_tipo_logradouro="AL", nm_logradouro="SANTOS"),
    ]
    variacoes = {
        "AVENIDA": "AV",
        "AV": "AV",
        "AV.": "AV",
        "RUA": "R",
        "R.": "R",
        "ALAMEDA": "AL",
    }
    return FakeCatalog(rows=rows, variacoes=variacoes)


def _matcher(threshold: float = DEFAULT_NAME_SCORE_THRESHOLD) -> LogradouroMatcher:
    return LogradouroMatcher(catalog=_catalog_padrao(), name_score_threshold=threshold)


# ---------------------------------------------------------------------------
# _split — quebra o texto no primeiro espaço
# ---------------------------------------------------------------------------


def test_split_com_espaco_retorna_tipo_e_nome() -> None:
    m = _matcher()
    tipo, nome = m._split("avenida paulista")
    assert tipo == "avenida"
    assert nome == "paulista"


def test_split_com_multiplos_espacos_preserva_nome_completo() -> None:
    m = _matcher()
    tipo, nome = m._split("rua monte alegre")
    assert tipo == "rua"
    assert nome == "monte alegre"


def test_split_sem_espaco_retorna_none_e_nome() -> None:
    m = _matcher()
    tipo, nome = m._split("paulista")
    assert tipo is None
    assert nome == "paulista"


def test_split_string_vazia_retorna_none_e_string_vazia() -> None:
    m = _matcher()
    tipo, nome = m._split("")
    assert tipo is None
    assert nome == ""


def test_split_so_espacos_retorna_none_e_string_vazia() -> None:
    m = _matcher()
    tipo, nome = m._split("   ")
    assert tipo is None
    assert nome == ""


# ---------------------------------------------------------------------------
# Pipeline com tipo — caminho normal
# ---------------------------------------------------------------------------


def test_pipeline_com_tipo_preenche_match_tipo() -> None:
    result = _matcher()(LogradouroMatchQuery(texto="avenida paulista"))
    assert result.match_tipo is not None


def test_pipeline_resolve_av_paulista() -> None:
    result = _matcher()(LogradouroMatchQuery(texto="avenida paulista"))
    assert result.logradouros[0].codlog == "000001"
    assert result.logradouros[0].tipo_codigo == "AV"


def test_pipeline_sem_rebusca_quando_score_alto() -> None:
    result = _matcher()(LogradouroMatchQuery(texto="avenida paulista"))
    assert result.ignorou_filtro_tipo is False


# ---------------------------------------------------------------------------
# Pipeline com tipo — rebusca por threshold baixo
# ---------------------------------------------------------------------------


def test_pipeline_dispara_rebusca_quando_score_abaixo_do_threshold() -> None:
    # threshold 100 força rebusca sempre (nenhum match é 100%)
    result = _matcher(threshold=100.0)(LogradouroMatchQuery(texto="rua paulista"))
    assert result.ignorou_filtro_tipo is True


def test_rebusca_encontra_resultado_fora_do_tipo_original() -> None:
    # "rua paulista" com threshold 100 → rebusca em todos → acha AV PAULISTA
    result = _matcher(threshold=100.0)(LogradouroMatchQuery(texto="rua paulista"))
    assert result.logradouros[0].codlog == "000001"
    assert result.logradouros[0].tipo_codigo == "AV"


# ---------------------------------------------------------------------------
# Fast-forward — sem tipo informado
# ---------------------------------------------------------------------------


def test_fast_forward_match_tipo_e_none() -> None:
    result = _matcher()(LogradouroMatchQuery(texto="paulista"))
    assert result.match_tipo is None


def test_fast_forward_ignorou_filtro_tipo_e_false() -> None:
    result = _matcher()(LogradouroMatchQuery(texto="paulista"))
    assert result.ignorou_filtro_tipo is False


def test_fast_forward_encontra_logradouro_correto() -> None:
    result = _matcher()(LogradouroMatchQuery(texto="paulista"))
    assert result.logradouros[0].codlog == "000001"


# ---------------------------------------------------------------------------
# Homônimos — mesmo nome, tipos/codlogs diferentes
# ---------------------------------------------------------------------------


def test_homonimos_resultado_multiplo_true() -> None:
    # AURORA tem dois codlogs dentro de R (000004 e 000007)
    result = _matcher()(LogradouroMatchQuery(texto="rua aurora"))
    assert result.resultado_multiplo is True


def test_homonimos_lista_tem_dois_itens() -> None:
    result = _matcher()(LogradouroMatchQuery(texto="rua aurora"))
    assert len(result.logradouros) == 2


def test_homonimos_codlogs_distintos() -> None:
    result = _matcher()(LogradouroMatchQuery(texto="rua aurora"))
    codlogs = {lg.codlog for lg in result.logradouros}
    assert codlogs == {"000004", "000007"}


# ---------------------------------------------------------------------------
# Resultado único — lista de um item
# ---------------------------------------------------------------------------


def test_resultado_unico_resultado_multiplo_false() -> None:
    result = _matcher()(LogradouroMatchQuery(texto="avenida paulista"))
    assert result.resultado_multiplo is False


def test_resultado_unico_lista_tem_um_item() -> None:
    result = _matcher()(LogradouroMatchQuery(texto="avenida paulista"))
    assert len(result.logradouros) == 1


# ---------------------------------------------------------------------------
# Rastreabilidade — match_tipo e match_nome preservados
# ---------------------------------------------------------------------------


def test_match_tipo_preservado_no_resultado() -> None:
    result = _matcher()(LogradouroMatchQuery(texto="avenida paulista"))
    assert result.match_tipo is not None
    assert result.match_tipo.original_query == "avenida"


def test_match_nome_preservado_no_resultado() -> None:
    result = _matcher()(LogradouroMatchQuery(texto="avenida paulista"))
    assert result.match_nome.original_query == "paulista"


def test_nome_logradouro_property_bate_com_best_match() -> None:
    result = _matcher()(LogradouroMatchQuery(texto="avenida paulista"))
    assert result.nome_logradouro == result.match_nome.best_match.original_string  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Tipo reportado vem da linha casada (não do token digitado)
# ---------------------------------------------------------------------------


def test_tipo_codigo_no_item_vem_da_linha_casada() -> None:
    # "av paulista" → tipo do item é o cd_tipo_logradouro real da linha
    result = _matcher()(LogradouroMatchQuery(texto="avenida paulista"))
    assert result.logradouros[0].tipo_codigo == "AV"


# ---------------------------------------------------------------------------
# Integração com dados reais — casos da spec
# ---------------------------------------------------------------------------


class TestIntegracaoDadosReais:
    """Testes contra os parquets reais em data/. Marcados para eventual separação."""

    def test_av_paulista_codlog_156566(self) -> None:
        from services.domain.logradouros_match import match_logradouro

        result = match_logradouro(LogradouroMatchQuery(texto="avenida paulista"))
        assert "156566" in result.codlogs

    def test_av_paulista_tipo_av(self) -> None:
        from services.domain.logradouros_match import match_logradouro

        result = match_logradouro(LogradouroMatchQuery(texto="avenida paulista"))
        assert result.logradouros[0].tipo_codigo == "AV"

    def test_av_paulista_nao_ignorou_filtro(self) -> None:
        from services.domain.logradouros_match import match_logradouro

        result = match_logradouro(LogradouroMatchQuery(texto="avenida paulista"))
        assert result.ignorou_filtro_tipo is False

    def test_fast_forward_paulista_encontra_av(self) -> None:
        from services.domain.logradouros_match import match_logradouro

        result = match_logradouro(LogradouroMatchQuery(texto="paulista"))
        assert result.match_tipo is None
        assert result.ignorou_filtro_tipo is False
        assert "156566" in result.codlogs

    def test_typo_no_tipo_avnda_resolve_av(self) -> None:
        from services.domain.logradouros_match import match_logradouro

        result = match_logradouro(LogradouroMatchQuery(texto="avnda paulista"))
        assert result.match_tipo is not None
        assert "156566" in result.codlogs

    def test_rua_abaete_homonimos(self) -> None:
        from services.domain.logradouros_match import match_logradouro

        result = match_logradouro(LogradouroMatchQuery(texto="rua abaete"))
        assert result.resultado_multiplo is True
        assert len(result.logradouros) >= 2
