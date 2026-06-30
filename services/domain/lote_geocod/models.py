from pydantic import BaseModel, Field, field_validator

from services.domain.geometry import GeoFeature, PolygonGeometry


class LoteGeocodInput(BaseModel):
    setor: str = Field(pattern=r"^\d{3}$")
    quadra: str = Field(pattern=r"^\d{3}$")
    lote: str = Field(pattern=r"^\d{4}$")
    tipo_lote: str
    layer_name: str

    @field_validator("tipo_lote", mode="before")
    @classmethod
    def _upper_tipo_lote(cls, v: object) -> str:
        return str(v).upper()
    output_crs: int


class LoteAttributes(BaseModel):
    """Atributos do lote (camada `attributes` da feature)."""
    id_poligono: str
    setor: str
    quadra: str
    lote: str
    tipo_lote: str
    tipo_quadra: str | None = None
    condominio: str | None = None


LoteFeature = GeoFeature[PolygonGeometry, LoteAttributes]
