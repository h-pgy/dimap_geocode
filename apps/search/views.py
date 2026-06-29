from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.address_geocoder.views import secao_endereco, secao_endereco_codlog
from apps.logradouro_matcher.views import secao_codlog, secao_logradouro
from apps.lote_matcher.views import secao_contribuinte
from apps.search.secoes import SecaoResultado
from services.domain.roteamento_busca import Candidato, RoteamentoQuery, TipoEntrada, rotear_entrada

SectionRenderer = Callable[..., SecaoResultado]

REGISTRO_SECOES: dict[TipoEntrada, SectionRenderer] = {
    TipoEntrada.CONTRIBUINTE: secao_contribuinte,
    TipoEntrada.ENDERECO_CODLOG: secao_endereco_codlog,
    TipoEntrada.ENDERECO: secao_endereco,
    TipoEntrada.CODLOG: secao_codlog,
    TipoEntrada.LOGRADOURO: secao_logradouro,
}


@require_POST
def rotear_busca(request: HttpRequest) -> HttpResponse:
    query = RoteamentoQuery(
        texto=request.POST.get("termo_pesquisa", ""),
        finished_typing=request.POST.get("tipo_evento") == "search",
    )
    result = rotear_entrada(query)
    secoes = [
        render_secao(candidato)
        for candidato in result.candidatos
        if (render_secao := REGISTRO_SECOES.get(candidato.tipo)) is not None
    ]
    return render(request, "search/partials/_sugestoes.html", {"secoes": secoes})
