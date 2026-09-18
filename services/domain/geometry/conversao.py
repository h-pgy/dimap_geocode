import json

from django.contrib.gis.geos import GEOSGeometry

from .models import LineGeometry, PointGeometry, PolygonGeometry


def para_geos(geometria: PointGeometry | LineGeometry | PolygonGeometry, srid: int) -> GEOSGeometry:
    geos = GEOSGeometry(json.dumps(geometria.model_dump()))
    geos.srid = srid
    return geos
