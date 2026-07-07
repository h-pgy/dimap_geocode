from collections.abc import Callable
from typing import TypeVar

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.address_geocoder.views import (
    geocodificar_endereco,
    secao_endereco,
    secao_endereco_codlog,
)
from apps.logradouro_geocoder.views import geocodificar_codlog
from apps.logradouro_matcher.views import secao_codlog, secao_logradouro
from apps.lote_geocoder.views import geocodificar_lote
from apps.lote_matcher.views import _resolver_codlogs, secao_contribuinte, secao_endereco_lote
from apps.mapping.context import contexto_aviso
from apps.search.secoes import SecaoResultado
from services.domain.codlog_match import CodlogMatchInput, match_codlog
from services.domain.contribuinte_match import (
    ContribuinteMatchInput,
    EnderecoFiscalMatchInput,
    match_contribuinte,
    match_endereco_fiscal,
)
from services.domain.logradouros_match import ResolucaoLogradouroQuery, resolver_logradouro
from services.domain.roteamento_busca import (
    Candidato,
    CodlogParse,
    ContribuinteParse,
    EnderecoCodlogParse,
    EnderecoLoteParse,
    EnderecoParse,
    LogradouroParse,
    RoteamentoQuery,
    TipoEntrada,
    rotear_entrada,
)

SectionRenderer = Callable[..., SecaoResultado | None]

MSG_SEM_RESULTADO_COMMIT = "Não foi possível localizar um resultado para essa busca no mapa."

REGISTRO_SECOES: dict[TipoEntrada, SectionRenderer] = {
    TipoEntrada.CONTRIBUINTE: secao_contribuinte,
    TipoEntrada.ENDERECO_LOTE: secao_endereco_lote,
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
        secao
        for candidato in result.candidatos
        if (render_secao := REGISTRO_SECOES.get(candidato.tipo)) is not None
        and (secao := render_secao(candidato)) is not None
    ]
    return render(request, "search/partials/_sugestoes.html", {"secoes": secoes})


_T = TypeVar("_T")


def _primeiro(itens: list[_T]) -> _T | None:
    return itens[0] if itens else None


def _acionar_candidato(request: HttpRequest, candidato: Candidato) -> HttpResponse | None:
    """Geocodifica o melhor match do candidato reusando os geocoders — o mesmo que faria o clique
    na 1ª sugestão dele. Devolve None quando o candidato não tem match (segue-se ao próximo)."""
    if isinstance(candidato, CodlogParse):
        cod = _primeiro(match_codlog(CodlogMatchInput(
            input_codlog=candidato.codlog,
            digito_verificador=candidato.digito_verificador or None,
        )))
        return None if cod is None else geocodificar_codlog(request, f"{cod.codlog}{cod.dv}")

    if isinstance(candidato, LogradouroParse):
        item = _primeiro(resolver_logradouro(ResolucaoLogradouroQuery(
            nome=candidato.nome, tipo=candidato.tipo_logradouro or None, modo="commit",
        )).itens)
        if item is None:
            return None
        logr = item.logradouro
        return geocodificar_codlog(request, f"{logr.codlog}{logr.dv}")

    if isinstance(candidato, ContribuinteParse):
        contrib = _primeiro(match_contribuinte(ContribuinteMatchInput(
            setor=candidato.setor,
            quadra=candidato.quadra or None,
            lote=candidato.lote or None,
            dv=candidato.dv or None,
        )))
        if contrib is None:
            return None
        return geocodificar_lote(
            request, contrib.setor, contrib.quadra, contrib.lote, contrib.tipo_lote,
            contrib.cd_condominio if contrib.is_condominio else None,
        )

    if isinstance(candidato, EnderecoLoteParse):
        codlogs = _resolver_codlogs(candidato)
        if not codlogs:
            return None
        fiscal = _primeiro(match_endereco_fiscal(EnderecoFiscalMatchInput(
            codlogs=codlogs, numero_padronizado=candidato.numero_padronizado,
        )))
        if fiscal is None:
            return None
        return geocodificar_lote(
            request, fiscal.setor, fiscal.quadra, fiscal.lote, fiscal.tipo_lote,
            fiscal.cd_condominio if fiscal.is_condominio else None,
        )

    if isinstance(candidato, EnderecoCodlogParse):
        cod_end = _primeiro(match_codlog(CodlogMatchInput(
            input_codlog=candidato.codlog.codlog,
            digito_verificador=candidato.codlog.digito_verificador or None,
        )))
        return (
            None if cod_end is None
            else geocodificar_endereco(request, f"{cod_end.codlog}{cod_end.dv}", candidato.numero)
        )

    if isinstance(candidato, EnderecoParse):
        item_end = _primeiro(resolver_logradouro(ResolucaoLogradouroQuery(
            nome=candidato.logradouro.nome,
            tipo=candidato.logradouro.tipo_logradouro or None,
            modo="commit",
        )).itens)
        if item_end is None:
            return None
        logr_end = item_end.logradouro
        return geocodificar_endereco(request, f"{logr_end.codlog}{logr_end.dv}", candidato.numero)

    return None


@require_POST
def comitar(request: HttpRequest) -> HttpResponse:
    """Enter na barra: comita a busca acionando o melhor match do 1º candidato que geocodifica —
    equivale a clicar na 1ª sugestão. Sem candidato/geometria, responde o aviso."""
    query = RoteamentoQuery(texto=request.POST.get("termo_pesquisa", ""), finished_typing=True)
    result = rotear_entrada(query)
    for candidato in result.candidatos:
        resposta = _acionar_candidato(request, candidato)
        if resposta is not None:
            return resposta
    return render(request, "mapping/_aviso.html", contexto_aviso(MSG_SEM_RESULTADO_COMMIT))
