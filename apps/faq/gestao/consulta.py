from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.faq.models import Faq as FaqModel
from services.domain.faq import Situacao

SITUACOES_ATIVAS = frozenset({Situacao.RASCUNHO, Situacao.PUBLICADA})
SITUACOES_COM_EXCLUIDAS = SITUACOES_ATIVAS | {Situacao.EXCLUIDA}


def faq_editavel(
    faq_id: int,
    situacoes: frozenset[Situacao] = SITUACOES_ATIVAS,
) -> FaqModel:
    # A excluída some com 404 de toda rota, menos da restauração, que pede {EXCLUIDA}.
    return get_object_or_404(FaqModel, pk=faq_id, situacao__in=situacoes)


def faqs_editaveis(
    situacoes: frozenset[Situacao] = SITUACOES_ATIVAS,
) -> QuerySet[FaqModel]:
    return (
        FaqModel.objects.filter(situacao__in=situacoes)
        .select_related("autor", "editado_por", "tema__pai")
        .prefetch_related("perguntas")
    )
