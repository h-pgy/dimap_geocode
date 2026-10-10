from services.domain.documento_selado import gerar_codigo
from services.domain.documento_selado.constants import ALFABETO_CODIGO, TAMANHO_CODIGO

# I, L, O e U se confundem com dígito na leitura de um papel (§6 da SPEC 007) e por isso ficam
# fora do alfabeto — a checagem é redundante com `ALFABETO_CODIGO`, mas prova a razão do recorte.
CARACTERES_AMBIGUOS = frozenset("ILOU")


# ---------------------------------------------------------------------------
# O código sorteado é aleatório e nunca traz caractere ambíguo
# ---------------------------------------------------------------------------


def test_codigo_eh_aleatorio_no_alfabeto_sem_ambiguidade() -> None:
    primeiro = gerar_codigo()
    segundo = gerar_codigo()

    assert primeiro != segundo
    for codigo in (primeiro, segundo):
        assert len(codigo) == TAMANHO_CODIGO
        assert set(codigo) <= set(ALFABETO_CODIGO)
        assert not set(codigo) & CARACTERES_AMBIGUOS
