from collections.abc import Mapping

from django import template

from apps.faq.models import Anexo as AnexoModel

register = template.Library()


@register.filter(name="anexos_da")
def anexos_da(
    anexos_por_faq: Mapping[int, list[AnexoModel]] | None, faq_id: int
) -> list[AnexoModel]:
    # O template não indexa um dicionário por variável.
    return (anexos_por_faq or {}).get(faq_id, [])
