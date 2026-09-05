"""
O ato de extinguir e reativar cargo em comissão (SPEC user_admin/029): uma coluna e nada mais —
extinguir NÃO revalida titularidade, competência nem concessão (§7), o que faz o ato ser bem mais
barato que o análogo de unidade. A projeção model → DTO mora aqui, e não no domínio, que não conhece
`CargoComissao`.
"""

from datetime import date

from apps.cargos.cadastro import DesfechoCargo
from apps.cargos.consulta import ocupantes_no_quadro
from apps.cargos.formularios import recusa_do_veredito
from apps.cargos.models import CargoComissao
from services.domain.cargos import (
    IdentidadeCargo,
    PreviaDaExtincaoCargo,
    PreviaDaReativacaoCargo,
    avaliar_extincao_cargo,
    avaliar_reativacao_cargo,
)


def previa_da_extincao(cargo: CargoComissao) -> PreviaDaExtincaoCargo:
    return PreviaDaExtincaoCargo(
        cargo=_identidade(cargo),
        ocupantes=ocupantes_no_quadro(cargo),
        ja_extinto=cargo.extinto_em is not None,
    )


def previa_da_reativacao(cargo: CargoComissao) -> PreviaDaReativacaoCargo:
    return PreviaDaReativacaoCargo(cargo=_identidade(cargo), ja_vigente=cargo.extinto_em is None)


def _identidade(cargo: CargoComissao) -> IdentidadeCargo:
    return IdentidadeCargo(cargo_id=cargo.pk, nome=cargo.nome, padrao=cargo.padrao)


def extinguir_cargo(cargo: CargoComissao, hoje: date) -> DesfechoCargo:
    veredito = avaliar_extincao_cargo(previa_da_extincao(cargo))
    if not veredito.pode:
        return DesfechoCargo(cargo=None, recusa=recusa_do_veredito(veredito.motivo))
    # Uma coluna e nada mais: extinguir NÃO mexe em perfil, titularidade, concessão nem delegação
    # — o cargo continua sendo avaliado, e é isso que o distingue da extinção de unidade.
    cargo.extinto_em = hoje
    cargo.save(update_fields=["extinto_em"])
    return DesfechoCargo(cargo=cargo)


def reativar_cargo(cargo: CargoComissao) -> DesfechoCargo:
    veredito = avaliar_reativacao_cargo(previa_da_reativacao(cargo))
    if not veredito.pode:
        return DesfechoCargo(cargo=None, recusa=recusa_do_veredito(veredito.motivo))
    cargo.extinto_em = None
    cargo.save(update_fields=["extinto_em"])
    return DesfechoCargo(cargo=cargo)
