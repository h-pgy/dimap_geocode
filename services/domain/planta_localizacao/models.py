from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field
from services.domain.geometry import PolygonGeometry
from services.integrations.wms.models import BoundingBox


class EstiloGeometria(StrEnum):
    DESTAQUE = "destaque"
    CONTEXTO = "contexto"


class CamadaPlanta(BaseModel):
    model_config = ConfigDict(frozen=True)

    geometrias: tuple[PolygonGeometry, ...] = Field(min_length=1)
    estilo: EstiloGeometria


class PaletaPlanta(BaseModel):
    """Os traços da planta. Defaults do domínio; o ambiente sobrepõe como no tema do documento."""

    model_config = ConfigDict(frozen=True)

    cor_destaque: str = "#D84F7F"
    cor_contexto: str = "#CAF0F8"
    espessura_destaque_pt: float = 3.0
    espessura_contexto_pt: float = 1.2
    alfa_preenchimento_destaque: float = Field(default=0.15, ge=0, le=1)


class PlantaConfig(BaseModel):
    """O que é do processo: onde buscar a ortofoto, o tamanho e o CRS métrico das geometrias."""

    model_config = ConfigDict(frozen=True)

    camada_ortofoto: str
    crs: int
    folga_m: float = Field(default=15.0, ge=0)
    lado_px: int = Field(default=1600, gt=0)
    paleta: PaletaPlanta = PaletaPlanta()


class PlantaLocalizacaoInput(BaseModel):
    camadas: tuple[CamadaPlanta, ...] = Field(min_length=1)
    config: PlantaConfig


class PlantaLocalizacao(BaseModel):
    model_config = ConfigDict(frozen=True)

    png: bytes
    enquadramento: BoundingBox
