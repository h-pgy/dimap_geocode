from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.address_geocoder.schemas import EnderecoSelection


@require_POST
def selecionar(request: HttpRequest) -> HttpResponse:
    selecao = EnderecoSelection(
        codlog=request.POST.get("codlog", ""),
        numero=request.POST.get("numero", ""),
    )
    print(f"[SELEÇÃO] tipo=endereço {selecao!r}")
    return render(request, "address_geocoder/partials/_selecao.html", {"selecao": selecao})
