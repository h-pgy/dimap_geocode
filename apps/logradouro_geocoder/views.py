from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.mapping.context import contexto_mapa
from services.domain.geometry import GeoFeature, to_geojson_feature_collection
from services.domain.logradouro_geocod import LogradouroGeocoder, LogradouroGeocodInput
from services.integrations.wfs import WfsConnectionConfig, WfsFetcher, WfsRetryPolicy

MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
WFS_LAYER_LOGRADOUROS: str = settings.WFS_LAYER_LOGRADOUROS
MAP_COR_LINHA: str = settings.MAP_COR_LINHA


def _fetcher() -> WfsFetcher:
    config = WfsConnectionConfig(
        domain=settings.WFS_DOMAIN,
        endpoint=settings.WFS_ENDPOINT,
        namespace=settings.WFS_NAMESPACE,
        service=settings.WFS_SERVICE,
        version=settings.WFS_VERSION,
    )
    retry = WfsRetryPolicy(
        request_timeout_seconds=settings.WFS_REQUEST_TIMEOUT_SECONDS,
        max_retries=settings.WFS_MAX_RETRIES,
        retry_wait_min_seconds=settings.WFS_RETRY_WAIT_MIN_SECONDS,
        retry_wait_max_seconds=settings.WFS_RETRY_WAIT_MAX_SECONDS,
    )
    return WfsFetcher(config, retry_policy=retry)


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
    features = LogradouroGeocoder(_fetcher())(entrada)
    geojson = to_geojson_feature_collection(features, _properties)
    return render(request, "mapping/_mapa.html", contexto_mapa(geojson, MAP_COR_LINHA))
