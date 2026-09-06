"""Consultas de borda (SPEC user_admin/018): banco → DTO, para a regra de domínio que não lê banco."""

from apps.unidades.models import Unidade
from services.domain.arvore_hierarquica import (
    ArvoreHierarquica,
    ComandoPosicao,
    ParHierarquia,
    PosicaoHierarquica,
)


def posicao_de(unidade_id: int, com_extintas: bool = False) -> PosicaoHierarquica:
    """Duas colunas de um organograma de dezenas de linhas: ler tudo custa menos que uma recursão
    em SQL, e mantém a regra fora do ORM.

    `com_extintas` (SPEC user_admin/025) troca para o gerente sem filtro — sem isso a unidade
    recém-extinta sairia da própria posição, e nem o alcance de quem a extinguiu a alcançaria."""
    gerente = Unidade.todas if com_extintas else Unidade.objects
    pares = tuple(
        ParHierarquia(unidade_id=pk, pai_id=pai_id)
        for pk, pai_id in gerente.values_list("id", "pai_id")
    )
    return ArvoreHierarquica()(ComandoPosicao(unidade_id=unidade_id, pares=pares))
