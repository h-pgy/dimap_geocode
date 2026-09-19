from pydantic import BaseModel, ConfigDict, Field

from services.domain.desenho import Desenho
from services.domain.geometry import PointGeometry
from services.domain.lote_geocod import LoteFeature


class CamadaLotes(BaseModel):
    """Onde os lotes moram no GeoServer — processo, não domínio; chega pronto da orquestração."""

    model_config = ConfigDict(frozen=True)

    nome: str
    campo_geometria: str
    crs_camada: int  # CRS métrico em que distância e área fazem sentido
    crs_saida: int  # CRS do mapa


class LoteProximo(BaseModel):
    """Um lote e a distância dele ao ponto, apurada no CRS da camada."""

    lote: LoteFeature
    # Menor distância do ponto à borda do lote; zero quando o ponto cai dentro dele.
    distancia_m: float = Field(ge=0)


class LoteMaisProximoInput(BaseModel):
    ponto: PointGeometry  # no CRS de saída (o do mapa)
    codlog: str = Field(pattern=r"^\d{6}$")
    raio_m: float = Field(gt=0)
    camada: CamadaLotes


class LotesDoDesenho(BaseModel):
    """O que a consulta apurou: o desenho, a área dele e os lotes que ele cruza."""

    desenho: Desenho
    # Guardada: depende do CRS métrico da camada, que não mora no desenho.
    area_m2: float = Field(gt=0)
    lotes: tuple[LoteFeature, ...] = ()
