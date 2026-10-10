from pydantic import BaseModel

from services.domain.geometry import PointGeometry


class PedidoPanoramaInput(BaseModel):
    ponto: PointGeometry
    crs_ponto: int
    crs_street_view: int
    raio_m: float


class PedidoPanorama(BaseModel):
    alvo: PointGeometry
    raio_m: float
