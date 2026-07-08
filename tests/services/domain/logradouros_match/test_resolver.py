import pytest

from services.domain.logradouros_match import ResolucaoLogradouroQuery
from services.domain.logradouros_match.catalog import LogradouroCatalog
from services.domain.logradouros_match.literal_matcher import LiteralLogradouroMatcher
from services.domain.logradouros_match.matcher import LogradouroMatcher
from services.domain.logradouros_match.models import LogradouroRow
from services.domain.logradouros_match.resolver import FUZZY_MIN_CHARS_SUGESTAO, LogradouroResolver


# ---------------------------------------------------------------------------
# Catálogo falso injetável (mesmo padrão de test_matcher.py / test_literal_matcher.py)
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
        return [r for r in self._rows_data if r.tipo_logradouro == codigo]

    def todas_as_linhas(self) -> list[LogradouroRow]:
        return list(self._rows_data)

    def linhas_por_nome(self, nome: str, codigo: str | None) -> list[LogradouroRow]:
        universo = self.linhas_do_tipo(codigo) if codigo else self._rows_data
        return [r for r in universo if r.nm_logradouro == nome]


def _catalog_padrao() -> FakeCatalog:
    rows = [
        # "PALISTA" ~ jaro_winkler ~97% de "PAULISTA" — erro de digitação plausível
        LogradouroRow(codlog="000001", dv="0", tipo_logradouro="AV", nm_logradouro="PAULISTA"),
        LogradouroRow(codlog="000002", dv="0", tipo_logradouro="AV", nm_logradouro="BRASIL"),
        LogradouroRow(codlog="000003", dv="0", tipo_logradouro="R", nm_logradouro="DIREITA"),
    ]
    variacoes = {
        "AVENIDA": "AV",
        "AV": "AV",
        "RUA": "R",
    }
    return FakeCatalog(rows=rows, variacoes=variacoes)


def _resolver(threshold: float = 80.0) -> LogradouroResolver:
    catalog = _catalog_padrao()
    return LogradouroResolver(
        literal=LiteralLogradouroMatcher(catalog=catalog),
        fuzzy=LogradouroMatcher(catalog=catalog),
        catalog=catalog,
        threshold=threshold,
    )


# ---------------------------------------------------------------------------
# Literal com resultado — não roda fuzzy; itens vêm sem score
# ---------------------------------------------------------------------------


def test_literal_com_resultado_nao_usa_fuzzy() -> None:
    result = _resolver()(ResolucaoLogradouroQuery(nome="paulista", tipo="avenida", modo="commit"))
    assert result.usou_fuzzy is False


def test_literal_com_resultado_itens_sem_score() -> None:
    result = _resolver()(ResolucaoLogradouroQuery(nome="paulista", tipo="avenida", modo="commit"))
    assert all(item.score is None for item in result.itens)


def test_literal_com_resultado_devolve_codlog_correto() -> None:
    result = _resolver()(ResolucaoLogradouroQuery(nome="paulista", tipo="avenida", modo="commit"))
    assert result.itens[0].logradouro.codlog == "000001"


def test_literal_propaga_ignorou_filtro_tipo() -> None:
    # PAULISTA só existe como AV; tipo="rua" força o literal a cair no fallback sem tipo
    result = _resolver()(ResolucaoLogradouroQuery(nome="paulista", tipo="rua", modo="commit"))
    assert result.ignorou_filtro_tipo is True


# ---------------------------------------------------------------------------
# Literal vazio + fuzzy acima do threshold — itens com score, usou_fuzzy=True
# ---------------------------------------------------------------------------


def test_literal_vazio_aciona_fuzzy() -> None:
    # "palista" não é prefixo nem substring de "PAULISTA" (falta o "U") — literal fica vazio
    result = _resolver()(ResolucaoLogradouroQuery(nome="palista", tipo="avenida", modo="commit"))
    assert result.usou_fuzzy is True


def test_fuzzy_acima_do_threshold_preenche_score() -> None:
    result = _resolver()(ResolucaoLogradouroQuery(nome="palista", tipo="avenida", modo="commit"))
    assert result.itens[0].score is not None


def test_fuzzy_resolve_logradouro_correto() -> None:
    result = _resolver()(ResolucaoLogradouroQuery(nome="palista", tipo="avenida", modo="commit"))
    assert result.itens[0].logradouro.codlog == "000001"


def test_fuzzy_ignora_filtro_tipo_quando_matcher_sinaliza() -> None:
    # tipo="rua" resolve para "R", mas dentro de R só há "DIREITA" (score baixo para "palista")
    # — o próprio LogradouroMatcher cai no fallback global e sinaliza ignorou_filtro_tipo=True
    result = _resolver()(ResolucaoLogradouroQuery(nome="palista", tipo="rua", modo="commit"))
    assert result.ignorou_filtro_tipo is True
    assert result.itens[0].logradouro.codlog == "000001"


