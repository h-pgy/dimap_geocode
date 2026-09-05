"""Consultas de borda (SPEC user_admin/029): a regra de quem pode ser nomeado, num lugar só."""

from django.db.models import Q, QuerySet

from apps.cargos.models import CargoComissao


def cargos_nomeaveis(cargo_atual_id: int | None = None) -> QuerySet[CargoComissao]:
    """Os cargos que uma nomeação pode escolher: os vigentes, mais o que o servidor JÁ ocupa.

    Sem a segunda metade, abrir a edição de quem ocupa cargo extinto para trocar o e-mail gravaria
    o cargo vazio — a tela apagaria a nomeação sem ninguém pedir.
    """
    nomeaveis = Q(extinto_em__isnull=True)
    if cargo_atual_id is not None:
        nomeaveis |= Q(pk=cargo_atual_id)
    return CargoComissao.objects.filter(nomeaveis).order_by("nome")


def ocupantes_no_quadro(cargo: CargoComissao) -> int:
    # Exonerado não ocupa mais: quem trava a edição é quem está no quadro hoje.
    return cargo.perfis.filter(is_active=True, exonerado_em__isnull=True).count()
