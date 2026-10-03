from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.mapping.context import contexto_aviso, contexto_mapa
from apps.search.secoes import SecaoResultado
from apps.search.tentativas import FalhaBaseOficial
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
from services.domain.logradouros_match import ResolucaoLogradouroQuery, resolver_logradouro
from services.domain.roteamento_busca import EnderecoCodlogParse, EnderecoParse
from services.integrations.wfs import build_fetcher
from services.domain.geometry.models import GeoJsonProperties

TITULO_ENDERECO_CODLOG = "Endereço (por codlog)"
TITULO_ENDERECO_NOME = "Endereço (por nome)"
TITULO_ENDERECO_NOME_APROXIMADO = "Endereço (por nome, aproximado)"

MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
MAP_INTERPOLATION_CRS: int = settings.MAP_INTERPOLATION_CRS
WFS_LAYER_LOGRADOUROS: str = settings.WFS_LAYER_LOGRADOUROS
MAP_COR_PONTO: str = settings.MAP_COR_PONTO
MAIS_PROXIMO_RAIO_LIMITE_M: float = settings.MAIS_PROXIMO_RAIO_LIMITE_M

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
    dto = ResolucaoLogradouroQuery(
        nome=candidato.logradouro.nome,
        tipo=candidato.logradouro.tipo_logradouro or None,
        modo="sugestao",
    )
    resultado = resolver_logradouro(dto)
    if not resultado.itens:
        return None  # seção OMITIDA: sem match não polui a UX
    html = render_to_string(
        "address_geocoder/partials/resultados_endereco_nome.html",
        {"resultado": resultado, "numero": candidato.numero},
    )
    titulo = TITULO_ENDERECO_NOME_APROXIMADO if resultado.usou_fuzzy else TITULO_ENDERECO_NOME
    return SecaoResultado(titulo=titulo, html=html)


def _properties(f: EnderecoFeature) -> GeoJsonProperties:
    a = f.attributes
    return GeoJsonProperties(
        popup_html=render_to_string(
            "address_geocoder/partials/_popup_endereco.html", {"a": a}
        ),
        rotulo=f"{a.logradouro.nome_completo}, {a.numero}",
        cor=None,
    )


def resolver_endereco(codlog: str, numero: object) -> EnderecoFeature | FalhaBaseOficial:
    """Interpola o endereço (codlog 6 dígitos + número) na base oficial. `numero` chega como str
    (POST) ou int (candidato) — o Pydantic coage."""
    entrada = AddressGeocodInput.model_validate({
        "codlog": codlog,
        "numero": numero,                            # Pydantic coage "123" → 123 (Field(gt=0))
        "layer_name": WFS_LAYER_LOGRADOUROS,
        "interpolation_crs": MAP_INTERPOLATION_CRS,
        "output_crs": MAP_OUTPUT_CRS,
    })
    geocoder = AddressGeocoder(LogradouroGeocoder(build_fetcher(settings)))
    try:
        return geocoder(entrada)
    except SegmentoNaoEncontradoError:
        return FalhaBaseOficial(motivo=MSG_SEM_SEGMENTO)
    except NumeracaoNaoEncontradaError:
        return FalhaBaseOficial(motivo=MSG_SEM_NUMERACAO)


def renderizar_endereco(
    request: HttpRequest,
    feature: EnderecoFeature,
    score: float | None = None,
) -> HttpResponse:
    """Desenha o ponto e abre a gaveta do endereço (SPEC localizacao_lote/002). `score` é só
    apresentação (grau de certeza do fuzzy match, quando houver) — nenhuma regra do domínio o lê."""
    geojson = to_geojson_feature_collection([feature], _properties)
    contexto = contexto_mapa(geojson, MAP_COR_PONTO) | {
        "endereco": feature.attributes,
        "ponto": feature.geometry,
        "score": score,
        "raio_m": MAIS_PROXIMO_RAIO_LIMITE_M,
    }
    return render(request, "address_geocoder/partials/_resultado_endereco.html", contexto)


def geocodificar_endereco(
    request: HttpRequest,
    codlog: str,
    numero: object,
    score: float | None = None,
) -> HttpResponse:
    resolvido = resolver_endereco(codlog, numero)
    if isinstance(resolvido, FalhaBaseOficial):
        # o clique numa sugestão oficial é escolha explícita: a falha vira aviso, sem fallback
        return render(request, "mapping/_aviso.html", contexto_aviso(resolvido.motivo))
    return renderizar_endereco(request, resolvido, score)


@require_POST
def selecionar(request: HttpRequest) -> HttpResponse:
    score_raw = request.POST.get("score")
    score = float(score_raw) if score_raw else None
    return geocodificar_endereco(
        request, request.POST.get("codlog", ""), request.POST.get("numero", ""), score=score
    )
