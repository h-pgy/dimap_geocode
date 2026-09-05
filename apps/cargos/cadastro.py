"""
Os dois atos que mantêm o catálogo de cargos em comissão (SPEC user_admin/029): criar grava um
cargo novo, editar altera identificação sempre e natureza/nível só enquanto ninguém o ocupa — a
trava (SPEC, §7) vive aqui, conferida no servidor, e não na tela.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.cargos.consulta import ocupantes_no_quadro
from apps.cargos.formularios import ler_edicao_cargo, ler_nova_cargo, recusa_de_natureza, traduzir_recusa
from apps.cargos.models import CargoComissao
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
