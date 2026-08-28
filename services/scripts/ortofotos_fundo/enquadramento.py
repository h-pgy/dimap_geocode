from django.contrib.gis.geos import Point

from config.pontos_fundo import PontoFundo
from services.integrations.wms import BoundingBox

from .contrato import OrtofotoConfig


def enquadrar(ponto: PontoFundo, config: OrtofotoConfig) -> BoundingBox:
    centro = Point(ponto.lng, ponto.lat, srid=config.crs_entrada)
    centro.transform(config.crs_saida)
    meia_largura = config.largura_px / 2 * config.metros_por_pixel
    meia_altura = config.altura_px / 2 * config.metros_por_pixel
    return BoundingBox(
        minx=centro.x - meia_largura,
        miny=centro.y - meia_altura,
        maxx=centro.x + meia_largura,
        maxy=centro.y + meia_altura,
        crs=f"EPSG:{config.crs_saida}",
    )
