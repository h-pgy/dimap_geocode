from django.conf import settings

from services.domain.lotes_mais_proximos import CamadaLotes

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
