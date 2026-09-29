import pytest

from services.domain.roteamento_busca import (
    GeocodificacaoExternaParse,
    RoteamentoQuery,
    RoteamentoResult,
    TipoEntrada,
    rotear_entrada,
)


def rotear(texto: str) -> RoteamentoResult:
    return rotear_entrada(RoteamentoQuery(texto=texto))


# ---------------------------------------------------------------------------
# O candidato externo: mesma regra do endereço por nome, sempre por último
# ---------------------------------------------------------------------------


def test_identifier_emite_geocodificacao_externa_com_o_texto_inteiro() -> None:
    r = rotear("rua augusta, 100 - consolação")

    ultimo = r.candidatos[-1]
    assert isinstance(ultimo, GeocodificacaoExternaParse)
    assert ultimo.texto == "rua augusta, 100 - consolação"


@pytest.mark.parametrize(
    "texto",
    ["12345, 100", "rua augusta", "rua x, s/n"],
    ids=["codlog", "sem-numero", "s/n"],
)
def test_identifier_nao_emite_para_codlog_nem_sem_numero(texto: str) -> None:
    assert TipoEntrada.GEOCODIFICACAO_EXTERNA not in rotear(texto).tipos
