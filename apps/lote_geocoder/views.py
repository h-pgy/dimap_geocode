from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.mapping.context import contexto_aviso, contexto_mapa
from services.domain.geometry import GeoFeature, to_geojson_feature_collection
from services.domain.lote_geocod import LoteGeocoder, LoteGeocodInput
from services.integrations.wfs import build_fetcher
from services.domain.geometry.models import GeoJsonProperties

MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
WFS_LAYER_LOTE_CIDADAO: str = settings.WFS_LAYER_LOTE_CIDADAO
MAP_COR_POLIGONO: str = settings.MAP_COR_POLIGONO
MAP_COR_POLIGONO_CONDOMINIO: str = settings.MAP_COR_POLIGONO_CONDOMINIO


def _properties(f: GeoFeature[Any, Any]) -> GeoJsonProperties:
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


def geocodificar_lote(
    request: HttpRequest,
    setor: str,
    quadra: str,
    lote: str,
    tipo_lote: str,
    cod_condominio: str | None,
) -> HttpResponse:
    """Geocodifica um lote → polígono. Reutilizável pela view e pela busca comitada."""
    entrada = LoteGeocodInput(
        setor=setor,
        quadra=quadra,
        lote=lote,
        tipo_lote=tipo_lote,
        cod_condominio=cod_condominio,
        layer_name=WFS_LAYER_LOTE_CIDADAO,
        output_crs=MAP_OUTPUT_CRS,
    )
    features = LoteGeocoder(build_fetcher(settings))(entrada)
    if not features:
        return render(
            request,
            "mapping/_aviso.html",
            contexto_aviso("Este lote não possui geometria cadastrada para exibir no mapa."),
        )
    geojson = to_geojson_feature_collection(features, _properties)
    return render(request, "mapping/_mapa.html", contexto_mapa(geojson, MAP_COR_POLIGONO))


@require_POST
def geocodificar(request: HttpRequest) -> HttpResponse:
    cd_cond_raw = request.POST.get("cd_condominio", "")
    cod_condominio = cd_cond_raw if cd_cond_raw and cd_cond_raw != "None" else None
    return geocodificar_lote(
        request,
        setor=request.POST.get("setor", ""),
        quadra=request.POST.get("quadra", ""),
        lote=request.POST.get("lote", ""),
        tipo_lote=request.POST.get("tipo_lote", ""),
        cod_condominio=cod_condominio,
    )
