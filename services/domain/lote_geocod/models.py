from pydantic import BaseModel, Field, computed_field, field_validator

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
    codlog: str | None = None          # cd_logradouro (opcional, como os demais de origem)
    nome_logradouro: str = ""          # nm_logradouro_completo (str; '' quando ausente/None)
    numero_porta: str = ""             # cd_numero_porta ORIGINAL (str; '' quando ausente/None)
    tipo_quadra: str | None = None
    condominio: str | None = None

    @field_validator("nome_logradouro", "numero_porta", mode="before")
    @classmethod
    def _none_para_vazio(cls, v: object) -> str:
        return "" if v is None else str(v)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def endereco(self) -> str:
        """Endereço por extenso da base oficial: nome do logradouro + número de porta."""
        partes = [p for p in (self.nome_logradouro, self.numero_porta) if p]
        return ", ".join(partes)


LoteFeature = GeoFeature[PolygonGeometry, LoteAttributes]
