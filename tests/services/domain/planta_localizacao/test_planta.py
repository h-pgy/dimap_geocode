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
from services.integrations.wms import WmsHttpError
from services.integrations.wms.models import BoundingBox, WmsImage, WmsMapRequest

CRS_METRICO = 31983


def _png_cor(r: int, g: int, b: int, lado: int) -> bytes:
    imagem = PILImage.new("RGB", (lado, lado), (r, g, b))
    buffer = BytesIO()
    imagem.save(buffer, format="PNG")
    return buffer.getvalue()


def _wms_image(png: bytes, lado: int) -> WmsImage:
    bbox = BoundingBox(minx=0.0, miny=0.0, maxx=1.0, maxy=1.0, crs=f"EPSG:{CRS_METRICO}")
    return WmsImage(
        content=png,
        content_type="image/png",
        width=lado,
        height=lado,
        layer="test:orto",
        bbox=bbox,
    )


def _quadrado(minx: float, miny: float, lado: float) -> PolygonGeometry:
    anel = [
        [minx, miny],
        [minx + lado, miny],
        [minx + lado, miny + lado],
        [minx, miny + lado],
        [minx, miny],
    ]
    return PolygonGeometry(type="Polygon", coordinates=[anel])


def _entrada(
    camadas: tuple[CamadaPlanta, ...],
    lado_px: int = 200,
    folga_m: float = 15.0,
) -> PlantaLocalizacaoInput:
    config = PlantaConfig(
        camada_ortofoto="test:orto",
        crs=CRS_METRICO,
        lado_px=lado_px,
        folga_m=folga_m,
    )
    return PlantaLocalizacaoInput(camadas=camadas, config=config)


def test_planta_desenha_sobre_a_ortofoto_recebida() -> None:
    lado = 200
    fundo = _wms_image(_png_cor(255, 0, 0, lado), lado)
    gerador = GerarPlantaLocalizacao(ortofoto=lambda _req: fundo)
    camada = CamadaPlanta(
        geometrias=(_quadrado(20.0, 20.0, 20.0),),
        estilo=EstiloGeometria.DESTAQUE,
    )

    resultado = gerador(_entrada((camada,), lado_px=lado))

    imagem = PILImage.open(BytesIO(resultado.png))
    assert imagem.size == (lado, lado)
    assert imagem.convert("RGB").getpixel((5, 5)) == (255, 0, 0)


def test_planta_propaga_erro_do_wms() -> None:
    def _indisponivel(_req: WmsMapRequest) -> WmsImage:
        raise WmsHttpError("GeoSampa fora do ar")

    gerador = GerarPlantaLocalizacao(ortofoto=_indisponivel)
    camada = CamadaPlanta(
        geometrias=(_quadrado(20.0, 20.0, 20.0),),
        estilo=EstiloGeometria.DESTAQUE,
    )

    with pytest.raises(WmsHttpError):
        gerador(_entrada((camada,)))


def test_enquadramento_une_camadas_e_soma_folga() -> None:
    capturado: list[WmsMapRequest] = []

    def _capturar(req: WmsMapRequest) -> WmsImage:
        capturado.append(req)
        lado = req.width or 200
        return _wms_image(_png_cor(10, 10, 10, lado), lado)

    gerador = GerarPlantaLocalizacao(ortofoto=_capturar)
    perto = CamadaPlanta(
        geometrias=(_quadrado(0.0, 0.0, 10.0),),
        estilo=EstiloGeometria.DESTAQUE,
    )
    longe = CamadaPlanta(
        geometrias=(_quadrado(90.0, 0.0, 10.0),),
        estilo=EstiloGeometria.CONTEXTO,
    )

    resultado = gerador(_entrada((perto, longe), folga_m=15.0))

    enquadramento = resultado.enquadramento
    # As duas camadas cabem inteiras, com a folga sobrando de cada lado.
    assert enquadramento.minx <= -15.0
    assert enquadramento.maxx >= 115.0
    assert enquadramento.miny <= -15.0
    assert enquadramento.maxy >= 25.0
    # Quadrado e centrado na união: o WMS devolve imagem quadrada, e bbox retangular a distorceria.
    largura = enquadramento.maxx - enquadramento.minx
    altura = enquadramento.maxy - enquadramento.miny
    assert largura == pytest.approx(altura)
    assert (enquadramento.minx + enquadramento.maxx) / 2 == pytest.approx(50.0)
    assert (enquadramento.miny + enquadramento.maxy) / 2 == pytest.approx(5.0)

    assert capturado[0].crs == f"EPSG:{CRS_METRICO}"
    assert capturado[0].raster is True
