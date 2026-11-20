from typing import cast

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from pydantic import BaseModel

from apps.core.acesso import superusuario_requerido
from apps.core.tabela import consulta_da_listagem
from apps.faq.models import Faq as FaqModel
from apps.user_admin.models import Perfil
from services.domain.faq import Editor, PerguntaJaRespondida, Situacao
from services.domain.listagem_gestao import ColunaFaq

from .cadastro import alterar_situacao, excluir_faq, restaurar_faq
from .consulta import faq_editavel
from .context import (
    contexto_corpo,
    contexto_formulario,
    contexto_lista,
    pergunta_principal,
    pode_excluir_registro,
)
from .formularios import (
    CONTROLE_NOVOS_ANEXOS,
    PREFIXO_VARIACAO,
    LinkNoFormulario,
    ValoresFaq,
    VariacaoNoFormulario,
    novo_sufixo,
    salvar_faq_existente,
    salvar_faq_nova,
    valores_do_post,
    valores_do_registro,
)

TEMPLATE_LISTA = "faq/gestao/lista.html"
TEMPLATE_CORPO = "faq/partials/gestao/_corpo_faqs.html"
TEMPLATE_PAGINA_FORMULARIO = "faq/gestao/formulario.html"
TEMPLATE_FORMULARIO = "faq/partials/gestao/_formulario_faq.html"
TEMPLATE_MODAL_EXCLUIR = "faq/partials/gestao/_modal_excluir.html"
TEMPLATE_AVISO_LISTA = "faq/partials/gestao/_aviso_lista.html"
TEMPLATE_SECAO_PERGUNTAS = "faq/partials/gestao/_secao_perguntas.html"
TEMPLATE_SECAO_LINKS = "faq/partials/gestao/_secao_links.html"
TEMPLATE_SECAO_RELACIONADAS = "faq/partials/gestao/_secao_relacionadas.html"
# A tabela escuta este evento para se recarregar com os filtros em vigor depois de excluir ou restaurar.
EVENTO_FAQS_ALTERADAS = "faqs-alteradas"


class PedidoListaFaqs(BaseModel):
    excluidas: bool = False


class PedidoSituacao(BaseModel):
    situacao: Situacao


@superusuario_requerido
def lista(request: HttpRequest) -> HttpResponse:
    consulta = consulta_da_listagem(request.GET.dict(), ColunaFaq)
    excluidas = PedidoListaFaqs.model_validate(request.GET.dict()).excluidas
    return render(request, TEMPLATE_LISTA, contexto_lista(consulta, excluidas))


@superusuario_requerido
def corpo(request: HttpRequest) -> HttpResponse:
    consulta = consulta_da_listagem(request.GET.dict(), ColunaFaq)
    excluidas = PedidoListaFaqs.model_validate(request.GET.dict()).excluidas
    return render(request, TEMPLATE_CORPO, contexto_corpo(consulta, excluidas))


