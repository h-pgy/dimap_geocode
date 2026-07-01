from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.mapping.context import contexto_mapa
from services.domain.geometry import GeoFeature, to_geojson_feature_collection
from services.domain.logradouro_geocod import LogradouroGeocoder, LogradouroGeocodInput
from services.integrations.wfs import build_fetcher

MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
WFS_LAYER_LOGRADOUROS: str = settings.WFS_LAYER_LOGRADOUROS
MAP_COR_LINHA: str = settings.MAP_COR_LINHA


def _properties(f: GeoFeature[Any, Any]) -> dict[str, Any]:
    return {
        "popup_html": render_to_string(
            "logradouro_geocoder/partials/_popup_segmento.html", {"a": f.attributes}
        ),
        "rotulo": f.attributes.nome_logradouro,
    }


@require_POST
def geocodificar(request: HttpRequest) -> HttpResponse:
    entrada = LogradouroGeocodInput(
        codlog=request.POST.get("codlog", ""),
        layer_name=WFS_LAYER_LOGRADOUROS,
        output_crs=MAP_OUTPUT_CRS,
    )
    features = LogradouroGeocoder(build_fetcher(settings))(entrada)
    geojson = to_geojson_feature_collection(features, _properties)
    return render(request, "mapping/_mapa.html", contexto_mapa(geojson, MAP_COR_LINHA))
