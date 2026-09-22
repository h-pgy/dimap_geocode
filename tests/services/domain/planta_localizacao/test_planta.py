from io import BytesIO
from PIL import Image as PILImage
import pytest

from services.domain.geometry import PolygonGeometry
from services.domain.planta_localizacao import (
    CamadaPlanta,
    EstiloGeometria,
    GerarPlantaLocalizacao,
    PlantaConfig,
    PlantaLocalizacaoInput,
)
from services.integrations.wms.models import BoundingBox, WmsImage


def _imagem_png_cor(r: int, g: int, b: int, lado: int = 100) -> bytes:
    img = PILImage.new("RGB", (lado, lado), (r, g, b))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_gerar_planta_usa_content_da_wms_image() -> None:
    # Cria uma WmsImage com pixels vermelhos ao fundo
    png_vermelho = _imagem_png_cor(255, 0, 0, lado=200)
    bbox = BoundingBox(minx=10.0, miny=10.0, maxx=50.0, maxy=50.0, crs="EPSG:31983")
    wms_img = WmsImage(
        content=png_vermelho,
        content_type="image/png",
        width=200,
        height=200,
        layer="test:orto",
        bbox=bbox,
    )

    gerador = GerarPlantaLocalizacao(ortofoto=lambda _req: wms_img)

    anel = [[20.0, 20.0], [40.0, 20.0], [40.0, 40.0], [20.0, 40.0], [20.0, 20.0]]
    geom = PolygonGeometry(type="Polygon", coordinates=[anel])
    camada = CamadaPlanta(geometrias=(geom,), estilo=EstiloGeometria.DESTAQUE)
    cfg = PlantaConfig(camada_ortofoto="test:orto", crs=31983, lado_px=200)

    resultado = gerador(PlantaLocalizacaoInput(camadas=(camada,), config=cfg))

    assert resultado.png is not None
    assert len(resultado.png) > 0

    # Abre a imagem final e confere que o fundo vermelho foi preservado
    img_final = PILImage.open(BytesIO(resultado.png))
    assert img_final.size == (200, 200)
    # Canto superior esquerdo deve ter a cor do fundo (vermelho)
    pixel = img_final.getpixel((5, 5))
    assert pixel[0] > 200  # R alto
    assert pixel[1] < 50   # G baixo
    assert pixel[2] < 50   # B baixo


def test_gerar_planta_com_falha_de_fundo_gera_fallback() -> None:
    def _orto_falha(_req: object) -> WmsImage:
        raise RuntimeError("WMS offline")

    gerador = GerarPlantaLocalizacao(ortofoto=_orto_falha)

    anel = [[20.0, 20.0], [40.0, 20.0], [40.0, 40.0], [20.0, 40.0], [20.0, 20.0]]
    geom = PolygonGeometry(type="Polygon", coordinates=[anel])
    camada = CamadaPlanta(geometrias=(geom,), estilo=EstiloGeometria.DESTAQUE)
    cfg = PlantaConfig(camada_ortofoto="test:orto", crs=31983, lado_px=100)

    resultado = gerador(PlantaLocalizacaoInput(camadas=(camada,), config=cfg))
    assert resultado.png is not None
    img_final = PILImage.open(BytesIO(resultado.png))
    assert img_final.size == (100, 100)
