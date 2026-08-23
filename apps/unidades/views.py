"""
Páginas de unidade: o formulário de cadastro (SPEC user_admin/012), a página própria
(SPEC user_admin/016) e o organograma (SPEC user_admin/018).

As rotas de LEITURA nascem ABERTAS, exceção declarada nas SPECs 016 e 018 nos termos do §3.5: a
proteção por perfil de administrador entra com a SPEC de autenticação.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.unidades.context import (
    contexto_cor_sugerida,
    contexto_criar_unidade,
    contexto_organograma,
    contexto_unidade,
)
from apps.unidades.models import Unidade
from apps.unidades.schemas import SelecaoUnidadePai

TEMPLATE_UNIDADE = "unidades/unidade_form.html"
TEMPLATE_PAGINA_UNIDADE = "unidades/unidade.html"
TEMPLATE_CAMPO_COR = "unidades/partials/_campo_cor_unidade.html"
TEMPLATE_ARVORE = "unidades/arvore_unidades.html"


def criar_unidade(request: HttpRequest) -> HttpResponse:
    return render(request, TEMPLATE_UNIDADE, contexto_criar_unidade())


def cor_sugerida_unidade(request: HttpRequest) -> HttpResponse:
    selecao = SelecaoUnidadePai.model_validate(request.GET.dict())
    return render(request, TEMPLATE_CAMPO_COR, contexto_cor_sugerida(selecao.pai))


def pagina_unidade(request: HttpRequest, pk: int) -> HttpResponse:
    unidade = get_object_or_404(Unidade.objects.select_related("tipo", "pai"), pk=pk)
    return render(request, TEMPLATE_PAGINA_UNIDADE, contexto_unidade(unidade))


def arvore_de_unidades(request: HttpRequest) -> HttpResponse:
    """Rota de leitura, como a página da unidade. Sem unidade em foco: a página do organograma
    abre no topo."""
    return render(request, TEMPLATE_ARVORE, contexto_organograma(None))
