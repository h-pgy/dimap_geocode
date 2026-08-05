"""
Páginas administrativas de servidor (SPEC user_admin/007): criar e editar renderizam o mesmo
organismo sobre o fundo administrativo. Só leitura — gravar servidor é ato administrativo e entra
com autenticação, autorização por perfil e registro da execução na SPEC seguinte (§3.5).
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.user_admin.context import contexto_criar_perfil, contexto_editar_perfil
from apps.user_admin.models import Perfil

TEMPLATE_FORMULARIO = "user_admin/perfil_form.html"


def criar_perfil(request: HttpRequest) -> HttpResponse:
    return render(request, TEMPLATE_FORMULARIO, contexto_criar_perfil())


def editar_perfil(request: HttpRequest, pk: int) -> HttpResponse:
    perfil = get_object_or_404(
        Perfil.objects.select_related("unidade", "cargo_base", "cargo_comissao"),
        pk=pk,
    )
    return render(request, TEMPLATE_FORMULARIO, contexto_editar_perfil(perfil))
