import pytest

from services.domain.geometry.coordinates import (
    eh_anel,
    eh_linha,
    eh_multilinha,
    eh_multipoligono,
    eh_poligono,
    eh_ponto,
)

# ---------------------------------------------------------------------------
# eh_ponto
# ---------------------------------------------------------------------------

P = [1.0, 2.0]
P2 = [3.0, 4.0]
P3 = [5.0, 6.0]
P4 = [1.0, 2.0]  # igual a P (para fechar anel)


def test_ponto_aceita_dois_numeros() -> None:
    assert eh_ponto([1.0, 2.0]) is True


def test_ponto_aceita_int() -> None:
    assert eh_ponto([1, 2]) is True


def test_ponto_rejeita_um_numero() -> None:
    assert eh_ponto([1.0]) is False


def test_ponto_rejeita_tres_numeros() -> None:
    assert eh_ponto([1.0, 2.0, 3.0]) is False


def test_ponto_rejeita_bool() -> None:
    assert eh_ponto([True, False]) is False


def test_ponto_rejeita_string() -> None:
    assert eh_ponto(["a", "b"]) is False


def test_ponto_rejeita_nao_sequencia() -> None:
    assert eh_ponto(42) is False


def test_ponto_rejeita_lista_vazia() -> None:
    assert eh_ponto([]) is False


# ---------------------------------------------------------------------------
# eh_linha
# ---------------------------------------------------------------------------


def test_linha_aceita_dois_pontos() -> None:
    assert eh_linha([P, P2]) is True


def test_linha_aceita_mais_de_dois_pontos() -> None:
    assert eh_linha([P, P2, P3]) is True


def test_linha_rejeita_um_ponto() -> None:
    assert eh_linha([P]) is False


def test_linha_rejeita_lista_vazia() -> None:
    assert eh_linha([]) is False


def test_linha_rejeita_nao_lista() -> None:
    assert eh_linha(P) is False


# ---------------------------------------------------------------------------
# eh_multilinha
# ---------------------------------------------------------------------------


def test_multilinha_aceita_uma_linha() -> None:
    assert eh_multilinha([[P, P2]]) is True


def test_multilinha_aceita_varias_linhas() -> None:
    assert eh_multilinha([[P, P2], [P2, P3]]) is True


def test_multilinha_nao_exige_fechamento() -> None:
    # MultiLineString = lista de linhas abertas; fechamento não é requisito
    linha_aberta = [P, P2, P3]
    assert eh_multilinha([linha_aberta]) is True


def test_multilinha_rejeita_lista_vazia() -> None:
    assert eh_multilinha([]) is False


def test_multilinha_rejeita_lista_de_pontos() -> None:
    # primeiro elemento é um ponto, não uma linha
    assert eh_multilinha([P]) is False


# ---------------------------------------------------------------------------
# eh_anel
# ---------------------------------------------------------------------------

ANEL = [P, P2, P3, P]  # 4 pontos, fechado (P == P4)


def test_anel_aceita_anel_fechado() -> None:
    assert eh_anel(ANEL) is True


def test_anel_rejeita_aberto() -> None:
    assert eh_anel([P, P2, P3, P3]) is False  # último != primeiro


def test_anel_rejeita_menos_de_4_pontos() -> None:
    assert eh_anel([P, P2, P]) is False


def test_anel_rejeita_dois_pontos() -> None:
    assert eh_anel([P, P]) is False


def test_anel_rejeita_lista_vazia() -> None:
    assert eh_anel([]) is False


# ---------------------------------------------------------------------------
# eh_poligono
# ---------------------------------------------------------------------------


def test_poligono_aceita_anel_valido() -> None:
    assert eh_poligono([ANEL]) is True


def test_poligono_aceita_varios_aneis() -> None:
    assert eh_poligono([ANEL, ANEL]) is True


def test_poligono_rejeita_lista_vazia() -> None:
    assert eh_poligono([]) is False


def test_poligono_rejeita_anel_aberto() -> None:
    anel_aberto = [P, P2, P3, P2]
    assert eh_poligono([anel_aberto]) is False


def test_poligono_rejeita_profundidade_errada() -> None:
    # recebe uma linha em vez de uma lista de anéis
    assert eh_poligono([P, P2]) is False


# ---------------------------------------------------------------------------
# eh_multipoligono
# ---------------------------------------------------------------------------


def test_multipoligono_aceita_poligono_valido() -> None:
    assert eh_multipoligono([[ANEL]]) is True


def test_multipoligono_aceita_varios_poligonos() -> None:
    assert eh_multipoligono([[ANEL], [ANEL]]) is True


def test_multipoligono_rejeita_lista_vazia() -> None:
    assert eh_multipoligono([]) is False


def test_multipoligono_rejeita_profundidade_errada() -> None:
    # recebe polígono diretamente em vez de lista de polígonos
    assert eh_multipoligono([ANEL]) is False


# ---------------------------------------------------------------------------
# Separação de ramos: multilinha NÃO é polígono
# ---------------------------------------------------------------------------


def test_multilinha_nao_e_poligono() -> None:
    multilinha = [[P, P2], [P2, P3]]
    assert eh_multilinha(multilinha) is True
    assert eh_poligono(multilinha) is False


@pytest.mark.parametrize("coords", [
    [P, P2],              # linha solta (não é multilinha de uma profundidade extra)
    [[P, P2, P3, P2]],    # anel aberto (não fecha)
    [[[P, P2]]],          # profundidade demais para multilinha
])
def test_multilinha_rejeita_formas_incorretas(coords: object) -> None:
    assert eh_multilinha(coords) is False or eh_anel(coords) is False  # pelo menos um falha