# ---------------------------------------------------------------------------
# Fuzzy abaixo do threshold — nenhum item aceito
# ---------------------------------------------------------------------------


def test_fuzzy_abaixo_do_threshold_devolve_vazio() -> None:
    # threshold 101 é inalcançável (score máximo é 100) — nenhum item passa no corte
    result = _resolver(threshold=101.0)(
        ResolucaoLogradouroQuery(nome="palista", tipo="avenida", modo="commit")
    )
    assert result.itens == []


def test_sem_nenhuma_proximidade_devolve_vazio() -> None:
    # "zzzzzzzzzzz" não tem nenhuma proximidade com o catálogo (score 0 para tudo)
    result = _resolver()(ResolucaoLogradouroQuery(nome="zzzzzzzzzzz", modo="commit"))
    assert result.itens == []


# ---------------------------------------------------------------------------
# Modo sugestão — guarda de tamanho mínimo de nome
# ---------------------------------------------------------------------------


def test_sugestao_nome_curto_nao_aciona_fuzzy() -> None:
    nome_curto = "x" * (FUZZY_MIN_CHARS_SUGESTAO - 1)
    result = _resolver()(ResolucaoLogradouroQuery(nome=nome_curto, modo="sugestao"))
    assert result.usou_fuzzy is False


def test_sugestao_nome_curto_devolve_vazio() -> None:
    nome_curto = "x" * (FUZZY_MIN_CHARS_SUGESTAO - 1)
    result = _resolver()(ResolucaoLogradouroQuery(nome=nome_curto, modo="sugestao"))
    assert result.itens == []


def test_sugestao_nome_no_minimo_aciona_fuzzy() -> None:
    result = _resolver()(
        ResolucaoLogradouroQuery(nome="palista", tipo="avenida", modo="sugestao")
    )
    assert result.usou_fuzzy is True


# ---------------------------------------------------------------------------
# Modo commit — sem guarda de tamanho mínimo
# ---------------------------------------------------------------------------


def test_commit_nome_curto_ainda_aciona_fuzzy() -> None:
    nome_curto = "x" * (FUZZY_MIN_CHARS_SUGESTAO - 1)
    result = _resolver()(ResolucaoLogradouroQuery(nome=nome_curto, modo="commit"))
    assert result.usou_fuzzy is True


# ---------------------------------------------------------------------------
# Top-N do fuzzy — mais de um nome candidato vira mais de um item
# ---------------------------------------------------------------------------


def test_fuzzy_devolve_varios_itens_quando_ha_varios_nomes_proximos() -> None:
    result = _resolver(threshold=0.0)(
        ResolucaoLogradouroQuery(nome="palista", tipo="avenida", limite=5, modo="commit")
    )
    # universo do tipo AV tem PAULISTA e BRASIL — ambos entram com threshold 0
    assert len(result.itens) == 2


def test_fuzzy_respeita_limite() -> None:
    result = _resolver(threshold=0.0)(
        ResolucaoLogradouroQuery(nome="palista", tipo="avenida", limite=1, modo="commit")
    )
    assert len(result.itens) == 1


# ---------------------------------------------------------------------------
# Integração com dados reais
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIntegracaoDadosReais:
    """Testes contra os parquets reais em data/. Marcados para eventual separação."""

    def test_avenida_palista_resolve_por_fuzzy(self) -> None:
        from services.domain.logradouros_match import resolver_logradouro

        result = resolver_logradouro(
            ResolucaoLogradouroQuery(nome="palista", tipo="avenida", modo="commit")
        )
        assert result.usou_fuzzy is True
        assert "15656" in {item.logradouro.codlog for item in result.itens}

    def test_avenida_paulista_literal_nao_usa_fuzzy(self) -> None:
        from services.domain.logradouros_match import resolver_logradouro

        result = resolver_logradouro(
            ResolucaoLogradouroQuery(nome="paulista", tipo="avenida", modo="commit")
        )
        assert result.usou_fuzzy is False
        assert all(item.score is None for item in result.itens)

    def test_sugestao_com_nome_muito_curto_nao_aciona_fuzzy(self) -> None:
        from services.domain.logradouros_match import resolver_logradouro

        # "xyz" (3 chars) não bate literal nem existe em nenhum nome real — fica abaixo do
        # mínimo de sugestão (4 chars), então nem chega a rodar o fuzzy.
        result = resolver_logradouro(
            ResolucaoLogradouroQuery(nome="xyz", tipo=None, modo="sugestao")
        )
        assert result.usou_fuzzy is False

    def test_entrada_sem_match_plausivel_devolve_vazio(self) -> None:
        from services.domain.logradouros_match import resolver_logradouro

        result = resolver_logradouro(
            ResolucaoLogradouroQuery(nome="zzzzzzzzzzzzzzz", modo="commit")
        )
        assert result.itens == []
