from typing import Any

from django.conf import settings
from django.urls import reverse

from apps.lotes_mais_proximos.desenho_declarado import CONSULTA_LOTES_INTERSECTADOS
from apps.mapping.context import contexto_resultado_acao
from services.domain.geometry import GeoFeature, to_geojson_feature_collection
from services.domain.geometry.models import GeoJsonProperties
from services.domain.lotes_mais_proximos import CamadaLotes, LotesDoDesenho

WFS_LAYER_LOTE_CIDADAO: str = settings.WFS_LAYER_LOTE_CIDADAO
WFS_LOTE_CIDADAO_CAMPO_GEOMETRIA: str = settings.WFS_LOTE_CIDADAO_CAMPO_GEOMETRIA
MAP_INTERPOLATION_CRS: int = settings.MAP_INTERPOLATION_CRS
MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS


def camada_lotes() -> CamadaLotes:
    # MAP_INTERPOLATION_CRS (31983, métrico) dobra como CRS da camada de lotes: mesma unidade
    # que já serve a interpolação do endereço, sem introduzir um segundo CRS métrico no projeto.
    return CamadaLotes(
        nome=WFS_LAYER_LOTE_CIDADAO,
        campo_geometria=WFS_LOTE_CIDADAO_CAMPO_GEOMETRIA,
        crs_camada=MAP_INTERPOLATION_CRS,
        crs_saida=MAP_OUTPUT_CRS,
    )


def url_detalhe_do_lote(id_poligono: str) -> str:
    return f"{reverse('lotes_mais_proximos:detalhe_do_lote')}?id={id_poligono}"


def _properties_lote_do_desenho(lote: GeoFeature[Any, Any]) -> GeoJsonProperties:
    sql = lote.attributes.sql
    return GeoJsonProperties(
        id=lote.attributes.id_poligono,
        rotulo=f"SQL {sql}" if sql else "Sem contribuinte",
        url_ficha=url_detalhe_do_lote(lote.attributes.id_poligono),
    )


def contexto_lotes_do_desenho(resultado: LotesDoDesenho) -> dict[str, Any]:
    geojson = to_geojson_feature_collection(resultado.lotes, _properties_lote_do_desenho)
    contexto = contexto_resultado_acao(CONSULTA_LOTES_INTERSECTADOS.slug, resultado.desenho, geojson)
    return contexto | {"resultado": resultado}
