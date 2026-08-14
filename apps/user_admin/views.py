"""
Páginas administrativas de servidor (SPEC user_admin/007), de unidade (SPEC user_admin/012), a
listagem de servidores (SPEC user_admin/013) e a página própria da unidade (SPEC user_admin/016):
criar e editar renderizam o mesmo organismo sobre o fundo administrativo. Só leitura — gravar é ato
administrativo e entra com autenticação, autorização por perfil e registro da execução no épico de
ações (§3.5); os modais de titularidade da página da unidade renderizam sem destino de submit.

A rota da listagem e a da página da unidade nascem ABERTAS, exceção declarada nas SPECs 013 e 016
nos termos do §3.5: a proteção por perfil de administrador entra com a SPEC de autenticação.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.user_admin.context import (
    contexto_corpo_servidores,
    contexto_cor_sugerida,
    contexto_criar_perfil,
    contexto_criar_unidade,
    contexto_editar_perfil,
    contexto_listagem_servidores,
    contexto_unidade,
)
from apps.user_admin.models import Perfil, Unidade
from apps.user_admin.schemas import SelecaoUnidadePai, consulta_de_servidores

TEMPLATE_FORMULARIO = "user_admin/perfil_form.html"
TEMPLATE_UNIDADE = "user_admin/unidade_form.html"
TEMPLATE_PAGINA_UNIDADE = "user_admin/unidade.html"
TEMPLATE_CAMPO_COR = "user_admin/partials/_campo_cor_unidade.html"
TEMPLATE_LISTAGEM = "user_admin/servidores_list.html"
TEMPLATE_CORPO_SERVIDORES = "user_admin/partials/_corpo_servidores.html"


def listar_servidores(request: HttpRequest) -> HttpResponse:
    consulta = consulta_de_servidores(request.GET.dict())
    return render(request, TEMPLATE_LISTAGEM, contexto_listagem_servidores(consulta))


def corpo_servidores(request: HttpRequest) -> HttpResponse:
    # Alvo do swap do HTMX: só o <tbody>. Trocar o <thead> junto destruiria, a cada tecla, o campo
    # em que se está digitando.
    consulta = consulta_de_servidores(request.GET.dict())
    return render(request, TEMPLATE_CORPO_SERVIDORES, contexto_corpo_servidores(consulta))


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


def pagina_unidade(request: HttpRequest, pk: int) -> HttpResponse:
    unidade = get_object_or_404(Unidade.objects.select_related("tipo", "pai"), pk=pk)
    return render(request, TEMPLATE_PAGINA_UNIDADE, contexto_unidade(unidade))
