from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from services.utils.sorteio import sortear_diferente

from .context import ortofotos_disponiveis


def fundo_ortofoto(request: HttpRequest) -> HttpResponse:
    """Rota aberta (design/010 §3): a tela de login é anônima e mostra o mesmo fundo."""
    disponiveis = ortofotos_disponiveis()
    escolhida = sortear_diferente(disponiveis, request.GET.get("atual")) if disponiveis else None
    return render(
        request,
        "mapping/_camada_ortofoto.html",
        {"ortofoto_fundo": escolhida, "entrando": True},
    )
