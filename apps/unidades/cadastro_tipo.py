"""
Os atos que mantêm o catálogo de tipos de unidade (SPEC user_admin/031): criar grava um tipo novo,
editar altera o nome sempre. Nível, permissão de raiz, requisito de titular e tipos filhos vedados
só mudam enquanto nenhuma unidade do organograma usa o tipo — a trava (SPEC, §7) vive aqui,
conferida no servidor, e não na tela.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.erros_formulario import de_validation_error
from apps.unidades.consulta import unidades_ativas_do_tipo
from apps.unidades.formularios import (
    ler_edicao_tipo_unidade,
    ler_novo_tipo_unidade,
    recusa_de_estrutura,
    traduzir_recusa_tipo,
)
from apps.unidades.models import TipoUnidade
from apps.unidades.schemas import EdicaoTipoUnidade
from services.domain.tipos_unidade import (
    IdentidadeTipoUnidade,
    PreviaDaEdicaoTipoUnidade,
    avaliar_edicao_tipo,
)
from services.utils.erros_formulario import RecusaDeFormulario


@dataclass(frozen=True)
class DesfechoTipoUnidade:
    """Mesma forma do `DesfechoUnidade`: gravou (`tipo`) ou recusou (`recusa`) — serve às duas
    operações de cadastro e às duas do ato de extinção/reativação (`extincao_tipo.py`)."""

    tipo: TipoUnidade | None
    recusa: RecusaDeFormulario = RecusaDeFormulario()


def criar_tipo_unidade(valores: Mapping[str, Any]) -> DesfechoTipoUnidade:
    leitura = ler_novo_tipo_unidade(valores)
    novo = leitura.dto
    if novo is None:
        return DesfechoTipoUnidade(tipo=None, recusa=leitura.recusa or RecusaDeFormulario())
    tipo = TipoUnidade(
        nome=novo.nome,
        nivel=novo.nivel,
        pode_ser_raiz=novo.pode_ser_raiz,
        exige_alta_administracao=novo.exige_alta_administracao,
        nivel_minimo_titular=novo.nivel_minimo_titular,
    )
    try:
        with transaction.atomic():
            tipo.full_clean()
            tipo.save()
            tipo.tipos_filhos_vedados.set(_tipos_existentes(novo.tipos_filhos_vedados))
    except ValidationError as recusa:
        return DesfechoTipoUnidade(tipo=None, recusa=traduzir_recusa_tipo(de_validation_error(recusa)))
    return DesfechoTipoUnidade(tipo=tipo)


def editar_tipo_unidade(tipo: TipoUnidade, valores: Mapping[str, Any]) -> DesfechoTipoUnidade:
    leitura = ler_edicao_tipo_unidade(valores)
    if leitura.dto is None:
        return DesfechoTipoUnidade(tipo=None, recusa=leitura.recusa or RecusaDeFormulario())
    travas = avaliar_edicao_tipo(
        PreviaDaEdicaoTipoUnidade(
            tipo=_identidade(tipo),
            unidades_ativas=unidades_ativas_do_tipo(tipo),
        )
    )
    # `disabled` não chega ao servidor, e requisição forjada não vê tela nenhuma: a trava vale
    # aqui, comparando o que veio com o que está gravado.
    if travas.estrutura_travada and _estrutura_mudou(tipo, leitura.dto):
        return DesfechoTipoUnidade(tipo=None, recusa=recusa_de_estrutura(travas.motivo))
    tipo.nome = leitura.dto.nome
    if not travas.estrutura_travada:
        tipo.nivel = leitura.dto.nivel
        tipo.pode_ser_raiz = leitura.dto.pode_ser_raiz
        tipo.exige_alta_administracao = leitura.dto.exige_alta_administracao
        tipo.nivel_minimo_titular = leitura.dto.nivel_minimo_titular
    try:
        with transaction.atomic():
            # A consistência alta administração × nível mínimo é do model e não se reescreve aqui.
            tipo.full_clean()
            tipo.save()
            if not travas.estrutura_travada:
                tipo.tipos_filhos_vedados.set(_tipos_existentes(leitura.dto.tipos_filhos_vedados))
    except ValidationError as recusa:
        return DesfechoTipoUnidade(tipo=None, recusa=traduzir_recusa_tipo(de_validation_error(recusa)))
    return DesfechoTipoUnidade(tipo=tipo)


def _identidade(tipo: TipoUnidade) -> IdentidadeTipoUnidade:
    return IdentidadeTipoUnidade(tipo_id=tipo.pk, nome=tipo.nome)


def _estrutura_mudou(tipo: TipoUnidade, edicao: EdicaoTipoUnidade) -> bool:
    vedados = set(tipo.tipos_filhos_vedados.values_list("pk", flat=True))
    return (
        tipo.nivel != edicao.nivel
        or tipo.pode_ser_raiz != edicao.pode_ser_raiz
        or tipo.exige_alta_administracao != edicao.exige_alta_administracao
        or tipo.nivel_minimo_titular != edicao.nivel_minimo_titular
        # Conjunto, e não lista: a ordem dos campos da tela não é a do banco.
        or vedados != set(edicao.tipos_filhos_vedados)
    )


def _tipos_existentes(ids: tuple[int, ...]) -> list[TipoUnidade]:
    # Id forjado não vira linha na tabela de vedas: a FK só acusaria no commit, fora do alcance
    # da recusa do formulário.
    return list(TipoUnidade.objects.filter(pk__in=ids))
