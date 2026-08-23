"""O que o modal de atribuir oferece a uma unidade (SPEC autorizacao/007)."""

from django.db.models import QuerySet

from apps.unidades.models import Unidade

from .models import Acao


def acoes_oferecidas(unidade: Unidade) -> QuerySet[Acao]:
    """Ativas e ainda não atribuídas. A estrutural entra como qualquer outra: excluí-la exigiria uma
    lista de slugs privilegiados, que é a configuração em runtime que o §3.5 recusa."""
    return Acao.objects.exclude(atribuicoes__unidade=unidade).filter(ativa=True)
