"""
Testes de services/domain/cargos/avaliador.py (SPEC user_admin/029): a regra que barra o ato
repetido — extinguir o já extinto, reativar o vigente.

Domínio puro: os avaliadores recebem a prévia já projetada e devolvem o veredito, sem tocar em
banco nem em Django. Sem marker, portanto. O que a edição pode tocar (`AvaliadorEdicao`) e o resto
do comportamento do ato vivem em tests/apps/cargos/, que passam pelo banco para contar ocupante e
gravar a data.
"""

from services.domain.cargos import (
    IdentidadeCargo,
    PreviaDaExtincaoCargo,
    PreviaDaReativacaoCargo,
    avaliar_extincao_cargo,
    avaliar_reativacao_cargo,
)


def _identidade(nome: str = "Diretor de Divisão", cargo_id: int = 1) -> IdentidadeCargo:
    return IdentidadeCargo(cargo_id=cargo_id, nome=nome, padrao="CDA-IV")


# ---------------------------------------------------------------------------
# O ato repetido é recusado, com motivo
# ---------------------------------------------------------------------------


def test_veredito_recusa_ato_repetido() -> None:
    extincao = avaliar_extincao_cargo(
        PreviaDaExtincaoCargo(cargo=_identidade(), ocupantes=0, ja_extinto=True)
    )
    assert extincao.pode is False
    assert extincao.motivo != ""

    reativacao = avaliar_reativacao_cargo(
        PreviaDaReativacaoCargo(cargo=_identidade(), ja_vigente=True)
    )
    assert reativacao.pode is False
    assert reativacao.motivo != ""
