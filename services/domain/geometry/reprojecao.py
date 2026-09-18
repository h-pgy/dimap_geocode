import json

from django.contrib.gis.geos import GEOSGeometry

from .models import LineGeometry, PointGeometry, PolygonGeometry


def reprojetar[G: (PointGeometry, LineGeometry, PolygonGeometry)](
    geometria: G,
    origem: int,
    destino: int,
) -> G:
    # SRID via atributo, não no construtor: GEOSGeometry lê GeoJSON como SRID 4326 (RFC 7946) e
    # rejeita um srid explícito que destoe disso quando origem != 4326.
    geos = GEOSGeometry(json.dumps(geometria.model_dump()))
    geos.srid = origem
    geos.transform(destino)
    return type(geometria).model_validate_json(geos.geojson)
