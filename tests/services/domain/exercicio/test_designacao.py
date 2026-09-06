"""
Testes de avaliar_designacao (SPEC user_admin/015): quem pode cobrir quem, e quando — a mesma
regra que o `clean()` da substituição e a lista de candidatos da tela consultam. Domínio puro,
sem Django.
"""

from datetime import date

from services.domain.exercicio import (
    Designacao,
    Periodo,
    Substituido,
    Substituto,
    avaliar_designacao,
)


def _periodo(inicio: date, fim: date | None = None) -> Periodo:
    return Periodo(inicio=inicio, fim=fim)


def _substituido(**overrides: object) -> Substituido:
    dados: dict[str, object] = {
        "perfil_id": 1,
        "exonerado": False,
        "tem_cargo_comissao": True,
        "substituicoes_recebidas": (),
    }
    dados.update(overrides)
    return Substituido(**dados)  # type: ignore[arg-type]


def _substituto(**overrides: object) -> Substituto:
    dados: dict[str, object] = {
        "perfil_id": 2,
        "exonerado": False,
        "impedimentos": (),
        "substituicoes_exercidas": (),
    }
    dados.update(overrides)
    return Substituto(**dados)  # type: ignore[arg-type]


def _designacao(**overrides: object) -> Designacao:
    periodo = _periodo(date(2026, 1, 1), date(2026, 1, 31))
    dados: dict[str, object] = {
        "periodo": periodo,
        "periodo_do_impedimento": periodo,
        "substituido": _substituido(),
        "substituto": _substituto(),
    }
    dados.update(overrides)
    return Designacao(**dados)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# O lado do substituído: cargo em comissão, exoneração e não-sobreposição das substituições dele
# ---------------------------------------------------------------------------


def test_designacao_exige_substituido_com_cargo_e_sem_substituicao_no_periodo() -> None:
    sem_cargo = _designacao(substituido=_substituido(tem_cargo_comissao=False))
    assert avaliar_designacao(sem_cargo) is False

    substituido_exonerado = _designacao(substituido=_substituido(exonerado=True))
    assert avaliar_designacao(substituido_exonerado) is False

    periodo_da_designacao = _periodo(date(2026, 2, 1), date(2026, 2, 15))
    impedimento_amplo = _periodo(date(2026, 2, 1), date(2026, 3, 31))

    # Já é substituído em período que cruza — venha do mesmo impedimento ou de outro sobreposto:
    # é uma regra só.
    cruzando = _designacao(
        periodo=periodo_da_designacao,
        periodo_do_impedimento=impedimento_amplo,
        substituido=_substituido(
            substituicoes_recebidas=(_periodo(date(2026, 2, 10), date(2026, 2, 20)),)
        ),
    )
    assert avaliar_designacao(cruzando) is False

    # Fica em sequência, sem cruzar: aceita.
    em_sequencia = _designacao(
        periodo=periodo_da_designacao,
        periodo_do_impedimento=impedimento_amplo,
        substituido=_substituido(
            substituicoes_recebidas=(_periodo(date(2026, 2, 16), date(2026, 2, 28)),)
        ),
    )
    assert avaliar_designacao(em_sequencia) is True


# ---------------------------------------------------------------------------
# O lado do substituto: impedimento próprio, exoneração, cobertura simultânea e a autossubstituição
# ---------------------------------------------------------------------------


def test_designacao_exige_substituto_livre_no_periodo() -> None:
    periodo_da_designacao = _periodo(date(2026, 3, 1), date(2026, 3, 15))
    impedimento_do_substituido = _periodo(date(2026, 3, 1), date(2026, 3, 31))

    impedido = _designacao(
        periodo=periodo_da_designacao,
        periodo_do_impedimento=impedimento_do_substituido,
        substituto=_substituto(
            impedimentos=(_periodo(date(2026, 3, 5), date(2026, 3, 10)),)
        ),
    )
    assert avaliar_designacao(impedido) is False

    substituto_exonerado = _designacao(
        periodo=periodo_da_designacao,
        periodo_do_impedimento=impedimento_do_substituido,
        substituto=_substituto(exonerado=True),
    )
    assert avaliar_designacao(substituto_exonerado) is False

    ja_cobrindo_alguem = _designacao(
        periodo=periodo_da_designacao,
        periodo_do_impedimento=impedimento_do_substituido,
        substituto=_substituto(
            substituicoes_exercidas=(_periodo(date(2026, 3, 5), date(2026, 3, 20)),)
        ),
    )
    assert avaliar_designacao(ja_cobrindo_alguem) is False

    proprio_substituido = _designacao(
        periodo=periodo_da_designacao,
        periodo_do_impedimento=impedimento_do_substituido,
        substituido=_substituido(perfil_id=42),
        substituto=_substituto(perfil_id=42),
    )
    assert avaliar_designacao(proprio_substituido) is False

    # De outra unidade, com cargo em comissão próprio (inclusive titular de outra cadeira): aceita.
    de_outra_unidade = _designacao(
        periodo=periodo_da_designacao,
        periodo_do_impedimento=impedimento_do_substituido,
    )
    assert avaliar_designacao(de_outra_unidade) is True

    # Substitui outra pessoa, mas em período que não cruza: aceita.
    cobrindo_sem_cruzar = _designacao(
        periodo=periodo_da_designacao,
        periodo_do_impedimento=impedimento_do_substituido,
        substituto=_substituto(
            substituicoes_exercidas=(_periodo(date(2026, 4, 1), date(2026, 4, 10)),)
        ),
    )
    assert avaliar_designacao(cobrindo_sem_cruzar) is True
