from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from services.domain.codlog_match import CodlogMatchInput, match_codlog


@require_POST
def buscar_codlog(request: HttpRequest) -> HttpResponse:
    dto = CodlogMatchInput.model_validate(request.POST.dict())
    resultados = match_codlog(dto)
    return render(
        request,
        "logradouro_matcher/partials/resultados_codlog.html",
        {"resultados": resultados},
    )