@superusuario_requerido
@require_http_methods(["GET", "POST"])
def nova(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        return render(
            request, TEMPLATE_PAGINA_FORMULARIO, contexto_formulario(ValoresFaq())
        )
    valores = valores_do_post(request.POST)
    desfecho = salvar_faq_nova(
        valores, _editor(request), request.FILES.getlist(CONTROLE_NOVOS_ANEXOS)
    )
    if not isinstance(desfecho, int):
        return render(
            request,
            TEMPLATE_FORMULARIO,
            contexto_formulario(valores, recusa=desfecho),
            status=422,
        )
    return _para_a_lista()


@superusuario_requerido
@require_http_methods(["GET", "POST"])
def editar(request: HttpRequest, faq_id: int) -> HttpResponse:
    registro = faq_editavel(faq_id)
    if request.method == "GET":
        return render(
            request,
            TEMPLATE_PAGINA_FORMULARIO,
            contexto_formulario(valores_do_registro(registro), registro),
        )
    valores = valores_do_post(request.POST)
    desfecho = salvar_faq_existente(
        valores,
        registro,
        _editor(request),
        request.FILES.getlist(CONTROLE_NOVOS_ANEXOS),
    )
    if not isinstance(desfecho, int):
        return render(
            request,
            TEMPLATE_FORMULARIO,
            contexto_formulario(valores, registro, recusa=desfecho),
            status=422,
        )
    return _para_a_lista()


@superusuario_requerido
@require_POST
def situacao(request: HttpRequest, faq_id: int) -> HttpResponse:
    pedido = PedidoSituacao.model_validate(request.POST.dict())
    alterar_situacao(faq_id, pedido.situacao, _editor(request))
    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


@superusuario_requerido
@require_http_methods(["GET", "POST"])
def excluir(request: HttpRequest, faq_id: int) -> HttpResponse:
    if request.method == "GET":
        registro = faq_editavel(faq_id)
        return render(
            request,
            TEMPLATE_MODAL_EXCLUIR,
            {
                "registro": registro,
                "pergunta": pergunta_principal(registro),
                "pode_excluir": pode_excluir_registro(registro),
            },
        )
    excluir_faq(faq_id, _editor(request))
    # Corpo vazio fecha o modal; a tabela se recarrega com os filtros que já estavam na tela.
    return HttpResponse(headers={"HX-Trigger": EVENTO_FAQS_ALTERADAS})


@superusuario_requerido
@require_POST
def restaurar(request: HttpRequest, faq_id: int) -> HttpResponse:
    try:
        restaurar_faq(faq_id, _editor(request))
    except PerguntaJaRespondida as erro:
        mensagens = [
            f"A pergunta “{o.pergunta.texto}” já é respondida por outra FAQ."
            for o in erro.ocupadas
        ]
        return render(
            request, TEMPLATE_AVISO_LISTA, {"mensagens": mensagens}, status=409
        )
    resposta = render(request, TEMPLATE_AVISO_LISTA, {})
    resposta["HX-Trigger"] = EVENTO_FAQS_ALTERADAS
    return resposta


@superusuario_requerido
def bloco_perguntas(request: HttpRequest) -> HttpResponse:
    # Adicionar e remover linha redesenham o bloco no servidor, com o que já estava digitado.
    valores = valores_do_post(request.GET)
    variacoes = [
        v for v in valores.variacoes if v.controle != request.GET.get("remover")
    ]
    if request.GET.get("adicionar"):
        variacoes.append(
            VariacaoNoFormulario(controle=f"{PREFIXO_VARIACAO}{novo_sufixo()}")
        )
    valores = valores.model_copy(update={"variacoes": variacoes})
    return render(request, TEMPLATE_SECAO_PERGUNTAS, {"valores": valores, "realce": {}})


@superusuario_requerido
def bloco_links(request: HttpRequest) -> HttpResponse:
    valores = valores_do_post(request.GET)
    links = [
        link for link in valores.links if link.sufixo != request.GET.get("remover")
    ]
    if request.GET.get("adicionar"):
        links.append(LinkNoFormulario(sufixo=novo_sufixo()))
    valores = valores.model_copy(update={"links": links})
    return render(request, TEMPLATE_SECAO_LINKS, {"valores": valores, "realce": {}})


@superusuario_requerido
def bloco_relacionadas(request: HttpRequest) -> HttpResponse:
    valores = valores_do_post(request.GET)
    ids = [
        i
        for i in valores.relacionadas_ids
        if str(i) != request.GET.get("desrelacionar")
    ]
    relacionar = request.GET.get("relacionar", "")
    if relacionar.isdigit() and int(relacionar) not in ids:
        ids.append(int(relacionar))
    faq = request.GET.get("faq", "")
    registro = FaqModel.objects.filter(pk=int(faq)).first() if faq.isdigit() else None
    valores = valores.model_copy(update={"relacionadas_ids": ids})
    contexto = contexto_formulario(valores, registro)
    return render(request, TEMPLATE_SECAO_RELACIONADAS, contexto)


def _editor(request: HttpRequest) -> Editor:
    return Editor(perfil_id=cast(Perfil, request.user).pk)


def _para_a_lista() -> HttpResponse:
    return HttpResponse(status=204, headers={"HX-Redirect": reverse("faq:admin_lista")})
