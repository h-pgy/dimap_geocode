from typing import Any

from django.conf import settings

WMS_URL: str = settings.WMS_URL
WMS_VERSION: str = settings.WMS_VERSION
WMS_BASES: list[dict[str, str]] = settings.WMS_BASES
MAP_CENTRO_DEFAULT: list[float] = settings.MAP_CENTRO_DEFAULT
MAP_ZOOM_DEFAULT: int = settings.MAP_ZOOM_DEFAULT
MAP_TILES_PUBLICOS_URL: str = settings.MAP_TILES_PUBLICOS_URL
MAP_TILES_PUBLICOS_SUBDOMINIOS: str = settings.MAP_TILES_PUBLICOS_SUBDOMINIOS
MAP_TILES_PUBLICOS_ATRIBUICAO: str = settings.MAP_TILES_PUBLICOS_ATRIBUICAO
MAP_TILES_PUBLICOS_ZOOM_MAXIMO: int = settings.MAP_TILES_PUBLICOS_ZOOM_MAXIMO
MAP_ZOOM_FUNDO_ADMIN: int = settings.MAP_ZOOM_FUNDO_ADMIN


def contexto_mapa_base() -> dict[str, Any]:
    """Contexto do canvas singleton da home: base WMS + centro/zoom, sem geometria.
    O mapa nasce uma única vez na home; resultados chegam depois como payload (§ contexto_mapa)."""
    return {
        "wms": {"url": WMS_URL, "version": WMS_VERSION, "bases": WMS_BASES},
        "config": {"centro": MAP_CENTRO_DEFAULT, "zoom": MAP_ZOOM_DEFAULT},
    }


def contexto_fundo_admin() -> dict[str, Any]:
    """Contexto do fundo à deriva da área administrativa: ortofoto do GeoSampa (dessaturada) + centro/zoom.
    Usa a mesma ortofoto da home, mas com dessaturação aplicada no CSS antes do filtro azul."""
    return {
        "wms": {"url": WMS_URL, "version": WMS_VERSION, "bases": WMS_BASES},
        "config_fundo": {
            "centro": MAP_CENTRO_DEFAULT,
            "zoom": MAP_ZOOM_FUNDO_ADMIN,
        },
    }


def contexto_mapa(geometria: dict[str, Any], cor: str) -> dict[str, Any]:
    """Monta o contexto de payload de um resultado: geometria GeoJSON 4326 + cor, sem WMS
    (o mapa singleton já existe). Agnóstico de domínio — só geometria pronta."""
    return {"payload": {"geometria": geometria, "cor": cor}}


def contexto_aviso(mensagem: str) -> dict[str, Any]:
    """Contexto do partial de aviso do mapping: só a mensagem pronta (agnóstico de domínio)."""
    return {"mensagem": mensagem}
