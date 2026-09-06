"""
Testes de services/domain/extincao_unidade/avaliador.py (SPEC user_admin/025): as duas regras que
decidem se o ato pode acontecer — só sai quem tem para onde mandar o que carrega, e só volta quem
está fora e tem onde pendurar.

Domínio puro: os avaliadores recebem a prévia já projetada e devolvem o veredito, sem tocar em
banco nem em Django. Sem marker, portanto — rodam na suíte rápida. O que a rota faz com o veredito
está em tests/apps/unidades/views/test_extincao_unidade.py.
"""

from services.domain.extincao_unidade import (
    MOTIVO_JA_EXTINTA,
    MOTIVO_JA_VIGENTE,
    MOTIVO_RAIZ,
    IdentidadeUnidade,
    PreviaDaExtincao,
    PreviaDaReativacao,
    avaliar_extincao,
    avaliar_reativacao,
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _identidade(sigla: str = "DIMAP-2", unidade_id: int = 2) -> IdentidadeUnidade:
    return IdentidadeUnidade(unidade_id=unidade_id, sigla=sigla)


def _previa_extincao(**overrides: object) -> PreviaDaExtincao:
    dados: dict[str, object] = {
        "unidade": _identidade(),
        "destino": _identidade("DIMAP", 1),
        "servidores": 3,
        "subordinadas": 1,
    }
    dados.update(overrides)
    return PreviaDaExtincao(**dados)  # type: ignore[arg-type]


def _previa_reativacao(**overrides: object) -> PreviaDaReativacao:
    dados: dict[str, object] = {
        "unidade": _identidade(),
        "superior": _identidade("DIMAP", 1),
        "superior_extinta": False,
        "atribuicoes": 2,
        "concessoes": 4,
    }
    dados.update(overrides)
    return PreviaDaReativacao(**dados)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Extinção: só sai quem tem para onde mandar o que carrega
# ---------------------------------------------------------------------------


def test_extincao_passa_quando_ha_destino() -> None:
    veredito = avaliar_extincao(_previa_extincao())

    assert veredito.pode is True
    assert veredito.motivo == ""


def test_extincao_recusa_a_raiz() -> None:
    veredito = avaliar_extincao(_previa_extincao(destino=None))

    assert veredito.pode is False
    assert veredito.motivo == MOTIVO_RAIZ


def test_extincao_ve_a_ja_extinta_antes_do_destino() -> None:
    """A ordem é a regra, não detalhe: o POST repetido chega com a unidade já extinta e o destino
    ainda de pé, e precisa ouvir que ela já saiu — não que não há para onde mandar."""
    veredito = avaliar_extincao(_previa_extincao(ja_extinta=True))

    assert veredito.pode is False
    assert veredito.motivo == MOTIVO_JA_EXTINTA


# ---------------------------------------------------------------------------
# Reativação: só volta quem está fora e tem onde pendurar
# ---------------------------------------------------------------------------


def test_reativacao_passa_quando_a_superior_esta_de_pe() -> None:
    veredito = avaliar_reativacao(_previa_reativacao())

    assert veredito.pode is True
    assert veredito.motivo == ""


def test_reativacao_recusa_a_que_nao_esta_extinta() -> None:
    veredito = avaliar_reativacao(_previa_reativacao(ja_vigente=True))

    assert veredito.pode is False
    assert veredito.motivo == MOTIVO_JA_VIGENTE


def test_reativacao_nomeia_a_superior_a_reativar_primeiro() -> None:
    """Nomear a sigla é o que faz a recusa ser acionável: sem ela, quem reabre um ramo em cadeia
    não sabe por onde começar."""
    veredito = avaliar_reativacao(
        _previa_reativacao(superior=_identidade("DIMAP-1", 9), superior_extinta=True)
    )

    assert veredito.pode is False
    assert "DIMAP-1" in veredito.motivo
