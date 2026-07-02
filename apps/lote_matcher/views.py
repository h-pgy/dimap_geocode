from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.lote_matcher.schemas import LoteSelection
from apps.search.secoes import SecaoResultado
from services.domain.codlog_match import CodlogMatchInput, match_codlog
from services.domain.contribuinte_match import (
    ContribuinteMatchInput,
    EnderecoFiscalMatchInput,
    match_contribuinte,
    match_endereco_fiscal,
)
from services.domain.logradouros_match import LiteralLogradouroQuery, match_logradouro_literal
from services.domain.roteamento_busca import ContribuinteParse, EnderecoLoteParse

TITULO_CONTRIBUINTE = "Lote (por nº de contribuinte)"
TITULO_ENDERECO_LOTE = "Endereço cadastrado (lote)"


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


def _resolver_codlogs(candidato: EnderecoLoteParse) -> list[str]:
    """Resolve a entrada para codlogs (5 dígitos) — mesma tabela da SPEC 009."""
    if candidato.codlog is not None:
        resultados = match_codlog(
            CodlogMatchInput(
                input_codlog=candidato.codlog.codlog,
                digito_verificador=candidato.codlog.digito_verificador or None,
            )
        )
        return [r.codlog for r in resultados]
    assert candidato.logradouro is not None  # exclusividade garantida pelo model_validator
    resultado = match_logradouro_literal(
        LiteralLogradouroQuery(
            nome=candidato.logradouro.nome,
            tipo=candidato.logradouro.tipo_logradouro or None,
        )
    )
    return [m.codlog for m in resultado.logradouros]


def secao_endereco_lote(candidato: EnderecoLoteParse) -> SecaoResultado | None:
    codlogs = _resolver_codlogs(candidato)  # nome → match_logradouro_literal; codlog → match_codlog
    if not codlogs:
        return None
    resultados = match_endereco_fiscal(
        EnderecoFiscalMatchInput(codlogs=codlogs, numero_padronizado=candidato.numero_padronizado)
    )
    if not resultados:
        return None  # seção OMITIDA: candidato especulativo sem match não polui a UX
    html = render_to_string(
        "lote_matcher/partials/resultados_endereco_lote.html", {"resultados": resultados}
    )
    return SecaoResultado(titulo=TITULO_ENDERECO_LOTE, html=html)


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
