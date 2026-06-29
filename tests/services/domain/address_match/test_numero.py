import pytest

from services.domain.address_match import eh_so_marcador, parse_numero_imovel


# ---------------------------------------------------------------------------
# parse_numero_imovel — dígito puro e sufixo de unidade
# ---------------------------------------------------------------------------


class TestParseNumeroImovelDigitoPuro:
    def test_digito_simples(self) -> None:
        assert parse_numero_imovel("1") == 1

    def test_numero_maior(self) -> None:
        assert parse_numero_imovel("100") == 100

    def test_sufixo_letra_minuscula(self) -> None:
        assert parse_numero_imovel("1a") == 1

    def test_sufixo_letra_maiuscula(self) -> None:
        assert parse_numero_imovel("1-A") == 1

    def test_sufixo_letra_b(self) -> None:
        assert parse_numero_imovel("1b") == 1

    def test_sufixo_nao_altera_numero(self) -> None:
        assert parse_numero_imovel("250B") == 250

    def test_espacos_em_branco_ignorados(self) -> None:
        assert parse_numero_imovel("  42  ") == 42


# ---------------------------------------------------------------------------
# parse_numero_imovel — marcadores grudados ao dígito
# ---------------------------------------------------------------------------


class TestParseNumeroImovelMarcadoresGrudados:
    def test_marcador_n_simples(self) -> None:
        assert parse_numero_imovel("n1") == 1

    def test_marcador_n_ponto(self) -> None:
        assert parse_numero_imovel("n.1") == 1

    def test_marcador_n_ordinal_masculino(self) -> None:
        assert parse_numero_imovel("nº1") == 1

    def test_marcador_n_grau(self) -> None:
        assert parse_numero_imovel("n°1") == 1

    def test_marcador_no(self) -> None:
        assert parse_numero_imovel("no1") == 1

    def test_marcador_nro(self) -> None:
        assert parse_numero_imovel("nro1") == 1

    def test_marcador_nro_ponto(self) -> None:
        assert parse_numero_imovel("nro.1") == 1

    def test_marcador_num(self) -> None:
        assert parse_numero_imovel("num1") == 1

    def test_marcador_num_acentuado(self) -> None:
        assert parse_numero_imovel("núm1") == 1

    def test_marcador_num_ponto(self) -> None:
        assert parse_numero_imovel("num.1") == 1

    def test_marcador_num_acentuado_ponto(self) -> None:
        assert parse_numero_imovel("núm.1") == 1

    def test_marcador_numero(self) -> None:
        assert parse_numero_imovel("numero1") == 1

    def test_marcador_numero_acentuado(self) -> None:
        assert parse_numero_imovel("número1") == 1

    def test_marcador_cerquilha(self) -> None:
        assert parse_numero_imovel("#1") == 1


# ---------------------------------------------------------------------------
# parse_numero_imovel — marcadores separados do dígito por espaço
# ---------------------------------------------------------------------------


class TestParseNumeroImovelMarcadoresSeparados:
    def test_n_espaco_digito(self) -> None:
        assert parse_numero_imovel("n 1") == 1

    def test_n_ponto_espaco_digito(self) -> None:
        assert parse_numero_imovel("n. 1") == 1

    def test_ordinal_espaco_digito(self) -> None:
        assert parse_numero_imovel("nº 1") == 1

    def test_no_espaco_digito(self) -> None:
        assert parse_numero_imovel("no 1") == 1

    def test_nro_espaco_digito(self) -> None:
        assert parse_numero_imovel("nro 1") == 1

    def test_nro_ponto_espaco_digito(self) -> None:
        assert parse_numero_imovel("nro. 1") == 1

    def test_num_espaco_digito(self) -> None:
        assert parse_numero_imovel("num 1") == 1

    def test_numero_espaco_digito(self) -> None:
        assert parse_numero_imovel("número 1") == 1

    def test_numero_sem_acento_espaco_digito(self) -> None:
        assert parse_numero_imovel("numero 1") == 1

    def test_cerquilha_espaco_digito(self) -> None:
        assert parse_numero_imovel("# 1") == 1


# ---------------------------------------------------------------------------
# parse_numero_imovel — case-insensitive
# ---------------------------------------------------------------------------


class TestParseNumeroImovelCaseInsensitive:
    def test_marcador_maiusculo(self) -> None:
        assert parse_numero_imovel("N1") == 1

    def test_nro_maiusculo(self) -> None:
        assert parse_numero_imovel("NRO1") == 1

    def test_num_maiusculo(self) -> None:
        assert parse_numero_imovel("NUM1") == 1

    def test_numero_maiusculo(self) -> None:
        assert parse_numero_imovel("NUMERO 1") == 1


# ---------------------------------------------------------------------------
# parse_numero_imovel — retorna None quando não há dígito
# ---------------------------------------------------------------------------


class TestParseNumeroImovelRetornaNone:
    def test_texto_puro(self) -> None:
        assert parse_numero_imovel("abc") is None

    def test_norte_nao_engole(self) -> None:
        assert parse_numero_imovel("norte") is None

    def test_so_marcador_sem_digito(self) -> None:
        assert parse_numero_imovel("nº") is None

    def test_string_vazia(self) -> None:
        assert parse_numero_imovel("") is None

    def test_so_espacos(self) -> None:
        assert parse_numero_imovel("   ") is None


# ---------------------------------------------------------------------------
# eh_so_marcador — tokens que SÃO marcadores
# ---------------------------------------------------------------------------


class TestEhSoMarcadorVerdadeiro:
    @pytest.mark.parametrize(
        "token",
        ["n", "n.", "nº", "n°", "no", "nro", "nro.", "num", "núm", "num.", "núm.", "numero", "número", "#"],
    )
    def test_marcadores_validos(self, token: str) -> None:
        assert eh_so_marcador(token) is True

    def test_case_insensitive_NRO(self) -> None:
        assert eh_so_marcador("NRO") is True

    def test_case_insensitive_NUM(self) -> None:
        assert eh_so_marcador("NUM") is True

    def test_espacos_em_volta_ignorados(self) -> None:
        assert eh_so_marcador("  nº  ") is True


# ---------------------------------------------------------------------------
# eh_so_marcador — tokens que NÃO são marcadores
# ---------------------------------------------------------------------------


class TestEhSoMarcadorFalso:
    def test_palavra_norte(self) -> None:
        assert eh_so_marcador("norte") is False

    def test_nome_de_rua(self) -> None:
        assert eh_so_marcador("paulista") is False

    def test_digito(self) -> None:
        assert eh_so_marcador("100") is False

    def test_marcador_com_digito_grudado(self) -> None:
        assert eh_so_marcador("nº1") is False

    def test_string_vazia(self) -> None:
        assert eh_so_marcador("") is False
