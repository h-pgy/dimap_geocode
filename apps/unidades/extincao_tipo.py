"""
O ato de extinguir e reativar tipo de unidade (SPEC user_admin/031): uma coluna e nada mais —
extinguir NÃO toca em unidade, titularidade nem competência (SPEC, §7); as unidades do tipo seguem
no organograma, e só o cadastro de unidades deixa de oferecê-lo. A projeção model → DTO mora aqui,
e não no domínio, que não conhece `TipoUnidade`.
"""

from datetime import date

from apps.unidades.cadastro_tipo import DesfechoTipoUnidade
from apps.unidades.consulta import unidades_ativas_do_tipo
from apps.unidades.formularios import recusa_do_veredito_tipo
from apps.unidades.models import TipoUnidade
from services.domain.tipos_unidade import (
    IdentidadeTipoUnidade,
    PreviaDaExtincaoTipoUnidade,
    PreviaDaReativacaoTipoUnidade,
    avaliar_extincao_tipo,
    avaliar_reativacao_tipo,
)


def previa_da_extincao_tipo(tipo: TipoUnidade) -> PreviaDaExtincaoTipoUnidade:
    return PreviaDaExtincaoTipoUnidade(
        tipo=_identidade(tipo),
        unidades_ativas=unidades_ativas_do_tipo(tipo),
        ja_extinto=tipo.extinto_em is not None,
    )


def previa_da_reativacao_tipo(tipo: TipoUnidade) -> PreviaDaReativacaoTipoUnidade:
    return PreviaDaReativacaoTipoUnidade(tipo=_identidade(tipo), ja_vigente=tipo.extinto_em is None)


def _identidade(tipo: TipoUnidade) -> IdentidadeTipoUnidade:
    return IdentidadeTipoUnidade(tipo_id=tipo.pk, nome=tipo.nome)


def extinguir_tipo_unidade(tipo: TipoUnidade, hoje: date) -> DesfechoTipoUnidade:
    veredito = avaliar_extincao_tipo(previa_da_extincao_tipo(tipo))
    if not veredito.pode:
        return DesfechoTipoUnidade(tipo=None, recusa=recusa_do_veredito_tipo(veredito.motivo))
    tipo.extinto_em = hoje
    tipo.save(update_fields=["extinto_em"])
    return DesfechoTipoUnidade(tipo=tipo)


def reativar_tipo_unidade(tipo: TipoUnidade) -> DesfechoTipoUnidade:
    veredito = avaliar_reativacao_tipo(previa_da_reativacao_tipo(tipo))
    if not veredito.pode:
        return DesfechoTipoUnidade(tipo=None, recusa=recusa_do_veredito_tipo(veredito.motivo))
    tipo.extinto_em = None
    tipo.save(update_fields=["extinto_em"])
    return DesfechoTipoUnidade(tipo=tipo)
