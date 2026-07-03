from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.logradouro_matcher.schemas import LogradouroSelection
from apps.search.secoes import SecaoResultado
from services.domain.codlog_match import CodlogMatchInput, match_codlog
from services.domain.logradouros_match import LiteralLogradouroQuery, match_logradouro_literal
from services.domain.roteamento_busca import CodlogParse, LogradouroParse

TITULO_LOGRADOURO_NOME = "Logradouro (por nome)"


def secao_codlog(candidato: CodlogParse) -> SecaoResultado | None:
    dto = CodlogMatchInput(
        input_codlog=candidato.codlog,
        digito_verificador=candidato.digito_verificador or None,
    )
    resultados = match_codlog(dto)
    if not resultados:
        return None  # seção OMITIDA: sem match não polui a UX
    html = render_to_string(
        "logradouro_matcher/partials/resultados_codlog.html",
        {"resultados": resultados},
    )
    return SecaoResultado(titulo="Logradouro (por codlog)", html=html)


def secao_logradouro(candidato: LogradouroParse) -> SecaoResultado | None:
    dto = LiteralLogradouroQuery(
        nome=candidato.nome,
        tipo=candidato.tipo_logradouro or None,
    )
    resultado = match_logradouro_literal(dto)
    if not resultado.logradouros:
        return None  # seção OMITIDA: sem match não polui a UX
    html = render_to_string(
        "logradouro_matcher/partials/resultados_logradouro.html",
        {"resultado": resultado},
    )
    return SecaoResultado(titulo=TITULO_LOGRADOURO_NOME, html=html)


@require_POST
def selecionar(request: HttpRequest) -> HttpResponse:
    selecao = LogradouroSelection(
        codlog=request.POST.get("codlog", ""),
        digito_verificador=request.POST.get("digito_verificador", ""),
    )
    print(f"[SELEÇÃO] tipo=logradouro {selecao!r}")
    return render(request, "logradouro_matcher/partials/_selecao.html", {"selecao": selecao})
