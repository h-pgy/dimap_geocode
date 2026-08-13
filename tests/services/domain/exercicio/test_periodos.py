"""
Testes de comparação e fatiamento de períodos (SPEC user_admin/015): a mesma convenção de
`Impedimento` e `Substituicao` — `fim=None` é indeterminado —, usada tanto para dizer se dois
períodos se cruzam quanto para fatiar um afastamento em trechos cobertos e descobertos. Domínio
puro, sem Django.
"""

from datetime import date

from services.domain.exercicio import (
    Periodo,
    Trecho,
    contem,
    lacunas,
    se_sobrepoem,
    trechos,
)


def _periodo(inicio: date, fim: date | None = None) -> Periodo:
    return Periodo(inicio=inicio, fim=fim)


# ---------------------------------------------------------------------------
# se_sobrepoem / contem — fim=None é a única guarda que este tipo de regra costuma esquecer
# ---------------------------------------------------------------------------


def test_periodos_com_fim_indeterminado_se_sobrepoem() -> None:
    indeterminado = _periodo(date(2026, 1, 1))
    depois_do_inicio = _periodo(date(2026, 6, 1), date(2026, 6, 10))
    antes_do_inicio = _periodo(date(2025, 1, 1), date(2025, 12, 31))
    assert se_sobrepoem(indeterminado, depois_do_inicio) is True
    assert se_sobrepoem(indeterminado, antes_do_inicio) is False

    # Se encostam pelas pontas — um termina no dia em que o outro começa —, se sobrepõem.
    encostados = _periodo(date(2026, 1, 1), date(2026, 1, 10))
    comeca_no_fim_do_outro = _periodo(date(2026, 1, 10), date(2026, 1, 20))
    assert se_sobrepoem(encostados, comeca_no_fim_do_outro) is True

    # Um termina na véspera do outro: não se sobrepõem.
    termina_na_vespera = _periodo(date(2026, 1, 1), date(2026, 1, 9))
    comeca_no_dia_seguinte = _periodo(date(2026, 1, 10), date(2026, 1, 20))
    assert se_sobrepoem(termina_na_vespera, comeca_no_dia_seguinte) is False

    # A contenção recusa substituição que termine depois de um impedimento com fim definido.
    impedimento = _periodo(date(2026, 1, 1), date(2026, 1, 31))
    dentro = _periodo(date(2026, 1, 5), date(2026, 1, 15))
    termina_depois_do_fim = _periodo(date(2026, 1, 5), date(2026, 2, 5))
    assert contem(impedimento, dentro) is True
    assert contem(impedimento, termina_depois_do_fim) is False


# ---------------------------------------------------------------------------
# lacunas / trechos — o afastamento fatiado em ordem, cobertos e descobertos alternados
# ---------------------------------------------------------------------------


def test_trechos_e_lacunas_do_afastamento() -> None:
    # Sem substituição nenhuma: um trecho só, descoberto, e é o afastamento inteiro — fim nulo
    # inclusive.
    afastamento_indeterminado = _periodo(date(2026, 1, 1))
    assert lacunas(afastamento_indeterminado, ()) == (afastamento_indeterminado,)
    sem_ocupacao = trechos(afastamento_indeterminado, ())
    assert len(sem_ocupacao) == 1
    assert sem_ocupacao[0].periodo == afastamento_indeterminado
    assert sem_ocupacao[0].substituto_id is None

    # Uma substituição no meio: sobram as duas pontas descobertas.
    afastamento = _periodo(date(2026, 1, 1), date(2026, 1, 31))
    no_meio = Trecho(
        periodo=_periodo(date(2026, 1, 10), date(2026, 1, 20)),
        substituto_id=1,
    )
    ponta_esquerda = _periodo(date(2026, 1, 1), date(2026, 1, 9))
    ponta_direita = _periodo(date(2026, 1, 21), date(2026, 1, 31))
    assert lacunas(afastamento, (no_meio.periodo,)) == (ponta_esquerda, ponta_direita)

    resultado = trechos(afastamento, (no_meio,))
    assert [trecho.periodo for trecho in resultado] == [
        ponta_esquerda,
        no_meio.periodo,
        ponta_direita,
    ]
    assert [trecho.substituto_id for trecho in resultado] == [None, 1, None]

    # Coberto de ponta a ponta: nenhuma lacuna e um trecho por substituição, na ordem.
    ponta_a_ponta = (
        Trecho(periodo=_periodo(date(2026, 1, 1), date(2026, 1, 15)), substituto_id=1),
        Trecho(periodo=_periodo(date(2026, 1, 16), date(2026, 1, 31)), substituto_id=2),
    )
    assert lacunas(afastamento, tuple(trecho.periodo for trecho in ponta_a_ponta)) == ()
    assert trechos(afastamento, ponta_a_ponta) == ponta_a_ponta
