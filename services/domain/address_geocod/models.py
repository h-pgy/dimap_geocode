from enum import StrEnum

from pydantic import BaseModel, Field

from services.domain.geometry import GeoFeature, PointGeometry
from services.domain.logradouro import Logradouro

from .numeracao import Paridade


class Lado(StrEnum):
    """De que lado do eixo o ponto está, para quem segue o segmento no sentido em que a numeração cresce."""

    DIREITA = "direita"
    ESQUERDA = "esquerda"


# A convenção de numeração do município: é ela que traduz lado em paridade.
PARIDADE_POR_LADO = {
    Lado.DIREITA: Paridade.PAR,
    Lado.ESQUERDA: Paridade.IMPAR,
}


class AddressGeocodInput(BaseModel):
    codlog: str                 # repassado ao LogradouroGeocodInput (que valida a forma)
    numero: int = Field(gt=0)   # número do imóvel, já parseado (int) upstream
    layer_name: str             # camada de logradouros (settings, via orquestração)
    interpolation_crs: int      # CRS projetado p/ interpolar (ex.: 31983), via orquestração
    output_crs: int             # CRS de saída (ex.: 4326), via orquestração


class EnderecoAttributes(BaseModel):
    """Proveniência do ponto geocodificado (camada `attributes` da feature)."""
    logradouro: Logradouro
    numero: int
    id_segmento: str            # segmento que originou a interpolação
    # faixa do lado (par/ímpar) do segmento escolhido, no dia da geocodificação
    numeracao_inicial: int
    numeracao_final: int


EnderecoFeature = GeoFeature[PointGeometry, EnderecoAttributes]
