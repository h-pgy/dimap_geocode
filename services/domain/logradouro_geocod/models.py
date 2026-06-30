from pydantic import BaseModel, Field, computed_field

from services.domain.geometry import GeoFeature, LineGeometry


class LogradouroGeocodInput(BaseModel):
    codlog: str = Field(pattern=r"^\d{6}$")
    layer_name: str
    output_crs: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def codlog_int(self) -> int:
        return int(self.codlog)


class SegmentoLogradouroAttributes(BaseModel):
    """Atributos do segmento de logradouro (camada `attributes` da feature)."""
    id_segmento: str
    codlog: str
    cd_tipo_logradouro: str
    nome_logradouro: str
    titulo: str | None = None
    preposicao: str | None = None
    numero_inicial_par: int | None = None
    numero_final_par: int | None = None
    numero_inicial_impar: int | None = None
    numero_final_impar: int | None = None


SegmentoLogradouroFeature = GeoFeature[LineGeometry, SegmentoLogradouroAttributes]
