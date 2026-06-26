import pytest
from pydantic import ValidationError
from unittest.mock import patch

from services.domain.contribuinte_match import ContribuinteMatcher, ContribuinteMatchInput

# ---------------------------------------------------------------------------
# Dados de teste
# ---------------------------------------------------------------------------

_DADOS_FAKE: dict[str, list[object]] = {
    "cd_identificador":        ["ID001",   "ID002",    "ID003",   "ID004"],
    "cd_setor_fiscal":         ["001",     "001",      "001",     "002"],
    "cd_quadra_fiscal":        ["002",     "002",      "003",     "001"],
    "cd_lote":                 ["0001",    "0002",     "0001",    "0001"],
    "cd_digito_sql":           [None,      "01",       None,      "02"],
    "cd_logradouro":           ["10001",   "10001",    "10002",   "20001"],
    "nm_logradouro_completo":  ["AV PAULISTA", "AV PAULISTA", "RUA DIREITA", "RUA IGUATEMI"],
    "cd_numero_porta":         ["100",     "200",      "300",     "400"],
    "tx_complemento_endereco": [None,      "APTO 1",   None,      None],
    "cd_tipo_quadra":          ["U",       "U",        "U",       "U"],
    "cd_tipo_lote":            ["F",       "F",        "F",       "F"],
}


from collections.abc import Generator

@pytest.fixture
def matcher() -> Generator[ContribuinteMatcher, None, None]:
    with patch(
        "services.domain.contribuinte_match.matcher.read_parquet_from_data",
        return_value=_DADOS_FAKE,
    ):
        yield ContribuinteMatcher()


# ---------------------------------------------------------------------------
# Resultados do match — filtragem
# ---------------------------------------------------------------------------


def test_busca_so_setor_retorna_linhas_do_setor(matcher: ContribuinteMatcher) -> None:
    resultado = matcher(ContribuinteMatchInput(setor="001"))
    assert len(resultado) == 3
    assert all(r.setor == "001" for r in resultado)


def test_busca_setor_quadra_filtra_quadra(matcher: ContribuinteMatcher) -> None:
    resultado = matcher(ContribuinteMatchInput(setor="001", quadra="002"))
    assert len(resultado) == 2
    assert all(r.quadra == "002" for r in resultado)


def test_busca_completa_retorna_lote_exato(matcher: ContribuinteMatcher) -> None:
    resultado = matcher(ContribuinteMatchInput(setor="001", quadra="002", lote="0001"))
    assert len(resultado) == 1
    assert resultado[0].id_poligono == "ID001"


def test_limite_aplica_quando_sem_lote(matcher: ContribuinteMatcher) -> None:
    resultado = matcher(ContribuinteMatchInput(setor="001", limite=2))
    assert len(resultado) == 2


def test_setor_inexistente_retorna_lista_vazia(matcher: ContribuinteMatcher) -> None:
    resultado = matcher(ContribuinteMatchInput(setor="999"))
    assert resultado == []


# ---------------------------------------------------------------------------
# Resultados do match — mapeamento de campos
# ---------------------------------------------------------------------------


def test_campos_obrigatorios_mapeados(matcher: ContribuinteMatcher) -> None:
    r = matcher(ContribuinteMatchInput(setor="001", quadra="002", lote="0002"))[0]
    assert r.id_poligono == "ID002"
    assert r.codlog == "10001"
    assert r.logradouro == "AV PAULISTA"
    assert r.numero == "200"
    assert r.tipo_quadra == "U"
    assert r.tipo_lote == "F"


def test_digito_nulo_mapeado_como_none(matcher: ContribuinteMatcher) -> None:
    r = matcher(ContribuinteMatchInput(setor="001", quadra="002", lote="0001"))[0]
    assert r.digito is None


def test_digito_preenchido_mapeado_como_string(matcher: ContribuinteMatcher) -> None:
    r = matcher(ContribuinteMatchInput(setor="001", quadra="002", lote="0002"))[0]
    assert r.digito == "01"


def test_complemento_nulo_mapeado_como_none(matcher: ContribuinteMatcher) -> None:
    r = matcher(ContribuinteMatchInput(setor="001", quadra="002", lote="0001"))[0]
    assert r.complemento is None


def test_complemento_preenchido_mapeado_como_string(matcher: ContribuinteMatcher) -> None:
    r = matcher(ContribuinteMatchInput(setor="001", quadra="002", lote="0002"))[0]
    assert r.complemento == "APTO 1"


# ---------------------------------------------------------------------------
# Validação do contrato de entrada
# ---------------------------------------------------------------------------


def test_rejeita_lote_sem_quadra() -> None:
    with pytest.raises(ValidationError):
        ContribuinteMatchInput(setor="001", lote="0001")


def test_rejeita_setor_com_dois_digitos() -> None:
    with pytest.raises(ValidationError):
        ContribuinteMatchInput(setor="01")


def test_rejeita_quadra_com_quatro_digitos() -> None:
    with pytest.raises(ValidationError):
        ContribuinteMatchInput(setor="001", quadra="0002")


def test_rejeita_lote_com_tres_digitos() -> None:
    with pytest.raises(ValidationError):
        ContribuinteMatchInput(setor="001", quadra="002", lote="001")


def test_rejeita_limite_zero() -> None:
    with pytest.raises(ValidationError):
        ContribuinteMatchInput(setor="001", limite=0)


# ---------------------------------------------------------------------------
# Integração com dados reais
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIntegracaoDadosReais:
    def test_busca_por_setor_retorna_resultados_do_setor(self) -> None:
        from services.domain.contribuinte_match import match_contribuinte

        resultado = match_contribuinte(ContribuinteMatchInput(setor="001", limite=3))
        assert len(resultado) > 0
        assert all(r.setor == "001" for r in resultado)

    def test_busca_completa_retorna_exatamente_um_resultado(self) -> None:
        from services.domain.contribuinte_match import match_contribuinte

        amostra = match_contribuinte(ContribuinteMatchInput(setor="001", quadra="002", limite=1))
        assert len(amostra) == 1
        lote = amostra[0].lote
        resultado = match_contribuinte(
            ContribuinteMatchInput(setor="001", quadra="002", lote=lote)
        )
        assert len(resultado) == 1
        assert resultado[0].lote == lote
