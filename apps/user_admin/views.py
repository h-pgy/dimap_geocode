"""
Páginas administrativas de servidor (SPEC user_admin/007), de unidade (SPEC user_admin/012), a
listagem de servidores (SPEC user_admin/013), a página própria da unidade (SPEC user_admin/016), a
página própria do servidor (SPEC user_admin/017) e o cadastro de servidor (SPEC
criacao_usuarios/004): ver um servidor ou uma unidade é página, e editar os dois é modal, buscado
por rota própria. Criar unidade segue em formulário aberto; criar servidor é ato administrativo —
`criar_perfil` só abre a tela, e é `gravar_servidor` quem grava (§3.5).

As rotas de leitura de servidor e unidade nascem ABERTAS, exceção declarada nas SPECs 013, 016 e 017
nos termos do §3.5: a proteção por perfil de administrador entra com a SPEC de autenticação.
"""

from typing import cast

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.competencias.consulta import alcance_do_perfil
from apps.competencias.protecao import acao_protegida, registrar_ato
from apps.user_admin.acoes_declaradas import ACAO_CRIAR_SERVIDOR
from apps.user_admin.cadastro import criar_servidor
from apps.user_admin.context import (
    contexto_cadastro_concluido,
    contexto_cadastro_recusado,
    contexto_corpo_servidores,
    contexto_cor_sugerida,
    contexto_criar_perfil,
    contexto_criar_unidade,
    contexto_listagem_servidores,
    contexto_modal_perfil,
    contexto_organograma,
    contexto_pagina_perfil,
    contexto_unidade,
)
from apps.user_admin.models import Perfil, Unidade
from apps.user_admin.schemas import NovoServidor, SelecaoUnidadePai, consulta_de_servidores

TEMPLATE_FORMULARIO = "user_admin/perfil_form.html"
TEMPLATE_FORMULARIO_RECUSADO = "user_admin/partials/_formulario_servidor.html"
TEMPLATE_CADASTRO_CONCLUIDO = "user_admin/partials/_cadastro_concluido.html"
TEMPLATE_PAGINA_PERFIL = "user_admin/perfil.html"
TEMPLATE_MODAL_PERFIL = "user_admin/partials/_modal_editar_perfil.html"
TEMPLATE_UNIDADE = "user_admin/unidade_form.html"
TEMPLATE_PAGINA_UNIDADE = "user_admin/unidade.html"
TEMPLATE_CAMPO_COR = "user_admin/partials/_campo_cor_unidade.html"
TEMPLATE_LISTAGEM = "user_admin/servidores_list.html"
TEMPLATE_CORPO_SERVIDORES = "user_admin/partials/_corpo_servidores.html"
TEMPLATE_ARVORE = "user_admin/arvore_unidades.html"


def listar_servidores(request: HttpRequest) -> HttpResponse:
    consulta = consulta_de_servidores(request.GET.dict())
    return render(request, TEMPLATE_LISTAGEM, contexto_listagem_servidores(consulta))


def corpo_servidores(request: HttpRequest) -> HttpResponse:
    # Alvo do swap do HTMX: só o <tbody>. Trocar o <thead> junto destruiria, a cada tecla, o campo
    # em que se está digitando.
    consulta = consulta_de_servidores(request.GET.dict())
    return render(request, TEMPLATE_CORPO_SERVIDORES, contexto_corpo_servidores(consulta))


@acao_protegida(ACAO_CRIAR_SERVIDOR)
def criar_perfil(request: HttpRequest) -> HttpResponse:
    # Oferecer o que o decorator vai recusar no POST é convidar ao 403: a lista sai do mesmo
    # alcance que a barreira confere.
    return render(request, TEMPLATE_FORMULARIO, contexto_criar_perfil(alcance_do_perfil(_autor(request))))


@acao_protegida(ACAO_CRIAR_SERVIDOR)
@require_POST
def gravar_servidor(request: HttpRequest) -> HttpResponse:
    novo = NovoServidor(
        rf=request.POST["rf"],
        nome=request.POST["nome"],
        sobrenome=request.POST["sobrenome"],
        email=request.POST["email"],
        unidade_id=request.POST["unidade"],  # type: ignore[arg-type]
        cargo_base_id=request.POST["cargo_base"],  # type: ignore[arg-type]
        cargo_comissao_id=request.POST["cargo_comissao"],  # type: ignore[arg-type]
        # O host de onde o convite parte é da orquestração, não do formulário.
        url_acesso=request.build_absolute_uri("/"),  # type: ignore[arg-type]
    )
    desfecho = criar_servidor(novo, foto=request.FILES.get("foto"))
    if desfecho.perfil is None:
        return render(
            request,
            TEMPLATE_FORMULARIO_RECUSADO,
            contexto_cadastro_recusado(novo, desfecho.erros, alcance_do_perfil(_autor(request))),
            status=422,
        )
    # A view NUNCA grava a execução: deixa o recado e quem persiste é o decorator, depois do return.
    registrar_ato(
        request,
        operacao="criar",
        alvo_tipo="servidor",
        alvo_identificador=desfecho.perfil.rf,
    )
    return render(request, TEMPLATE_CADASTRO_CONCLUIDO, contexto_cadastro_concluido(desfecho.perfil))


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


def _autor(request: HttpRequest) -> Perfil:
    # AUTH_USER_MODEL é Perfil: autenticado aqui É um Perfil — o decorator já barrou o anônimo.
    return cast(Perfil, request.user)


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
