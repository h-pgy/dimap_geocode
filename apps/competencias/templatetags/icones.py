from django import template

from services.domain.autorizacao import VarianteIcone

from ..icones import ResolvedorIcones

register = template.Library()

# Uma instância basta: o cache que importa é o do processo, em `ResolvedorIcones._cache`.
_resolvedor = ResolvedorIcones()


@register.simple_tag
def icone_acao(slug: str, variante: VarianteIcone) -> str:
    return _resolvedor(slug, variante)
