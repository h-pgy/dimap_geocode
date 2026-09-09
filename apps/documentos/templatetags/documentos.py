"""Expõe `services.domain.documento_selado.datas.por_extenso` como filtro de template: a data
como ela sai no papel (SPEC documentos_oficiais/007) e no acervo é a MESMA função — não a duas."""

from datetime import datetime

from django.template import Library
from django.utils import timezone

from services.domain.documento_selado.datas import por_extenso as _por_extenso

register = Library()


@register.filter(name="por_extenso")
def por_extenso(momento: datetime) -> str:
    if timezone.is_aware(momento):
        momento = timezone.localtime(momento)
    return _por_extenso(momento)
