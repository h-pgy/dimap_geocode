"""Testes de services/domain/autorizacao/avaliador.py (SPEC autorizacao/003).

Cobre: cruzamento de caneta × concessão por cargo base ou em comissão, exigência de unidade exata,
isolamento entre as canetas de quem cobre outra unidade, ação inativa fora do resultado, as duas
portas da estrutural (direção e concessão) e o exercício como pré-condição de qualquer competência.
"""

from services.domain.autorizacao import (
    AvaliacaoCompetenciaInput,
    Caneta,
    ConcessaoVigente,
    PerfilCompetencia,
    avaliar_competencia,
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _caneta(**overrides: object) -> Caneta:
    dados: dict[str, object] = {
        "unidade_id": 1,
        "cargo_base_id": None,
        "cargo_comissao_id": None,
        "dirige_a_unidade": False,
    }
    dados.update(overrides)
    return Caneta(**dados)  # type: ignore[arg-type]


def _concessao(**overrides: object) -> ConcessaoVigente:
    dados: dict[str, object] = {
        "acao_slug": "competencias.acao_teste",
        "acao_ativa": True,
        "unidade_id": 1,
        "cargo_base_id": None,
        "cargo_comissao_id": None,
    }
    dados.update(overrides)
    return ConcessaoVigente(**dados)  # type: ignore[arg-type]


def _perfil(**overrides: object) -> PerfilCompetencia:
    dados: dict[str, object] = {
        "em_exercicio": True,
        "canetas": (_caneta(),),
    }
    dados.update(overrides)
    return PerfilCompetencia(**dados)  # type: ignore[arg-type]


def _avaliacao(**overrides: object) -> AvaliacaoCompetenciaInput:
    dados: dict[str, object] = {
        "perfil": _perfil(),
        "concessoes": (),
        "slugs_estruturais": frozenset(),
    }
    dados.update(overrides)
    return AvaliacaoCompetenciaInput(**dados)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Cruzamento caneta × concessão
# ---------------------------------------------------------------------------


def test_avaliador_libera_por_cargo_base_ou_comissao() -> None:
    caneta = _caneta(unidade_id=1, cargo_base_id=10, cargo_comissao_id=20)

    liberada_por_base = avaliar_competencia(
        _avaliacao(
            perfil=_perfil(canetas=(caneta,)),
            concessoes=(_concessao(acao_slug="a.base", unidade_id=1, cargo_base_id=10),),
        )
    )
    liberada_por_comissao = avaliar_competencia(
        _avaliacao(
            perfil=_perfil(canetas=(caneta,)),
            concessoes=(_concessao(acao_slug="a.comissao", unidade_id=1, cargo_comissao_id=20),),
        )
    )
    sem_match = avaliar_competencia(
        _avaliacao(
            perfil=_perfil(canetas=(caneta,)),
            concessoes=(_concessao(acao_slug="a.sem_match", unidade_id=1, cargo_base_id=99),),
        )
    )

    assert liberada_por_base.slugs_liberados == frozenset({"a.base"})
    assert liberada_por_comissao.slugs_liberados == frozenset({"a.comissao"})
    assert sem_match.slugs_liberados == frozenset()


def test_avaliador_exige_unidade_exata() -> None:
    caneta = _caneta(unidade_id=1, cargo_base_id=10)

    saida = avaliar_competencia(
        _avaliacao(
            perfil=_perfil(canetas=(caneta,)),
            # Mesmo cargo, unidade superior — não é a caneta, e não há herança pelo organograma.
            concessoes=(_concessao(acao_slug="a.outra_unidade", unidade_id=2, cargo_base_id=10),),
        )
    )

    assert saida.slugs_liberados == frozenset()


def test_avaliador_nao_cruza_canetas() -> None:
    propria = _caneta(unidade_id=1, cargo_base_id=10)
    coberta = _caneta(unidade_id=2, cargo_base_id=20)

    saida = avaliar_competencia(
        _avaliacao(
            perfil=_perfil(canetas=(propria, coberta)),
            concessoes=(
                # Cargo da caneta coberta, na unidade da própria — cruzamento inválido.
                _concessao(acao_slug="a.cruzada1", unidade_id=1, cargo_base_id=20),
                # Cargo da própria, na unidade da coberta — cruzamento inválido no sentido oposto.
                _concessao(acao_slug="a.cruzada2", unidade_id=2, cargo_base_id=10),
            ),
        )
    )

    assert saida.slugs_liberados == frozenset()


def test_avaliador_ignora_acao_inativa() -> None:
    caneta = _caneta(unidade_id=1, cargo_base_id=10)

    saida = avaliar_competencia(
        _avaliacao(
            perfil=_perfil(canetas=(caneta,)),
            concessoes=(
                _concessao(
                    acao_slug="a.inativa", acao_ativa=False, unidade_id=1, cargo_base_id=10
                ),
            ),
        )
    )

    assert saida.slugs_liberados == frozenset()


# ---------------------------------------------------------------------------
# As duas portas da estrutural
# ---------------------------------------------------------------------------


def test_avaliador_libera_estrutural_para_quem_dirige() -> None:
    dirige = _caneta(unidade_id=1, dirige_a_unidade=True)
    nao_dirige = _caneta(unidade_id=1, dirige_a_unidade=False)
    slugs_estruturais = frozenset({"competencias.estrutural"})

    saida_dirige = avaliar_competencia(
        _avaliacao(perfil=_perfil(canetas=(dirige,)), slugs_estruturais=slugs_estruturais)
    )
    saida_nao_dirige = avaliar_competencia(
        _avaliacao(perfil=_perfil(canetas=(nao_dirige,)), slugs_estruturais=slugs_estruturais)
    )

    assert saida_dirige.slugs_liberados == slugs_estruturais
    assert saida_nao_dirige.slugs_liberados == frozenset()


def test_avaliador_libera_estrutural_concedida_a_outro_cargo() -> None:
    caneta = _caneta(unidade_id=1, cargo_base_id=10, dirige_a_unidade=False)

    saida = avaliar_competencia(
        _avaliacao(
            perfil=_perfil(canetas=(caneta,)),
            concessoes=(
                _concessao(acao_slug="competencias.estrutural", unidade_id=1, cargo_base_id=10),
            ),
            slugs_estruturais=frozenset({"competencias.estrutural"}),
        )
    )

    assert saida.slugs_liberados == frozenset({"competencias.estrutural"})


# ---------------------------------------------------------------------------
# Exercício como pré-condição
# ---------------------------------------------------------------------------


def test_avaliador_nega_tudo_fora_de_exercicio() -> None:
    caneta = _caneta(unidade_id=1, cargo_base_id=10, dirige_a_unidade=True)

    saida = avaliar_competencia(
        _avaliacao(
            perfil=_perfil(em_exercicio=False, canetas=(caneta,)),
            concessoes=(_concessao(acao_slug="a.concedida", unidade_id=1, cargo_base_id=10),),
            slugs_estruturais=frozenset({"a.estrutural"}),
        )
    )

    assert saida.slugs_liberados == frozenset()
