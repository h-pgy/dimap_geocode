from django.template.loader import render_to_string

from apps.search.secoes import SecaoResultado
from services.domain.codlog_match import CodlogMatchInput, match_codlog
from services.domain.logradouros_match import LiteralLogradouroQuery, match_logradouro_literal
from services.domain.roteamento_busca import CodlogParse, LogradouroParse

TITULO_LOGRADOURO_NOME = "Logradouro (por nome)"


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


def _render_logradouro(dto: LiteralLogradouroQuery) -> str:
    resultado = match_logradouro_literal(dto)
    return render_to_string(
        "logradouro_matcher/partials/resultados_logradouro.html",
        {"resultado": resultado},
    )


def secao_logradouro(candidato: LogradouroParse) -> SecaoResultado:
    dto = LiteralLogradouroQuery(
        nome=candidato.nome,
        tipo=candidato.tipo_logradouro or None,
    )
    return SecaoResultado(titulo=TITULO_LOGRADOURO_NOME, html=_render_logradouro(dto))
