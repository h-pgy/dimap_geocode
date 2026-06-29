from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.lote_matcher.schemas import LoteSelection
from apps.search.secoes import SecaoResultado
from services.domain.contribuinte_match import ContribuinteMatchInput, match_contribuinte
from services.domain.roteamento_busca import ContribuinteParse

TITULO_CONTRIBUINTE = "Lote (por nº de contribuinte)"


def _render_contribuinte(dto: ContribuinteMatchInput) -> str:
    resultados = match_contribuinte(dto)
    return render_to_string(
        "lote_matcher/partials/resultados_contribuinte.html",
        {"resultados": resultados},
    )


def secao_contribuinte(candidato: ContribuinteParse) -> SecaoResultado:
    dto = ContribuinteMatchInput(
        setor=candidato.setor,
        quadra=candidato.quadra or None,
        lote=candidato.lote or None,
        dv=candidato.dv or None,
    )
    return SecaoResultado(titulo=TITULO_CONTRIBUINTE, html=_render_contribuinte(dto))


@require_POST
def selecionar(request: HttpRequest) -> HttpResponse:
    selecao = LoteSelection(
        setor=request.POST.get("setor", ""),
        quadra=request.POST.get("quadra", ""),
        lote=request.POST.get("lote", ""),
        dv=request.POST.get("dv") or None,
    )
    print(f"[SELEÇÃO] tipo=lote {selecao!r}")
    return render(request, "lote_matcher/partials/_selecao.html", {"selecao": selecao})
