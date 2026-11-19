from django import template
from django.utils.safestring import SafeString, mark_safe

from services.utils.markdown import RenderizadorMarkdown

register = template.Library()

renderizar = RenderizadorMarkdown()


@register.filter(name="markdown")
def markdown(texto: str) -> SafeString:
    # Seguro porque a saída passou pela allowlist do nh3, que é a barreira contra XSS.
    return mark_safe(renderizar(texto))  # noqa: S308
