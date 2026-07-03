import pytest

from services.utils.normalization import chave_numero_porta
from services.utils.normalization.sem_numero import CANONICO_SEM_NUMERO


# ---------------------------------------------------------------------------
# chave_numero_porta — compõe normalize_text + normalize_sem_numero + strip de espaços
# ---------------------------------------------------------------------------


class TestChaveNumeroComum:
    @pytest.mark.parametrize("valor", ["10a", "10-A", "10 A", "10A"])
    def test_variacoes_de_10a_colapsam(self, valor: str) -> None:
        # caixa, traço e espaço interno colapsam na mesma chave
        assert chave_numero_porta(valor) == "10A"

    def test_numero_puro_intacto(self) -> None:
        assert chave_numero_porta("100") == "100"


class TestChaveSemNumero:
    @pytest.mark.parametrize(
        "grafia",
        ["s/n", "S/N", "sn", "s.n.", "s/nº", "sem número", "sem numero", "SEM NÚMERO"],
    )
    def test_todas_grafias_viram_o_mesmo_token(self, grafia: str) -> None:
        assert chave_numero_porta(grafia) == CANONICO_SEM_NUMERO

    def test_numero_comum_nao_vira_sem_numero(self) -> None:
        # a canonicalização é ancorada: números comuns não casam
        assert chave_numero_porta("100") != CANONICO_SEM_NUMERO
        assert chave_numero_porta("10A") != CANONICO_SEM_NUMERO


class TestChaveDoisLados:
    def test_input_e_base_saem_da_mesma_chave(self) -> None:
        # o que o usuário digita ("s/n") e o que está gravado na base ("SEM NÚMERO")
        # produzem a MESMA chave (single-source §7.1) — permite o match dos dois lados
        assert chave_numero_porta("s/n") == chave_numero_porta("SEM NÚMERO")

    def test_idempotente(self) -> None:
        for valor in ["s/n", "10-A", "100"]:
            chave = chave_numero_porta(valor)
            assert chave_numero_porta(chave) == chave

    def test_sem_espacos_residuais(self) -> None:
        assert " " not in chave_numero_porta("10 A")
