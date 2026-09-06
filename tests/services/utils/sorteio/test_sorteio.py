"""Testes de services/utils/sorteio (SPEC design/010): o sorteio que nunca repete a opção atual,
salvo quando excluí-la esvazia as alternativas.
"""

from services.utils.sorteio import sortear_diferente

OPCOES = ("anhangabau", "ibirapuera", "butanta")


# ---------------------------------------------------------------------------
# Sorteio
# ---------------------------------------------------------------------------


def test_sorteio_nunca_devolve_a_atual() -> None:
    for _ in range(50):
        assert sortear_diferente(OPCOES, "anhangabau") != "anhangabau"


def test_sorteio_com_opcao_unica_devolve_ela() -> None:
    assert sortear_diferente(("anhangabau",), "anhangabau") == "anhangabau"
