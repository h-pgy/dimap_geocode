from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.search.secoes import SecaoResultado
from services.domain.codlog_match import CodlogMatchInput, match_codlog
from services.domain.roteamento_busca import CodlogParse


def _render_codlog(dto: CodlogMatchInput) -> str:
    resultados = match_codlog(dto)
    return render_to_string(
        "logradouro_matcher/partials/resultados_codlog.html",
        {"resultados": resultados},
    )


def secao_codlog(candidato: CodlogParse) -> SecaoResultado:
    dto = CodlogMatchInput(
        input_codlog=candidato.codlog,
        digito_verificador=candidato.digito_verificador or None,
    )
    return SecaoResultado(titulo="Logradouro (por codlog)", html=_render_codlog(dto))


@require_POST
def buscar_codlog(request: HttpRequest) -> HttpResponse:
    dto = CodlogMatchInput.model_validate(request.POST.dict())
    return HttpResponse(_render_codlog(dto))
