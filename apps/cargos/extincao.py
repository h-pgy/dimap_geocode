"""
O ato de extinguir e reativar os dois catálogos de cargo (SPECs user_admin/029 e 030): uma coluna e
nada mais — extinguir NÃO revalida titularidade, competência nem concessão (SPEC 029, §7), o que faz
o ato ser bem mais barato que o análogo de unidade. A projeção model → DTO mora aqui, e não no
domínio, que não conhece `CargoComissao` nem `CargoBase`.
"""

from datetime import date

from apps.cargos.cadastro import DesfechoCargo, DesfechoCargoBase
from apps.cargos.consulta import ocupantes_no_quadro
from apps.cargos.formularios import recusa_do_veredito, recusa_do_veredito_base
from apps.cargos.models import CargoBase, CargoComissao
from services.domain.cargos import (
    IdentidadeCargo,
    IdentidadeCargoBase,
    PreviaDaExtincaoCargo,
    PreviaDaExtincaoCargoBase,
    PreviaDaReativacaoCargo,
    PreviaDaReativacaoCargoBase,
    avaliar_extincao_cargo,
    avaliar_extincao_cargo_base,
    avaliar_reativacao_cargo,
    avaliar_reativacao_cargo_base,
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


def previa_da_extincao_base(cargo: CargoBase) -> PreviaDaExtincaoCargoBase:
    return PreviaDaExtincaoCargoBase(
        cargo=_identidade_base(cargo),
        ocupantes=ocupantes_no_quadro(cargo),
        ja_extinto=cargo.extinto_em is not None,
    )


def previa_da_reativacao_base(cargo: CargoBase) -> PreviaDaReativacaoCargoBase:
    return PreviaDaReativacaoCargoBase(
        cargo=_identidade_base(cargo), ja_vigente=cargo.extinto_em is None
    )


def _identidade_base(cargo: CargoBase) -> IdentidadeCargoBase:
    return IdentidadeCargoBase(cargo_id=cargo.pk, nome=cargo.nome)


def extinguir_cargo_base(cargo: CargoBase, hoje: date) -> DesfechoCargoBase:
    veredito = avaliar_extincao_cargo_base(previa_da_extincao_base(cargo))
    if not veredito.pode:
        return DesfechoCargoBase(cargo=None, recusa=recusa_do_veredito_base(veredito.motivo))
    cargo.extinto_em = hoje
    cargo.save(update_fields=["extinto_em"])
    return DesfechoCargoBase(cargo=cargo)


def reativar_cargo_base(cargo: CargoBase) -> DesfechoCargoBase:
    veredito = avaliar_reativacao_cargo_base(previa_da_reativacao_base(cargo))
    if not veredito.pode:
        return DesfechoCargoBase(cargo=None, recusa=recusa_do_veredito_base(veredito.motivo))
    cargo.extinto_em = None
    cargo.save(update_fields=["extinto_em"])
    return DesfechoCargoBase(cargo=cargo)
