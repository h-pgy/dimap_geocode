from collections.abc import Mapping

from django import template

register = template.Library()


@register.filter(name="realce_do")
def realce_do(realce: Mapping[str, str], controle: str) -> str:
    # As linhas repetíveis têm nome com sufixo: o template não indexa um dicionário por variável.
    return realce.get(controle, "")
