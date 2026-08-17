"""
Testes de ArvoreHierarquica (SPEC user_admin/018): onde uma unidade está no organograma — o
caminho do topo até ela e a subárvore que pende dela. Domínio puro, sem Django: as arestas chegam
achatadas em `ParHierarquia`.
"""

from services.domain.arvore_hierarquica import (
    ArvoreHierarquica,
    ComandoPosicao,
    NoHierarquia,
    ParHierarquia,
    PosicaoHierarquica,
)


def _par(unidade_id: int, pai_id: int | None) -> ParHierarquia:
    return ParHierarquia(unidade_id=unidade_id, pai_id=pai_id)


def _posicao(unidade_id: int, pares: tuple[ParHierarquia, ...]) -> PosicaoHierarquica:
    return ArvoreHierarquica()(ComandoPosicao(unidade_id=unidade_id, pares=pares))


# ---------------------------------------------------------------------------
# Caminho e subárvore
# ---------------------------------------------------------------------------


def test_posicao_traz_o_caminho_e_a_subarvore() -> None:
    pares = (
        _par(1, None),
        _par(2, 1),
        _par(3, 2),
        _par(4, 1),  # tio: ramo irmão de 2, fora do caminho e fora do ego
        _par(5, 3),  # filha do ego
        _par(6, 2),  # irmã do ego, fora do ego
    )

    posicao = _posicao(3, pares)

    assert posicao.acima == (1, 2)
    assert posicao.ego.unidade_id == 3
    assert posicao.ego.ids == frozenset({3, 5})


def test_posicao_do_topo_nao_tem_caminho() -> None:
    pares = (
        _par(1, None),
        _par(2, 1),
        _par(3, 1),
    )

    posicao = _posicao(1, pares)

    assert posicao.acima == ()
    assert posicao.ego.ids == frozenset({1, 2, 3})


def test_posicao_de_folha_tem_ego_sem_filhas() -> None:
    pares = (
        _par(1, None),
        _par(2, 1),
        _par(3, 2),
    )

    posicao = _posicao(3, pares)

    assert posicao.ego.filhas == ()
    assert posicao.acima == (1, 2)


# ---------------------------------------------------------------------------
# `ids` derivado
# ---------------------------------------------------------------------------


def test_ids_leem_a_propria_arvore() -> None:
    no = NoHierarquia(
        unidade_id=1,
        filhas=(
            NoHierarquia(unidade_id=2, filhas=(NoHierarquia(unidade_id=4),)),
            NoHierarquia(unidade_id=3),
        ),
    )

    assert no.ids == frozenset({1, 2, 3, 4})


# ---------------------------------------------------------------------------
# Ciclo longo (A→B→A) tolerado, sem recursão sem fim
# ---------------------------------------------------------------------------


def test_posicao_nao_trava_em_ciclo() -> None:
    pares = (
        _par(1, 2),
        _par(2, 1),
    )

    posicao = _posicao(1, pares)

    assert set(posicao.acima) == {1, 2}
    assert posicao.ego.unidade_id == 1
    assert posicao.ego.ids == frozenset({1, 2})
    # A descida para no nó já visitado: nenhuma filha se repete.
    assert [filha.unidade_id for filha in posicao.ego.filhas] == [2]
    assert posicao.ego.filhas[0].filhas == ()
