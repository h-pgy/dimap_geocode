from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.logradouro_matcher.views import secao_codlog
from apps.search.secoes import SecaoResultado
from services.domain.roteamento_busca import Candidato, RoteamentoQuery, TipoEntrada, rotear_entrada

SectionRenderer = Callable[..., SecaoResultado]

REGISTRO_SECOES: dict[TipoEntrada, SectionRenderer] = {
    TipoEntrada.CODLOG: secao_codlog,
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
