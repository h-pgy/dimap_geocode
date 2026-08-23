"""
Páginas administrativas de servidor (SPEC user_admin/007), a listagem de servidores
(SPEC user_admin/013), a página própria do servidor (SPEC user_admin/017), o cadastro de servidor
(SPEC criacao_usuarios/004) e a edição dele (SPEC criacao_usuarios/005): ver um servidor é página
e editar é modal, buscado por rota própria. Criar e editar servidor são atos administrativos —
`criar_perfil`/`editar_perfil` só abrem a tela, e são `gravar_servidor`/`gravar_edicao` quem
gravam (§3.5).

As rotas de LEITURA de servidor nascem ABERTAS, exceção declarada nas SPECs 013 e 017 nos termos
do §3.5: a proteção por perfil de administrador entra com a SPEC de autenticação.
"""

from typing import cast

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.competencias.consulta import alcance_do_perfil
from apps.competencias.protecao import acao_protegida, pode_executar, registrar_ato
from apps.user_admin.acoes_declaradas import ACAO_CRIAR_SERVIDOR, ACAO_EDITAR_SERVIDOR
from apps.user_admin.cadastro import criar_servidor, editar_servidor
from apps.user_admin.context import (
    contexto_cadastro_concluido,
    contexto_cadastro_recusado,
    contexto_corpo_servidores,
    contexto_criar_perfil,
    contexto_edicao_recusada,
    contexto_listagem_servidores,
    contexto_modal_perfil,
    contexto_pagina_perfil,
)
from apps.user_admin.models import Perfil
from apps.user_admin.schemas import consulta_de_servidores

TEMPLATE_FORMULARIO = "user_admin/perfil_form.html"
TEMPLATE_FORMULARIO_RECUSADO = "user_admin/partials/_formulario_servidor.html"
TEMPLATE_CADASTRO_CONCLUIDO = "user_admin/partials/_cadastro_concluido.html"
TEMPLATE_PAGINA_PERFIL = "user_admin/perfil.html"
TEMPLATE_MODAL_PERFIL = "user_admin/partials/_modal_editar_perfil.html"
TEMPLATE_EDICAO_CONCLUIDA = "user_admin/partials/_edicao_concluida.html"
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


@acao_protegida(ACAO_CRIAR_SERVIDOR)
def criar_perfil(request: HttpRequest) -> HttpResponse:
    # Oferecer o que o decorator vai recusar no POST é convidar ao 403: a lista sai do mesmo
    # alcance que a barreira confere.
    return render(request, TEMPLATE_FORMULARIO, contexto_criar_perfil(alcance_do_perfil(_autor(request))))


@acao_protegida(ACAO_CRIAR_SERVIDOR)
@require_POST
def gravar_servidor(request: HttpRequest) -> HttpResponse:
    # A view traduz nome de controle em nome de campo e NÃO constrói o DTO: quem o constrói é o
    # ato, porque a recusa dele volta como o próprio formulário, não como página de erro (SPEC
    # formularios/001). `.get(..., "")` porque só `unidade` tem rede — o decorator já devolve 400
    # quando ela falta; nos demais, chave ausente daria 500 justamente na rota que existe para
    # transformar entrada ruim em recusa na tela.
    valores = {
        "rf": request.POST.get("rf", ""),
        "nome": request.POST.get("nome", ""),
        "sobrenome": request.POST.get("sobrenome", ""),
        "email": request.POST.get("email", ""),
        "unidade_id": request.POST.get("unidade", ""),
        "cargo_base_id": request.POST.get("cargo_base", ""),
        "cargo_comissao_id": request.POST.get("cargo_comissao", ""),
        # O host de onde o convite parte é da orquestração, não do formulário.
        "url_acesso": request.build_absolute_uri("/"),
    }
    desfecho = criar_servidor(valores, foto=request.FILES.get("foto"))
    if desfecho.perfil is None:
        return render(
            request,
            TEMPLATE_FORMULARIO_RECUSADO,
            contexto_cadastro_recusado(
                valores,
                desfecho.recusa,
                alcance_do_perfil(_autor(request)),
            ),
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
    """Rota aberta de leitura (SPEC user_admin/017). O que a autorização decide aqui é um botão."""
    perfil = _perfil(pk)
    return render(
        request,
        TEMPLATE_PAGINA_PERFIL,
        contexto_pagina_perfil(perfil)
        | {"pode_editar": pode_executar(request.user, ACAO_EDITAR_SERVIDOR, perfil.unidade_id)},
    )


@acao_protegida(ACAO_EDITAR_SERVIDOR)
def editar_perfil(request: HttpRequest, servidor: int) -> HttpResponse:
    # Só o partial do modal: a página de leitura não o carrega, e os catálogos dos selects só são
    # consultados quando alguém abre o lápis. Nenhuma conferência de lotação escrita aqui: o
    # contrato da ação declara o alcance pela pessoa, e o decorator já resolveu a unidade dela.
    # Oferecer destino que o decorator vai recusar no POST é convidar ao 403 — que o HTMX não troca
    # na tela: a lista sai do mesmo alcance que a barreira confere, como em `criar_perfil`.
    return render(
        request,
        TEMPLATE_MODAL_PERFIL,
        contexto_modal_perfil(_perfil(servidor), alcance_do_perfil(_autor(request))),
    )


@acao_protegida(ACAO_EDITAR_SERVIDOR)
@require_POST
def gravar_edicao(request: HttpRequest, servidor: int) -> HttpResponse:
    # A view traduz nome de controle em nome de campo e NÃO constrói o DTO: quem o constrói é o
    # ato, porque a recusa dele volta como o próprio modal (SPEC formularios/001). `.get(..., "")`
    # porque só `unidade` tem rede — o decorator já devolve 400 quando ela falta; nos demais, chave
    # ausente daria 500 na rota que existe para transformar entrada ruim em recusa na tela.
    valores = {
        # Do caminho da rota, nunca do corpo: é o mesmo id que o decorator conferiu.
        "servidor_id": servidor,
        "rf": request.POST.get("rf", ""),
        "nome": request.POST.get("nome", ""),
        "sobrenome": request.POST.get("sobrenome", ""),
        "email": request.POST.get("email", ""),
        "unidade_id": request.POST.get("unidade", ""),
        "cargo_base_id": request.POST.get("cargo_base", ""),
        "cargo_comissao_id": request.POST.get("cargo_comissao", ""),
    }
    desfecho = editar_servidor(valores, foto=request.FILES.get("foto"))
    if desfecho.perfil is None:
        return render(
            request,
            TEMPLATE_MODAL_PERFIL,
            contexto_edicao_recusada(
                _perfil(servidor),
                alcance_do_perfil(_autor(request)),
                valores,
                desfecho.recusa,
            ),
            status=422,
        )
    registrar_ato(
        request,
        operacao="editar",
        alvo_tipo="servidor",
        alvo_identificador=desfecho.perfil.rf,
    )
    # O poço volta vazio — é assim que o modal fecha — e a página se atualiza pelo swap fora de
    # banda que o partial carrega.
    return render(request, TEMPLATE_EDICAO_CONCLUIDA, contexto_pagina_perfil(desfecho.perfil))


def _perfil(pk: int) -> Perfil:
    return get_object_or_404(
        Perfil.objects.select_related("unidade", "cargo_base", "cargo_comissao"),
        pk=pk,
    )


def _autor(request: HttpRequest) -> Perfil:
    # AUTH_USER_MODEL é Perfil: autenticado aqui É um Perfil — o decorator já barrou o anônimo.
    return cast(Perfil, request.user)
