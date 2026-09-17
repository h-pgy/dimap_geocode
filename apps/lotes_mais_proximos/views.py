from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from pydantic import BaseModel

from apps.lotes_mais_proximos.contexto import camada_lotes
from apps.mapping.context import contexto_aviso, contexto_mapa
from services.domain.geometry import GeoFeature, PointGeometry, to_geojson_feature_collection
from services.domain.geometry.models import GeoJsonProperties
from services.domain.lotes_mais_proximos import (
    LoteMaisProximo,
    LoteMaisProximoInput,
    LoteProximo,
    NenhumLoteProximoError,
)
from services.integrations.wfs import build_fetcher

MAP_COR_PONTO: str = settings.MAP_COR_PONTO
MAP_COR_POLIGONO: str = settings.MAP_COR_POLIGONO
MAP_COR_POLIGONO_CONDOMINIO: str = settings.MAP_COR_POLIGONO_CONDOMINIO
LOTE_MAIS_PROXIMO_RAIO_M: float = settings.LOTE_MAIS_PROXIMO_RAIO_M

TEMPLATE_RESULTADO_MAIS_PROXIMO = "lotes_mais_proximos/partials/_resultado_mais_proximo.html"

# O raio sai da mesma constante que alimentou a consulta; a exceção não precisa carregá-lo de volta.
MSG_SEM_LOTE_PROXIMO = (
    "Nenhum lote situado neste logradouro foi encontrado "
    "a {raio_m:.0f} metros do ponto de busca."
)


class ConsultaLoteMaisProximo(BaseModel):
    """O formulário da gaveta. lon/lat malformados morrem no PydanticValidationMiddleware."""

    lon: float
    lat: float
    codlog: str
    # Rótulo do endereço de origem, só para a gaveta ler — como `score`, é apresentação.
    origem: str = ""


def _properties_lote(f: GeoFeature[Any, Any]) -> GeoJsonProperties:
    cor_condominio = (
        MAP_COR_POLIGONO_CONDOMINIO if getattr(f.attributes, "is_condominio", False) else None
    )
    return GeoJsonProperties(
        popup_html=render_to_string(
            "lote_geocoder/partials/_popup_lote.html", {"a": f.attributes}
        ),
        rotulo=f"{f.attributes.setor}.{f.attributes.quadra}.{f.attributes.lote}",
        cor=cor_condominio,
    )


def _ponto_feature(ponto: PointGeometry) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": ponto.model_dump(),
        "properties": GeoJsonProperties(cor=MAP_COR_PONTO).model_dump(exclude_none=True),
    }


def _contexto_mais_proximo(
    ponto: PointGeometry, proximo: LoteProximo, origem: str
) -> dict[str, Any]:
    lote_geojson = to_geojson_feature_collection([proximo.lote], _properties_lote)
    geojson = {
        "type": "FeatureCollection",
        "features": [_ponto_feature(ponto), *lote_geojson["features"]],
    }
    return contexto_mapa(geojson, MAP_COR_POLIGONO) | {
        "lote": proximo.lote.attributes,
        "distancia_m": proximo.distancia_m,
        "origem_busca": origem,
    }


@require_POST
def mais_proximo(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaLoteMaisProximo.model_validate(request.POST.dict())
    entrada = LoteMaisProximoInput(
        ponto=PointGeometry(type="Point", coordinates=[consulta.lon, consulta.lat]),
        codlog=consulta.codlog,
        raio_m=LOTE_MAIS_PROXIMO_RAIO_M,
        camada=camada_lotes(),
    )
    try:
        proximo = LoteMaisProximo(build_fetcher(settings))(entrada)
    except NenhumLoteProximoError:
        return render(
            request,
            "mapping/_aviso.html",
            contexto_aviso(MSG_SEM_LOTE_PROXIMO.format(raio_m=LOTE_MAIS_PROXIMO_RAIO_M)),
        )
    return render(
        request,
        TEMPLATE_RESULTADO_MAIS_PROXIMO,
        _contexto_mais_proximo(entrada.ponto, proximo, consulta.origem),
    )
