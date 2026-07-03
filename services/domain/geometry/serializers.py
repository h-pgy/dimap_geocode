from collections.abc import Callable, Sequence
from typing import Any

from .models import GeoFeature


def to_geojson_feature_collection(
    features: Sequence[GeoFeature[Any, Any]],
    properties: Callable[[GeoFeature[Any, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Converte features de domínio numa GeoJSON FeatureCollection 4326 (formato do Leaflet).
    Agnóstico ao tipo de geometria. Envelope é geometria (mora aqui); properties de
    apresentação (popup_html, rotulo) vêm do app via `properties` — este módulo não renderiza HTML."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": f.geometry.model_dump(),
                "properties": properties(f),
            }
            for f in features
        ],
    }
