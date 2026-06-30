from typing import Any

from django.conf import settings

WMS_URL: str = settings.WMS_URL
WMS_VERSION: str = settings.WMS_VERSION
WMS_BASES: list[dict[str, str]] = settings.WMS_BASES
MAP_CENTRO_DEFAULT: list[float] = settings.MAP_CENTRO_DEFAULT
MAP_ZOOM_DEFAULT: int = settings.MAP_ZOOM_DEFAULT


def contexto_mapa(geometria: dict[str, Any], cor: str) -> dict[str, Any]:
    """Monta o contexto do partial do mapa: geometria GeoJSON 4326 + cor + config WMS/centro.
    Agnóstico de domínio — não conhece logradouro/lote, só geometria pronta."""
    return {
        "wms": {"url": WMS_URL, "version": WMS_VERSION, "bases": WMS_BASES},
        "payload": {
            "geometria": geometria,
            "cor": cor,
            "centro": MAP_CENTRO_DEFAULT,
            "zoom": MAP_ZOOM_DEFAULT,
        },
    }
