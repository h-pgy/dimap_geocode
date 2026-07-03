from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.mapping.context import contexto_aviso, contexto_mapa
from apps.search.secoes import SecaoResultado
from services.domain.address_geocod import (
    AddressGeocodInput,
    AddressGeocoder,
    EnderecoFeature,
    NumeracaoNaoEncontradaError,
    SegmentoNaoEncontradoError,
)
from services.domain.codlog_match import CodlogMatchInput, match_codlog
from services.domain.geometry import to_geojson_feature_collection
from services.domain.logradouro_geocod import LogradouroGeocoder
from services.domain.logradouros_match import LiteralLogradouroQuery, match_logradouro_literal
from services.domain.roteamento_busca import EnderecoCodlogParse, EnderecoParse
from services.integrations.wfs import build_fetcher
from services.domain.geometry.models import GeoJsonProperties

TITULO_ENDERECO_CODLOG = "Endereço (por codlog)"
TITULO_ENDERECO_NOME = "Endereço (por nome)"

MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
MAP_INTERPOLATION_CRS: int = settings.MAP_INTERPOLATION_CRS
WFS_LAYER_LOGRADOUROS: str = settings.WFS_LAYER_LOGRADOUROS
MAP_COR_PONTO: str = settings.MAP_COR_PONTO

MSG_SEM_SEGMENTO = "Não foi possível localizar o logradouro para geocodificar este endereço."
MSG_SEM_NUMERACAO = "O número informado está fora da faixa de numeração cadastrada para este logradouro."


def secao_endereco_codlog(candidato: EnderecoCodlogParse) -> SecaoResultado | None:
    dto = CodlogMatchInput(
        input_codlog=candidato.codlog.codlog,
        digito_verificador=candidato.codlog.digito_verificador or None,
    )
    resultados = match_codlog(dto)
    if not resultados:
        return None  # seção OMITIDA: sem match não polui a UX
    html = render_to_string(
        "address_geocoder/partials/resultados_endereco_codlog.html",
        {"resultados": resultados, "numero": candidato.numero},
    )
    return SecaoResultado(titulo=TITULO_ENDERECO_CODLOG, html=html)


def secao_endereco(candidato: EnderecoParse) -> SecaoResultado | None:
    dto = LiteralLogradouroQuery(
        nome=candidato.logradouro.nome,
        tipo=candidato.logradouro.tipo_logradouro or None,
    )
    resultado = match_logradouro_literal(dto)
    if not resultado.logradouros:
        return None  # seção OMITIDA: sem match não polui a UX
    html = render_to_string(
        "address_geocoder/partials/resultados_endereco_nome.html",
        {"resultado": resultado, "numero": candidato.numero},
    )
    return SecaoResultado(titulo=TITULO_ENDERECO_NOME, html=html)


def _properties(f: EnderecoFeature) -> GeoJsonProperties:
    a = f.attributes
    return GeoJsonProperties(
        popup_html=render_to_string(
            "address_geocoder/partials/_popup_endereco.html", {"a": a}
        ),
        rotulo=f"{a.nome_completo}, {a.numero}",
        cor=None,
    )


@require_POST
def selecionar(request: HttpRequest) -> HttpResponse:
    entrada = AddressGeocodInput.model_validate({
        "codlog": request.POST.get("codlog", ""),
        "numero": request.POST.get("numero", ""),   # Pydantic coage "123" → 123 (Field(gt=0))
        "layer_name": WFS_LAYER_LOGRADOUROS,
        "interpolation_crs": MAP_INTERPOLATION_CRS,
        "output_crs": MAP_OUTPUT_CRS,
    })
    geocoder = AddressGeocoder(LogradouroGeocoder(build_fetcher(settings)))
    try:
        feature = geocoder(entrada)
    except SegmentoNaoEncontradoError:
        return render(request, "mapping/_aviso.html", contexto_aviso(MSG_SEM_SEGMENTO))
    except NumeracaoNaoEncontradaError:
        return render(request, "mapping/_aviso.html", contexto_aviso(MSG_SEM_NUMERACAO))
    geojson = to_geojson_feature_collection([feature], _properties)
    return render(request, "mapping/_mapa.html", contexto_mapa(geojson, MAP_COR_PONTO))
