from collections.abc import Generator

import pytest
from pydantic import ValidationError
from unittest.mock import patch

from services.domain.codlog_match import CodlogMatcher, CodlogMatchInput

# ---------------------------------------------------------------------------
# Dados de teste
# ---------------------------------------------------------------------------

_DADOS_FAKE: dict[str, list[object]] = {
    "codlog": ["000011", "000029", "000103", "001005", "999999"],
    "cd_tipo_logradouro": ["AV", "RUA", "AV", "PC", "RUA"],
    "nm_logradouro": ["PAULISTA", "DIREITA", "FARIA LIMA", "DA SE", "XV DE NOVEMBRO"],
}


@pytest.fixture
def matcher() -> Generator[CodlogMatcher, None, None]:
    with patch(
        "services.domain.codlog_match.matcher.read_parquet_from_data",
        return_value=_DADOS_FAKE,
    ):
        yield CodlogMatcher()


# ---------------------------------------------------------------------------
# Filtragem — prefixo (startswith)
# ---------------------------------------------------------------------------


def test_prefixo_1_digito_retorna_matches(matcher: CodlogMatcher) -> None:
    resultado = matcher(CodlogMatchInput(input_codlog="0"))
    assert len(resultado) == 4
    assert all(r.codlog.startswith("0") for r in resultado)


def test_prefixo_4_digitos_filtra_corretamente(matcher: CodlogMatcher) -> None:
    resultado = matcher(CodlogMatchInput(input_codlog="0000"))
    assert len(resultado) == 2
    assert all(r.codlog.startswith("0000") for r in resultado)


def test_prefixo_sem_match_retorna_lista_vazia(matcher: CodlogMatcher) -> None:
    resultado = matcher(CodlogMatchInput(input_codlog="888"))
    assert resultado == []


# ---------------------------------------------------------------------------
# Filtragem — igualdade exata (5 dígitos)
# ---------------------------------------------------------------------------


def test_5_digitos_retorna_match_exato(matcher: CodlogMatcher) -> None:
    resultado = matcher(CodlogMatchInput(input_codlog="00001"))
    assert len(resultado) == 1
    assert resultado[0].codlog == "00001"


def test_5_digitos_sem_match_retorna_lista_vazia(matcher: CodlogMatcher) -> None:
    resultado = matcher(CodlogMatchInput(input_codlog="88888"))
    assert resultado == []


# ---------------------------------------------------------------------------
# Limite
# ---------------------------------------------------------------------------


def test_limite_e_respeitado(matcher: CodlogMatcher) -> None:
    resultado = matcher(CodlogMatchInput(input_codlog="0", limite=2))
    assert len(resultado) == 2


# ---------------------------------------------------------------------------
# Mapeamento de campos
# ---------------------------------------------------------------------------


def test_codlog_saida_tem_5_digitos(matcher: CodlogMatcher) -> None:
    resultado = matcher(CodlogMatchInput(input_codlog="00001"))
    assert resultado[0].codlog == "00001"
    assert len(resultado[0].codlog) == 5


def test_dv_saida_tem_1_digito(matcher: CodlogMatcher) -> None:
    resultado = matcher(CodlogMatchInput(input_codlog="00001"))
    assert resultado[0].dv == "1"
    assert len(resultado[0].dv) == 1


def test_campos_tipo_e_nome_mapeados(matcher: CodlogMatcher) -> None:
    resultado = matcher(CodlogMatchInput(input_codlog="00001"))
    assert resultado[0].tipo_logradouro == "AV"
    assert resultado[0].nome_logradouro == "PAULISTA"


def test_nome_completo_concatena_tipo_e_nome(matcher: CodlogMatcher) -> None:
    resultado = matcher(CodlogMatchInput(input_codlog="00001"))
    assert resultado[0].nome_completo == "AV PAULISTA"


# ---------------------------------------------------------------------------
# Validação do contrato de entrada
# ---------------------------------------------------------------------------


def test_rejeita_codlog_com_6_digitos() -> None:
    with pytest.raises(ValidationError):
        CodlogMatchInput(input_codlog="123456")


def test_rejeita_codlog_vazio() -> None:
    with pytest.raises(ValidationError):
        CodlogMatchInput(input_codlog="")


def test_rejeita_codlog_nao_numerico() -> None:
    with pytest.raises(ValidationError):
        CodlogMatchInput(input_codlog="12A45")


def test_rejeita_dv_com_2_digitos() -> None:
    with pytest.raises(ValidationError):
        CodlogMatchInput(input_codlog="00001", digito_verificador="12")


def test_rejeita_dv_nao_numerico() -> None:
    with pytest.raises(ValidationError):
        CodlogMatchInput(input_codlog="00001", digito_verificador="A")


def test_aceita_dv_nulo() -> None:
    payload = CodlogMatchInput(input_codlog="00001")
    assert payload.digito_verificador is None


def test_rejeita_limite_zero() -> None:
    with pytest.raises(ValidationError):
        CodlogMatchInput(input_codlog="00001", limite=0)


# ---------------------------------------------------------------------------
# Integração com dados reais
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIntegracaoDadosReais:
    def test_busca_por_prefixo_retorna_resultados(self) -> None:
        from services.domain.codlog_match import match_codlog

        resultado = match_codlog(CodlogMatchInput(input_codlog="0", limite=5))
        assert len(resultado) > 0
        assert all(r.codlog.startswith("0") for r in resultado)

    def test_busca_exata_retorna_um_resultado(self) -> None:
        from services.domain.codlog_match import match_codlog

        # busca prefix para pegar um codlog real e então testa busca exata
        amostra = match_codlog(CodlogMatchInput(input_codlog="0", limite=1))
        assert len(amostra) == 1
        codlog = amostra[0].codlog
        resultado = match_codlog(CodlogMatchInput(input_codlog=codlog))
        assert len(resultado) >= 1
        assert all(r.codlog == codlog for r in resultado)
