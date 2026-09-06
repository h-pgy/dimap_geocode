"""O que o modal de atribuir oferece a uma unidade (SPEC autorizacao/007)."""

from django.db.models import QuerySet

from apps.unidades.models import Unidade

from .consulta import slugs_exclusivos
from .models import Acao


def acoes_oferecidas(unidade: Unidade) -> QuerySet[Acao]:
    """Ativas, ainda não atribuídas e não exclusivas do superusuário (SPEC user_admin/022): a
    exclusividade não se atribui nem se concede, e por isso nunca chega às telas de concessão. A
    estrutural comum entra como qualquer outra: excluí-la exigiria uma lista de slugs
    privilegiados, que é a configuração em runtime que o §3.5 recusa."""
    return (
        Acao.objects.exclude(atribuicoes__unidade=unidade)
        .exclude(slug__in=slugs_exclusivos())
        .filter(ativa=True)
    )
