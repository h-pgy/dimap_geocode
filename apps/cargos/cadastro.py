"""
Os atos que mantêm os dois catálogos de cargo (SPECs user_admin/029 e 030): criar grava um cargo
novo, editar altera identificação sempre. Em cargo em comissão, natureza/nível só mudam enquanto
ninguém o ocupa — a trava (SPEC 029, §7) vive aqui, conferida no servidor, e não na tela; cargo base
não tem campo nenhum que a ocupação proteja (SPEC 030, §2), e por isso `editar_cargo_base` não tem
trava alguma.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.cargos.consulta import ocupantes_no_quadro
from apps.cargos.formularios import (
    ler_edicao_cargo,
    ler_edicao_cargo_base,
    ler_nova_cargo,
    ler_nova_cargo_base,
    recusa_de_natureza,
    traduzir_recusa,
    traduzir_recusa_base,
)
from apps.cargos.models import CargoBase, CargoComissao
from apps.cargos.schemas import EdicaoCargo
from apps.core.erros_formulario import de_validation_error
from services.domain.cargos import IdentidadeCargo, PreviaDaEdicao, avaliar_edicao
from services.utils.erros_formulario import RecusaDeFormulario


@dataclass(frozen=True)
class DesfechoCargo:
    """Mesma forma do `DesfechoUnidade`: gravou (`cargo`) ou recusou (`recusa`) — serve às duas
    operações de cadastro e às duas do ato de extinção/reativação (`apps/cargos/extincao.py`)."""

    cargo: CargoComissao | None
    recusa: RecusaDeFormulario = RecusaDeFormulario()


@dataclass(frozen=True)
class DesfechoCargoBase:
    """Mesma forma de `DesfechoCargo`, para o catálogo de cargo base (SPEC user_admin/030)."""

    cargo: CargoBase | None
    recusa: RecusaDeFormulario = RecusaDeFormulario()


def criar_cargo(valores: Mapping[str, Any]) -> DesfechoCargo:
    leitura = ler_nova_cargo(valores)
    nova = leitura.dto
    if nova is None:
        return DesfechoCargo(cargo=None, recusa=leitura.recusa or RecusaDeFormulario())
    cargo = CargoComissao(
        nome=nova.nome,
        sigla=nova.sigla,
        nivel=nova.nivel,
        e_chefia=nova.e_chefia,
        alta_administracao=nova.alta_administracao,
    )
    return _gravar(cargo)


def editar_cargo(cargo: CargoComissao, valores: Mapping[str, Any]) -> DesfechoCargo:
    leitura = ler_edicao_cargo(valores)
    if leitura.dto is None:
        return DesfechoCargo(cargo=None, recusa=leitura.recusa or RecusaDeFormulario())
    travas = avaliar_edicao(
        PreviaDaEdicao(cargo=_identidade(cargo), ocupantes=ocupantes_no_quadro(cargo))
    )
    # `disabled` não chega ao servidor, e requisição forjada não vê tela nenhuma: a trava vale
    # aqui, comparando o que veio com o que está gravado.
    if travas.natureza_travada and _natureza_mudou(cargo, leitura.dto):
        return DesfechoCargo(cargo=None, recusa=recusa_de_natureza(travas.motivo))
    cargo.nome = leitura.dto.nome
    cargo.sigla = leitura.dto.sigla
    if not travas.natureza_travada:
        cargo.nivel = leitura.dto.nivel
        cargo.e_chefia = leitura.dto.e_chefia
        cargo.alta_administracao = leitura.dto.alta_administracao
    try:
        with transaction.atomic():
            # A consistência alta_administracao × nivel × e_chefia é do model e não se reescreve
            # aqui.
            cargo.full_clean()
            cargo.save()
    except ValidationError as recusa:
        return DesfechoCargo(cargo=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    return DesfechoCargo(cargo=cargo)


def _identidade(cargo: CargoComissao) -> IdentidadeCargo:
    return IdentidadeCargo(cargo_id=cargo.pk, nome=cargo.nome, padrao=cargo.padrao)


def _natureza_mudou(cargo: CargoComissao, edicao: EdicaoCargo) -> bool:
    return (
        cargo.nivel != edicao.nivel
        or cargo.e_chefia != edicao.e_chefia
        or cargo.alta_administracao != edicao.alta_administracao
    )


def _gravar(cargo: CargoComissao) -> DesfechoCargo:
    try:
        cargo.full_clean()
        cargo.save()
    except ValidationError as recusa:
        return DesfechoCargo(cargo=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    return DesfechoCargo(cargo=cargo)


def criar_cargo_base(valores: Mapping[str, Any]) -> DesfechoCargoBase:
    leitura = ler_nova_cargo_base(valores)
    nova = leitura.dto
    if nova is None:
        return DesfechoCargoBase(cargo=None, recusa=leitura.recusa or RecusaDeFormulario())
    cargo = CargoBase(nome=nova.nome, sigla=nova.sigla)
    return _gravar_base(cargo)


def editar_cargo_base(cargo: CargoBase, valores: Mapping[str, Any]) -> DesfechoCargoBase:
    leitura = ler_edicao_cargo_base(valores)
    if leitura.dto is None:
        return DesfechoCargoBase(cargo=None, recusa=leitura.recusa or RecusaDeFormulario())
    cargo.nome = leitura.dto.nome
    cargo.sigla = leitura.dto.sigla
    try:
        with transaction.atomic():
            cargo.full_clean()
            cargo.save()
    except ValidationError as recusa:
        return DesfechoCargoBase(cargo=None, recusa=traduzir_recusa_base(de_validation_error(recusa)))
    return DesfechoCargoBase(cargo=cargo)


def _gravar_base(cargo: CargoBase) -> DesfechoCargoBase:
    try:
        cargo.full_clean()
        cargo.save()
    except ValidationError as recusa:
        return DesfechoCargoBase(cargo=None, recusa=traduzir_recusa_base(de_validation_error(recusa)))
    return DesfechoCargoBase(cargo=cargo)
