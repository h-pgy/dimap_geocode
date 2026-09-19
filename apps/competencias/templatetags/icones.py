from django import template

from services.domain.autorizacao import VarianteIcone

from ..icones import ResolvedorIcones

register = template.Library()

# Uma instância basta: o cache que importa é o do processo, em `ResolvedorIcones._cache`.
_resolvedor = ResolvedorIcones()


@register.simple_tag
def icone_acao(slug: str, variante: VarianteIcone | str) -> str:
    # O template também passa a variante como literal ("pequeno"): o StrEnum aceita os dois.
    variante_icone = VarianteIcone(variante)
    return _resolvedor(slug, variante_icone)
