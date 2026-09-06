"""
Testes de avaliar_direcao (SPEC user_admin/014): quem dirige a unidade hoje, com as duas faltas
distintas — sem direção (titular afastado sem substituto) e sem titular (a vaga). Domínio puro.
"""

from services.domain.titularidade import Direcao, EstadoDaDirecao, avaliar_direcao


def _estado(**overrides: object) -> EstadoDaDirecao:
    dados: dict[str, object] = {
        "tem_titular": True,
        "titular_em_exercicio": True,
        "substituto_do_titular_em_exercicio": False,
    }
    dados.update(overrides)
    return EstadoDaDirecao(**dados)  # type: ignore[arg-type]


def test_direcao_distingue_titular_substituto_e_as_duas_faltas() -> None:
    titular_em_exercicio = _estado(titular_em_exercicio=True)
    assert avaliar_direcao(titular_em_exercicio) == Direcao.TITULAR

    substituto_cobrindo = _estado(
        titular_em_exercicio=False,
        substituto_do_titular_em_exercicio=True,
    )
    assert avaliar_direcao(substituto_cobrindo) == Direcao.SUBSTITUTO

    ninguem_cobre = _estado(
        titular_em_exercicio=False,
        substituto_do_titular_em_exercicio=False,
    )
    assert avaliar_direcao(ninguem_cobre) == Direcao.SEM_DIRECAO

    # A vaga responde antes de qualquer marca de exercício.
    vaga = _estado(
        tem_titular=False,
        titular_em_exercicio=True,
        substituto_do_titular_em_exercicio=True,
    )
    assert avaliar_direcao(vaga) == Direcao.SEM_TITULAR
