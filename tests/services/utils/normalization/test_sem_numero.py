import pytest

from services.utils.normalization import normalize_sem_numero, normalize_text
from services.utils.normalization.sem_numero import CANONICO_SEM_NUMERO, SemNumeroNormalizer


# ---------------------------------------------------------------------------
# Canonicalização das grafias de "sem número"
#
# normalize_sem_numero ASSUME input já passado por normalize_text (§7.1). Os casos
# abaixo usam as saídas REAIS da normalize_text para cada grafia crua.
# ---------------------------------------------------------------------------


class TestCanonizaSemNumero:
    @pytest.mark.parametrize(
        "texto_normalizado",
        ["S N", "SN", "S NO", "S Nº", "SEM NUMERO"],
    )
    def test_formas_normalizadas_viram_token_canonico(self, texto_normalizado: str) -> None:
        assert normalize_sem_numero(texto_normalizado) == CANONICO_SEM_NUMERO

    def test_saidas_reais_da_normalize_text_colapsam(self) -> None:
        # ponta a ponta: normalize_text + normalize_sem_numero para todas as grafias cruas
        for cru in ["s/n", "S/N", "sn", "s.n.", "s/nº", "s/n°", "s/no", "sem número", "sem numero"]:
            assert normalize_sem_numero(normalize_text(cru)) == CANONICO_SEM_NUMERO


# ---------------------------------------------------------------------------
# Números comuns passam INTACTOS (identidade)
# ---------------------------------------------------------------------------


class TestNumeroComumInalterado:
    @pytest.mark.parametrize("texto", ["10A", "100", "AV PAULISTA", "10 A", ""])
    def test_identidade(self, texto: str) -> None:
        assert normalize_sem_numero(texto) == texto


# ---------------------------------------------------------------------------
# Idempotência e contrato
# ---------------------------------------------------------------------------


class TestContrato:
    @pytest.mark.parametrize("texto", ["S N", "SN", "SEM NUMERO", "10A", "100"])
    def test_idempotente(self, texto: str) -> None:
        uma = normalize_sem_numero(texto)
        duas = normalize_sem_numero(uma)
        assert uma == duas

    def test_e_callable_e_instancia(self) -> None:
        assert callable(normalize_sem_numero)
        assert isinstance(normalize_sem_numero, SemNumeroNormalizer)

    def test_retorna_str(self) -> None:
        assert isinstance(normalize_sem_numero("S N"), str)
