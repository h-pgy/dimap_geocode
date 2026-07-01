from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.mapping.context import contexto_mapa
from services.domain.geometry import GeoFeature, to_geojson_feature_collection
from services.domain.lote_geocod import LoteGeocoder, LoteGeocodInput
from services.integrations.wfs import build_fetcher

MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
WFS_LAYER_LOTE_CIDADAO: str = settings.WFS_LAYER_LOTE_CIDADAO
MAP_COR_POLIGONO: str = settings.MAP_COR_POLIGONO


def _properties(f: GeoFeature[Any, Any]) -> dict[str, Any]:
    return {
        "popup_html": render_to_string(
            "lote_geocoder/partials/_popup_lote.html", {"a": f.attributes}
        ),
        "rotulo": f"{f.attributes.setor}.{f.attributes.quadra}.{f.attributes.lote}",
    }


@require_POST
def geocodificar(request: HttpRequest) -> HttpResponse:
    entrada = LoteGeocodInput(
        setor=request.POST.get("setor", ""),
        quadra=request.POST.get("quadra", ""),
        lote=request.POST.get("lote", ""),
        tipo_lote=request.POST.get("tipo_lote", ""),
        layer_name=WFS_LAYER_LOTE_CIDADAO,
        output_crs=MAP_OUTPUT_CRS,
    )
    features = LoteGeocoder(build_fetcher(settings))(entrada)
    geojson = to_geojson_feature_collection(features, _properties)
    return render(request, "mapping/_mapa.html", contexto_mapa(geojson, MAP_COR_POLIGONO))
