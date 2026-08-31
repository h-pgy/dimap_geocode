"""
Testes de services/domain/exoneracao/avaliador.py (SPEC user_admin/027): as duas regras que
decidem se o ato pode acontecer — só sai do quadro quem está nele e não é quem assina, e só volta
quem está fora e tem lotação de pé para onde voltar.

Domínio puro: os avaliadores recebem a prévia já projetada e devolvem o veredito, sem tocar em
banco nem em Django. Sem marker, portanto — rodam na suíte rápida. O que a rota faz com o veredito
está em tests/apps/user_admin/views/test_exoneracao.py.
"""

from services.domain.exoneracao import (
    MOTIVO_AUTO_EXONERACAO,
    MOTIVO_JA_EXONERADO,
    MOTIVO_NO_QUADRO,
    IdentidadeServidor,
    PreviaDaExoneracao,
    PreviaDaReintegracao,
    avaliar_exoneracao,
    avaliar_reintegracao,
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _servidor(**overrides: object) -> IdentidadeServidor:
    dados: dict[str, object] = {"servidor_id": 1, "rf": "700100", "nome_completo": "Fulano de Tal"}
    dados.update(overrides)
    return IdentidadeServidor(**dados)  # type: ignore[arg-type]


def _previa_exoneracao(**overrides: object) -> PreviaDaExoneracao:
    dados: dict[str, object] = {
        "servidor": _servidor(),
        "unidade_que_dirige": None,
        "impedimentos_em_aberto": 0,
        "coberturas_em_curso": 0,
        "delegacoes_recebidas": 0,
        "administrador": False,
    }
    dados.update(overrides)
    return PreviaDaExoneracao(**dados)  # type: ignore[arg-type]


def _previa_reintegracao(**overrides: object) -> PreviaDaReintegracao:
    dados: dict[str, object] = {
        "servidor": _servidor(),
        "exonerado_em": None,
        "unidade": "DIVEX",
        "unidade_extinta": False,
    }
    dados.update(overrides)
    return PreviaDaReintegracao(**dados)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Exoneração: só sai quem está no quadro e não é quem assina
# ---------------------------------------------------------------------------


def test_avaliador_recusa_auto_exoneracao_e_quem_ja_saiu() -> None:
    assert avaliar_exoneracao(_previa_exoneracao()).pode is True

    ja_exonerado = avaliar_exoneracao(_previa_exoneracao(ja_exonerado=True))
    assert ja_exonerado.pode is False
    assert ja_exonerado.motivo == MOTIVO_JA_EXONERADO

    # A recusa vale antes de mais nada: o POST repetido chega com o servidor já fora do quadro, e
    # precisa ouvir isso — não que não pode exonerar a si mesmo.
    os_dois = avaliar_exoneracao(_previa_exoneracao(ja_exonerado=True, eh_o_proprio_autor=True))
    assert os_dois.motivo == MOTIVO_JA_EXONERADO

    auto_exoneracao = avaliar_exoneracao(_previa_exoneracao(eh_o_proprio_autor=True))
    assert auto_exoneracao.pode is False
    assert auto_exoneracao.motivo == MOTIVO_AUTO_EXONERACAO


# ---------------------------------------------------------------------------
# Reintegração: só volta quem está fora e tem lotação de pé para onde voltar
# ---------------------------------------------------------------------------


def test_avaliador_recusa_reintegracao_de_quem_esta_no_quadro_e_de_unidade_extinta() -> None:
    assert avaliar_reintegracao(_previa_reintegracao()).pode is True

    no_quadro = avaliar_reintegracao(_previa_reintegracao(ja_no_quadro=True))
    assert no_quadro.pode is False
    assert no_quadro.motivo == MOTIVO_NO_QUADRO

    # Nomeia a sigla a reativar primeiro: é o que faz a recusa ser acionável.
    unidade_extinta = avaliar_reintegracao(
        _previa_reintegracao(unidade="DIMAP-1", unidade_extinta=True)
    )
    assert unidade_extinta.pode is False
    assert "DIMAP-1" in unidade_extinta.motivo
