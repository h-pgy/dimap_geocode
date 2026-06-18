from pydantic import BaseModel


class BoundingBox(BaseModel):
    """Bounding box CRS-aware. DTO autocontido desta integration (não importado de fora)."""

    minx: float
    miny: float
    maxx: float
    maxy: float
    crs: str = "EPSG:31983"  # SIRGAS 2000 / UTM 23S (São Paulo)

    @property
    def string_wms(self) -> str:
        # ordem minx,miny,maxx,maxy (lon/lat).
        # Nota: WMS 1.3.0 + EPSG:4326 inverte p/ lat/lon — caller é responsável pelo CRS correto.
        return f"{self.minx},{self.miny},{self.maxx},{self.maxy}"


class WmsConnectionConfig(BaseModel):
    vector_url: str
    raster_url: str
    version: str = "1.3.0"
    default_crs: str = "EPSG:31983"
    image_format: str = "image/png"
    default_width: int = 256
    default_height: int = 256

    def base_url_for(self, *, raster: bool) -> str:
        return self.raster_url if raster else self.vector_url


class WmsMapRequest(BaseModel):
    layer: str
    bbox: BoundingBox
    width: int | None = None
    height: int | None = None
    raster: bool = False
    crs: str | None = None
    image_format: str | None = None
    transparent: bool = True
    styles: str = ""


class WmsImage(BaseModel):
    content: bytes
    content_type: str
    width: int
    height: int
    layer: str
    bbox: BoundingBox
