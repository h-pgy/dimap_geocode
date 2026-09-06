"""Expõe `apps.core.navegacao` como filtro de template — a lógica de origem mora num só lugar, o
partial que a consome (`templates/partials/_botao_voltar_painel.html`), não em cada view que o
inclui."""

from django.http import HttpRequest
from django.template import Library

from apps.core.navegacao import veio_do_painel as _veio_do_painel

register = Library()


@register.filter(name="veio_do_painel")
def veio_do_painel(request: HttpRequest) -> bool:
    return _veio_do_painel(request)
