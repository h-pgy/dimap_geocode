"""Consultas de borda (SPECs user_admin/029 e 030): a regra de quem pode ser nomeado, num lugar só,
para os dois catálogos de cargo."""

from django.db.models import Q, QuerySet

from apps.cargos.models import CargoBase, CargoComissao


def cargos_nomeaveis(cargo_atual_id: int | None = None) -> QuerySet[CargoComissao]:
    """Os cargos que uma nomeação pode escolher: os vigentes, mais o que o servidor JÁ ocupa.

    Sem a segunda metade, abrir a edição de quem ocupa cargo extinto para trocar o e-mail gravaria
    o cargo vazio — a tela apagaria a nomeação sem ninguém pedir.
    """
    nomeaveis = Q(extinto_em__isnull=True)
    if cargo_atual_id is not None:
        nomeaveis |= Q(pk=cargo_atual_id)
    return CargoComissao.objects.filter(nomeaveis).order_by("nome")


def cargos_base_nomeaveis(cargo_atual_id: int | None = None) -> QuerySet[CargoBase]:
    """Mesmo predicado de `cargos_nomeaveis`, sobre o outro catálogo (SPEC user_admin/030)."""
    nomeaveis = Q(extinto_em__isnull=True)
    if cargo_atual_id is not None:
        nomeaveis |= Q(pk=cargo_atual_id)
    return CargoBase.objects.filter(nomeaveis).order_by("nome")


def ocupantes_no_quadro(cargo: CargoBase | CargoComissao) -> int:
    # Exonerado não ocupa mais: quem trava a edição é quem está no quadro hoje. Os dois catálogos
    # expõem `.perfis` pelo mesmo related_name (SPEC user_admin/030).
    return cargo.perfis.filter(is_active=True, exonerado_em__isnull=True).count()
