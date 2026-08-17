"""Consultas de borda (SPEC user_admin/018): banco → DTO, para a regra de domínio que não lê banco."""

from apps.user_admin.models import Unidade
from services.domain.arvore_hierarquica import (
    ArvoreHierarquica,
    ComandoPosicao,
    ParHierarquia,
    PosicaoHierarquica,
)


def posicao_de(unidade_id: int) -> PosicaoHierarquica:
    """Duas colunas de um organograma de dezenas de linhas: ler tudo custa menos que uma recursão
    em SQL, e mantém a regra fora do ORM."""
    pares = tuple(
        ParHierarquia(unidade_id=pk, pai_id=pai_id)
        for pk, pai_id in Unidade.objects.values_list("id", "pai_id")
    )
    return ArvoreHierarquica()(ComandoPosicao(unidade_id=unidade_id, pares=pares))
