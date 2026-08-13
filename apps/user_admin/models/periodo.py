"""
A convenção de período que impedimento e substituição partilham (SPEC user_admin/015): início
obrigatório, fim nulo = indeterminado. O predicado mora num lugar só porque cinco leituras fazem
esta mesma pergunta — uma delas esquecendo o fim nulo faz o sistema responder duas coisas sobre a
mesma pessoa.
"""

from datetime import date

from django.db.models import Q


def q_vigente_em(dia: date) -> Q:
    return Q(data_inicio__lte=dia) & (Q(data_fim__isnull=True) | Q(data_fim__gte=dia))


def q_em_aberto_em(dia: date) -> Q:
    """Vigente ou ainda por vir — é sobre estes que a tela oferece designar substituto."""
    return Q(data_fim__isnull=True) | Q(data_fim__gte=dia)
