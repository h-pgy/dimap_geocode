from collections.abc import Callable, Sequence
from typing import Any

from .models import GeoFeature, GeoJsonProperties


def to_geojson_feature_collection(
    features: Sequence[GeoFeature[Any, Any]],
    properties: Callable[[GeoFeature[Any, Any]], GeoJsonProperties],
) -> dict[str, Any]:
    """Converte features de domínio numa GeoJSON FeatureCollection 4326 (formato do Leaflet).
    Agnóstico ao tipo de geometria. Envelope é geometria (mora aqui); properties de
    apresentação (popup_html, rotulo, cor) vêm do app via `properties`."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": f.geometry.model_dump(),
                "properties": properties(f).model_dump(exclude_none=True),
            }
            for f in features
        ],
    }
