from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.address_geocoder.schemas import EnderecoSelection
from apps.search.secoes import SecaoResultado
from services.domain.codlog_match import CodlogMatchInput, match_codlog
from services.domain.logradouros_match import LiteralLogradouroQuery, match_logradouro_literal
from services.domain.roteamento_busca import EnderecoCodlogParse, EnderecoParse

TITULO_ENDERECO_CODLOG = "Endereço (por codlog)"
TITULO_ENDERECO_NOME = "Endereço (por nome)"


def secao_endereco_codlog(candidato: EnderecoCodlogParse) -> SecaoResultado:
    dto = CodlogMatchInput(
        input_codlog=candidato.codlog.codlog,
        digito_verificador=candidato.codlog.digito_verificador or None,
    )
    html = render_to_string(
        "address_geocoder/partials/resultados_endereco_codlog.html",
        {"resultados": match_codlog(dto), "numero": candidato.numero},
    )
    return SecaoResultado(titulo=TITULO_ENDERECO_CODLOG, html=html)


def secao_endereco(candidato: EnderecoParse) -> SecaoResultado:
    dto = LiteralLogradouroQuery(
        nome=candidato.logradouro.nome,
        tipo=candidato.logradouro.tipo_logradouro or None,
    )
    html = render_to_string(
        "address_geocoder/partials/resultados_endereco_nome.html",
        {"resultado": match_logradouro_literal(dto), "numero": candidato.numero},
    )
    return SecaoResultado(titulo=TITULO_ENDERECO_NOME, html=html)


@require_POST
def selecionar(request: HttpRequest) -> HttpResponse:
    selecao = EnderecoSelection(
        codlog=request.POST.get("codlog", ""),
        numero=request.POST.get("numero", ""),
    )
    print(f"[SELEÇÃO] tipo=endereço {selecao!r}")
    return render(request, "address_geocoder/partials/_selecao.html", {"selecao": selecao})
