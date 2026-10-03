from pydantic import BaseModel, Field

from services.domain.geometry import GeoFeature, LineGeometry, PointGeometry


class LogradouroGeocodInput(BaseModel):
    # codlog é string com zero à esquerda ("059447"): a camada segmento_logradouro
    # do GeoSampa guarda o campo como texto, então o CQL precisa consultar por string.
    codlog: str = Field(pattern=r"^\d{6}$")
    layer_name: str
    output_crs: int


class SegmentoLogradouroAttributes(BaseModel):
    """Atributos do segmento de logradouro (camada `attributes` da feature)."""
    id_segmento: str
    codlog: str
    tipo_logradouro: str
    nome_logradouro: str
    titulo: str | None = None
    preposicao: str | None = None
    numero_inicial_par: int | None = None
    numero_final_par: int | None = None
    numero_inicial_impar: int | None = None
    numero_final_impar: int | None = None


SegmentoLogradouroFeature = GeoFeature[LineGeometry, SegmentoLogradouroAttributes]


class SegmentosNoRaioInput(BaseModel):
    ponto: PointGeometry
    crs_ponto: int
    raio_m: float = Field(gt=0)
    layer_name: str
    campo_geometria: str
    crs_metrico: int


class SegmentoProximo(BaseModel):
    """Um segmento e a distância dele ao ponto, apurada no CRS métrico."""

    segmento: SegmentoLogradouroFeature
    distancia_m: float = Field(ge=0)
