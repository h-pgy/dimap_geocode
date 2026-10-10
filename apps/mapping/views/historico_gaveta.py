from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from apps.mapping.context import contexto_aviso
from apps.mapping.historico_gaveta import (
    TEMPLATE_CENA,
    abrir_no_historico,
    contexto_cena,
    historico_da_sessao,
)
from apps.mapping.models import GavetaNaTela, PedidoDeCena

TEMPLATE_HISTORICO = "mapping/_historico_gaveta.html"
TEMPLATE_AVISO = "mapping/_aviso.html"

MSG_CENA_FORA_DO_HISTORICO = (
    "Esta gaveta saiu do histórico. Refaça a busca para abri-la de novo."
)


@require_GET
def historico_gaveta(request: HttpRequest) -> HttpResponse:
    """Rota aberta: lê só o histórico da sessão de quem pede."""
    na_tela = GavetaNaTela.model_validate(request.GET.dict())
    demais = historico_da_sessao(request.session).fora(na_tela.chave)
    return render(request, TEMPLATE_HISTORICO, {"demais": demais})


@require_POST
def devolver_cena(request: HttpRequest) -> HttpResponse:
    """Rota aberta: devolve só o que a sessão de quem pede guardou."""
    pedido = PedidoDeCena.model_validate(request.POST.dict())
    item = historico_da_sessao(request.session).de_chave(pedido.chave)
    # Sessão expirada, ou cena que saiu da lista por outra aba: aviso, e o mapa não muda.
    if item is None or item.cena is None:
        return render(request, TEMPLATE_AVISO, contexto_aviso(MSG_CENA_FORA_DO_HISTORICO))
    # A devolvida volta ao topo: é o que faz o voltar seguinte trazer a gaveta de onde se saiu.
    abrir_no_historico(request.session, item)
    return render(request, TEMPLATE_CENA, contexto_cena(item.cena))
