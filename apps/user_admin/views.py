"""
Páginas administrativas de servidor (SPEC user_admin/007), de unidade (SPEC user_admin/012), a
listagem de servidores (SPEC user_admin/013), a página própria da unidade (SPEC user_admin/016) e a
página própria do servidor (SPEC user_admin/017): criar servidor e criar unidade seguem em
formulário aberto; ver um servidor ou uma unidade é página, e editar os dois é modal, buscado por
rota própria. Só leitura — gravar é ato administrativo e entra com autenticação, autorização por
perfil e registro da execução no épico de ações (§3.5); os modais renderizam sem destino de submit.

As rotas de leitura nascem ABERTAS, exceção declarada nas SPECs 013, 016 e 017 nos termos do §3.5: a
proteção por perfil de administrador entra com a SPEC de autenticação.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.user_admin.context import (
    contexto_corpo_servidores,
    contexto_corpo_unidades,
    contexto_cor_sugerida,
    contexto_criar_perfil,
    contexto_criar_unidade,
    contexto_listagem_servidores,
    contexto_listagem_unidades,
    contexto_modal_perfil,
    contexto_organograma,
    contexto_pagina_perfil,
    contexto_unidade,
)
from apps.user_admin.models import Perfil, Unidade
from apps.user_admin.schemas import SelecaoUnidadePai
from services.domain.listagem_gestao import (
    ColunaServidor,
    ColunaUnidade,
    ConsultaServidores,
    ConsultaUnidades,
)

TEMPLATE_FORMULARIO = "user_admin/perfil_form.html"
TEMPLATE_PAGINA_PERFIL = "user_admin/perfil.html"
TEMPLATE_MODAL_PERFIL = "user_admin/partials/_modal_editar_perfil.html"
TEMPLATE_UNIDADE = "user_admin/unidade_form.html"
TEMPLATE_PAGINA_UNIDADE = "user_admin/unidade.html"
TEMPLATE_CAMPO_COR = "user_admin/partials/_campo_cor_unidade.html"
TEMPLATE_LISTAGEM = "user_admin/servidores_list.html"
TEMPLATE_CORPO_SERVIDORES = "user_admin/partials/_corpo_servidores.html"
TEMPLATE_LISTAGEM_UNIDADES = "user_admin/unidades_list.html"
TEMPLATE_CORPO_UNIDADES = "user_admin/partials/_corpo_unidades.html"
TEMPLATE_ARVORE = "user_admin/arvore_unidades.html"


def listar_servidores(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaServidores.de_parametros(request.GET.dict(), ColunaServidor)
    return render(request, TEMPLATE_LISTAGEM, contexto_listagem_servidores(consulta))


def corpo_servidores(request: HttpRequest) -> HttpResponse:
    # Alvo do swap do HTMX: só o <tbody>. Trocar o <thead> junto destruiria, a cada tecla, o campo
    # em que se está digitando.
    consulta = ConsultaServidores.de_parametros(request.GET.dict(), ColunaServidor)
    return render(request, TEMPLATE_CORPO_SERVIDORES, contexto_corpo_servidores(consulta))


def listar_unidades(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaUnidades.de_parametros(request.GET.dict(), ColunaUnidade)
    foco_param = request.GET.get("foco")
    unidade_em_foco = None
    if foco_param and foco_param.isdigit():
        unidade_em_foco = Unidade.objects.filter(pk=int(foco_param)).first()
    return render(
        request,
        TEMPLATE_LISTAGEM_UNIDADES,
        contexto_listagem_unidades(consulta, unidade_em_foco),
    )


def corpo_unidades(request: HttpRequest) -> HttpResponse:
    # Alvo do swap do HTMX: só o <tbody> da tabela de unidades.
    consulta = ConsultaUnidades.de_parametros(request.GET.dict(), ColunaUnidade)
    return render(request, TEMPLATE_CORPO_UNIDADES, contexto_corpo_unidades(consulta))


def criar_perfil(request: HttpRequest) -> HttpResponse:
    return render(request, TEMPLATE_FORMULARIO, contexto_criar_perfil())


def pagina_perfil(request: HttpRequest, pk: int) -> HttpResponse:
    return render(request, TEMPLATE_PAGINA_PERFIL, contexto_pagina_perfil(_perfil(pk)))


def editar_perfil(request: HttpRequest, pk: int) -> HttpResponse:
    # Só o partial do modal: a página de leitura não o carrega, e os catálogos dos selects só são
    # consultados quando alguém abre o lápis.
    return render(request, TEMPLATE_MODAL_PERFIL, contexto_modal_perfil(_perfil(pk)))


def _perfil(pk: int) -> Perfil:
    return get_object_or_404(
        Perfil.objects.select_related("unidade", "cargo_base", "cargo_comissao"),
        pk=pk,
    )


def criar_unidade(request: HttpRequest) -> HttpResponse:
    return render(request, TEMPLATE_UNIDADE, contexto_criar_unidade())


def cor_sugerida_unidade(request: HttpRequest) -> HttpResponse:
    selecao = SelecaoUnidadePai.model_validate(request.GET.dict())
    return render(request, TEMPLATE_CAMPO_COR, contexto_cor_sugerida(selecao.pai))


def pagina_unidade(request: HttpRequest, pk: int) -> HttpResponse:
    unidade = get_object_or_404(Unidade.objects.select_related("tipo", "pai"), pk=pk)
    return render(request, TEMPLATE_PAGINA_UNIDADE, contexto_unidade(unidade))


def arvore_de_unidades(request: HttpRequest) -> HttpResponse:
    """Redireciona para a listagem de unidades com organograma integrado (SPEC user_admin/019)."""
    return redirect("user_admin:listar_unidades")
