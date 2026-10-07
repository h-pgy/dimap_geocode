"""
Testes de services/domain/tipos_unidade/avaliador.py (SPEC user_admin/031): a regra que barra o ato
repetido — extinguir o já extinto, reativar o vigente.

Domínio puro: os avaliadores recebem a prévia já projetada e devolvem o veredito, sem tocar em
banco nem em Django. Sem marker, portanto. O que a edição pode tocar (`AvaliadorEdicaoTipoUnidade`)
e o resto do comportamento do ato vivem em tests/apps/unidades/, que passam pelo banco para contar
as unidades do tipo e gravar a data.
"""

from services.domain.tipos_unidade import (
    IdentidadeTipoUnidade,
    PreviaDaExtincaoTipoUnidade,
    PreviaDaReativacaoTipoUnidade,
    avaliar_extincao_tipo,
    avaliar_reativacao_tipo,
)


def _identidade(nome: str = "Divisão", tipo_id: int = 1) -> IdentidadeTipoUnidade:
    return IdentidadeTipoUnidade(tipo_id=tipo_id, nome=nome)


# ---------------------------------------------------------------------------
# O ato repetido é recusado, com motivo
# ---------------------------------------------------------------------------


def test_veredito_recusa_ato_repetido() -> None:
    extincao = avaliar_extincao_tipo(
        PreviaDaExtincaoTipoUnidade(tipo=_identidade(), unidades_ativas=0, ja_extinto=True)
    )
    assert extincao.pode is False
    assert extincao.motivo != ""

    reativacao = avaliar_reativacao_tipo(
        PreviaDaReativacaoTipoUnidade(tipo=_identidade(), ja_vigente=True)
    )
    assert reativacao.pode is False
    assert reativacao.motivo != ""
