from pydantic import BaseModel, Field

from services.domain.geometry import GeoFeature, PointGeometry


class AddressGeocodInput(BaseModel):
    codlog: str                 # repassado ao LogradouroGeocodInput (que valida a forma)
    numero: int = Field(gt=0)   # número do imóvel, já parseado (int) upstream
    layer_name: str             # camada de logradouros (settings, via orquestração)
    interpolation_crs: int      # CRS projetado p/ interpolar (ex.: 31983), via orquestração
    output_crs: int             # CRS de saída (ex.: 4326), via orquestração


class EnderecoAttributes(BaseModel):
    """Proveniência do ponto geocodificado (camada `attributes` da feature)."""
    codlog: str
    nome_logradouro: str
    cd_tipo_logradouro: str
    numero: int
    id_segmento: str            # segmento que originou a interpolação
    titulo: str | None = None


EnderecoFeature = GeoFeature[PointGeometry, EnderecoAttributes]
