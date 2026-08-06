"""
Páginas administrativas de servidor (SPEC user_admin/007) e de unidade (SPEC user_admin/012):
criar e editar renderizam o mesmo organismo sobre o fundo administrativo. Só leitura — gravar é
ato administrativo e entra com autenticação, autorização por perfil e registro da execução na SPEC
seguinte (§3.5).
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.user_admin.context import (
    contexto_cor_sugerida,
    contexto_criar_perfil,
    contexto_criar_unidade,
    contexto_editar_perfil,
)
from apps.user_admin.models import Perfil
from apps.user_admin.schemas import SelecaoUnidadePai

TEMPLATE_FORMULARIO = "user_admin/perfil_form.html"
TEMPLATE_UNIDADE = "user_admin/unidade_form.html"
TEMPLATE_CAMPO_COR = "user_admin/partials/_campo_cor_unidade.html"


def criar_perfil(request: HttpRequest) -> HttpResponse:
    return render(request, TEMPLATE_FORMULARIO, contexto_criar_perfil())


def editar_perfil(request: HttpRequest, pk: int) -> HttpResponse:
    perfil = get_object_or_404(
        Perfil.objects.select_related("unidade", "cargo_base", "cargo_comissao"),
        pk=pk,
    )
    return render(request, TEMPLATE_FORMULARIO, contexto_editar_perfil(perfil))


def criar_unidade(request: HttpRequest) -> HttpResponse:
    return render(request, TEMPLATE_UNIDADE, contexto_criar_unidade())


def cor_sugerida_unidade(request: HttpRequest) -> HttpResponse:
    selecao = SelecaoUnidadePai.model_validate(request.GET.dict())
    return render(request, TEMPLATE_CAMPO_COR, contexto_cor_sugerida(selecao.pai))
