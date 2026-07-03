"""
Testes dos localizadores de número (SPEC 010): o esqueleto comum parametrizado pelo
leitor permissivo (`parse_numero_porta`) devolve sempre o TOKEN BRUTO — quem parseia
(estrito ou permissivo) é o identifier consumidor.
"""

from services.domain.roteamento_busca.split_localizadores import (
    separar_numero,
    separar_numero_codlog,
    split_tipo_nome,
)


# ---------------------------------------------------------------------------
# separar_numero — logradouro por nome
# ---------------------------------------------------------------------------


class TestSepararNumero:
    def test_alfanumerico_com_virgula(self) -> None:
        assert separar_numero("Rua X, 10A") == ("Rua X", "10A")

    def test_sem_numero_com_virgula(self) -> None:
        # novo comportamento: "s/n" passa a ser reconhecido como token de número
        assert separar_numero("Rua X, s/n") == ("Rua X", "s/n")

    def test_rua_numerada_sem_virgula(self) -> None:
        assert separar_numero("rua 25 de março 100") == ("rua 25 de março", "100")

    def test_marcador_antes_do_numero(self) -> None:
        # o marcador ('nº') é descartado do prefixo (eh_so_marcador)
        assert separar_numero("av paulista nº 100") == ("av paulista", "100")

    def test_sem_numero_retorna_none(self) -> None:
        assert separar_numero("avenida paulista") is None

    def test_comeca_com_digito_retorna_none(self) -> None:
        # separar_numero exige começar com letra (é o caminho por nome)
        assert separar_numero("20") is None

    def test_token_bruto_preservado(self) -> None:
        # devolve o token como digitado, sem normalizar
        _, token = separar_numero("Rua X, 10-A")  # type: ignore[misc]
        assert token == "10-A"


# ---------------------------------------------------------------------------
# separar_numero_codlog — codlog + número
# ---------------------------------------------------------------------------


class TestSepararNumeroCodlog:
    def test_codlog_numero_sem_virgula(self) -> None:
        assert separar_numero_codlog("12345 100") == ("12345", "100")

    def test_codlog_sem_numero_com_barra(self) -> None:
        assert separar_numero_codlog("12345, s/n") == ("12345", "s/n")

    def test_ponto_rejeita_entrada_inteira(self) -> None:
        # ponto é formato de contribuinte — a entrada inteira sai deste caminho,
        # inclusive "12345, s.n." (que tem ponto)
        assert separar_numero_codlog("12345, s.n.") is None

    def test_so_codlog_sem_numero_retorna_none(self) -> None:
        assert separar_numero_codlog("12345") is None

    def test_comeca_com_letra_retorna_none(self) -> None:
        assert separar_numero_codlog("avenida paulista") is None


# ---------------------------------------------------------------------------
# split_tipo_nome
# ---------------------------------------------------------------------------


class TestSplitTipoNome:
    def test_tipo_e_nome(self) -> None:
        assert split_tipo_nome("avenida paulista") == ("avenida", "paulista")

    def test_token_unico_vira_so_nome(self) -> None:
        assert split_tipo_nome("paulista") == ("", "paulista")

    def test_nome_composto(self) -> None:
        assert split_tipo_nome("rua 25 de março") == ("rua", "25 de março")

    def test_vazio(self) -> None:
        assert split_tipo_nome("") == ("", "")
