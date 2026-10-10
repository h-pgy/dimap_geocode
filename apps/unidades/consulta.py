"""Consultas de borda (SPEC user_admin/018): banco → DTO, para a regra de domínio que não lê banco."""

from django.db.models import Q, QuerySet

from apps.unidades.models import TipoUnidade, Unidade
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


def tipos_unidade_disponiveis(tipo_atual_id: int | None = None) -> QuerySet[TipoUnidade]:
    """Os tipos que uma nova unidade ou alteração pode escolher: os vigentes, mais o que a unidade
    JÁ possui.

    Sem a segunda metade, abrir a edição de unidade de tipo extinto para trocar o nome gravaria
    outro tipo — a tela mudaria a hierarquia sem ninguém pedir.
    """
    disponiveis = Q(extinto_em__isnull=True)
    if tipo_atual_id is not None:
        disponiveis |= Q(pk=tipo_atual_id)
    # Nível decrescente: a lista de tipos desce da mais abrangente para a mais específica.
    return TipoUnidade.objects.filter(disponiveis).order_by("-nivel", "nome")


def unidades_ativas_do_tipo(tipo: TipoUnidade) -> int:
    # `tipo.unidades` já sai pelo `UnidadeVigenteManager`: unidade extinta não conta nem trava.
    return tipo.unidades.count()
