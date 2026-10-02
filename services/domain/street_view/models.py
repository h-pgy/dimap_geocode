from pydantic import BaseModel

from services.domain.geometry import PointGeometry


class LinkStreetViewInput(BaseModel):
    ponto: PointGeometry
    crs_ponto: int
    crs_street_view: int


class LinkStreetView(BaseModel):
    url: str
