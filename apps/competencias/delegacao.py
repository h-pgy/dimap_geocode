"""
Atos administrativos de delegação nominal de competência estrutural (SPEC autorizacao/009).
"""

from collections.abc import Callable, Collection
from dataclasses import dataclass
from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from apps.competencias.formularios import traduzir_recusa_delegacao
from apps.competencias.models import AtribuicaoUnidade, Delegacao
from apps.competencias.schemas import NovaDelegacao
from apps.core.erros_formulario import de_validation_error
from apps.unidades.models import Unidade
from apps.user_admin.models import Impedimento, Perfil, q_vigente_em
from services.utils.erros_formulario import ErroBruto, RecusaDeFormulario


@dataclass(frozen=True)
class DesfechoDelegacao:
    delegacao: Delegacao | None
    recusa: RecusaDeFormulario = RecusaDeFormulario()


def delegar_competencia(
    atribuicao: AtribuicaoUnidade,
    dados: NovaDelegacao,
    delegante: Perfil,
    alcance: Collection[int],
) -> DesfechoDelegacao:
    recusa = recusa_de_delegado_fora_do_alcance(dados.delegado, alcance)
    if recusa is not None:
        return DesfechoDelegacao(delegacao=None, recusa=recusa)
    return _desfecho(lambda: _gravar_delegacao(atribuicao, dados, delegante))


def encerrar_delegacao(delegacao: Delegacao) -> None:
    with transaction.atomic():
        encerrar_delegacao_em(delegacao, timezone.localdate())


def encerrar_delegacao_em(delegacao: Delegacao, dia: date) -> None:
    if dia <= delegacao.data_inicio:
        delegacao.delete()
        return
    delegacao.data_fim = dia
    delegacao.save(update_fields=["data_fim"])


def recusa_de_delegado_fora_do_alcance(
    delegado_id: int,
    alcance: Collection[int],
) -> RecusaDeFormulario | None:
    lotacao = Perfil.objects.filter(pk=delegado_id).values_list("unidade_id", flat=True).first()
    if lotacao is not None and lotacao in alcance:
        return None
    return traduzir_recusa_delegacao(
        (
            ErroBruto(
                controle="delegado",
                tipo="fora_do_alcance",
                mensagem="Servidor fora do seu alcance.",
            ),
        )
    )


def candidatos_a_delegado(unidade: Unidade, alcance: Collection[int]) -> list[Perfil]:
    hoje = timezone.localdate()
    return list(
        Perfil.objects.filter(unidade_id__in=alcance, is_active=True)
        .exclude(impedimentos__in=Impedimento.objects.filter(q_vigente_em(hoje)))
        .select_related("unidade", "cargo_base", "cargo_comissao")
        .order_by("nome", "sobrenome")
    )


def _gravar_delegacao(
    atribuicao: AtribuicaoUnidade,
    dados: NovaDelegacao,
    delegante: Perfil,
) -> Delegacao:
    with transaction.atomic():
        delegado = Perfil.objects.get(pk=dados.delegado)
        delegacao = Delegacao(
            acao=atribuicao.acao,
            unidade=atribuicao.unidade,
            delegante=delegante,
            delegado=delegado,
            data_inicio=dados.data_inicio,
            data_fim=dados.data_fim,
        )
        delegacao.full_clean()
        delegacao.save()
        return delegacao


def _desfecho(escrever: Callable[[], Delegacao]) -> DesfechoDelegacao:
    try:
        return DesfechoDelegacao(delegacao=escrever())
    except DjangoValidationError as erro:
        return DesfechoDelegacao(
            delegacao=None,
            recusa=traduzir_recusa_delegacao(de_validation_error(erro)),
        )
