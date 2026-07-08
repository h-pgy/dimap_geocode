from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.lote_matcher.schemas import LoteSelection


@require_POST
def selecionar(request: HttpRequest) -> HttpResponse:
    selecao = LoteSelection(
        setor=request.POST.get("setor", ""),
        quadra=request.POST.get("quadra", ""),
        lote=request.POST.get("lote", ""),
        dv=request.POST.get("dv") or None,
        tipo_lote=request.POST.get("tipo_lote", ""),
    )
    print(f"[SELEÇÃO] tipo=lote tipo_lote={selecao.tipo_lote!r} {selecao!r}")
    return render(request, "lote_matcher/partials/_selecao.html", {"selecao": selecao})
