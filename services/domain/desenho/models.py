from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from services.domain.geometry import LineGeometry, PointGeometry, PolygonGeometry


class TipoDesenho(StrEnum):
    PONTO = "ponto"
    LINHA = "linha"
    POLIGONO = "poligono"


TIPO_POR_GEOMETRIA = {
    "Point": TipoDesenho.PONTO,
    "LineString": TipoDesenho.LINHA,
    "MultiLineString": TipoDesenho.LINHA,
    "Polygon": TipoDesenho.POLIGONO,
    "MultiPolygon": TipoDesenho.POLIGONO,
}


class Desenho(BaseModel):
    """Um traço da bancada, no CRS do mapa. `id_bancada` é a camada no mapa: é o que liga a linha da
    lista ao traço destacado."""

    model_config = ConfigDict(frozen=True)

    id_bancada: str = Field(pattern=r"^\d+$")
    geometria: PointGeometry | LineGeometry | PolygonGeometry

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tipo(self) -> TipoDesenho:
        return TIPO_POR_GEOMETRIA[self.geometria.type]


class Grandeza(StrEnum):
    AREA = "area"
    COMPRIMENTO = "comprimento"


class Medida(BaseModel):
    """Quanto o traço mede. Guardada: depende do CRS métrico, que não mora no desenho."""

    grandeza: Grandeza
    valor: float = Field(gt=0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def unidade(self) -> str:
        return "m²" if self.grandeza is Grandeza.AREA else "m"


class Eixo(StrEnum):
    LATITUDE = "latitude"
    LONGITUDE = "longitude"


class Hemisferio(StrEnum):
    NORTE = "N"
    SUL = "S"
    LESTE = "L"
    OESTE = "O"


HEMISFERIOS = {
    Eixo.LATITUDE: (Hemisferio.NORTE, Hemisferio.SUL),
    Eixo.LONGITUDE: (Hemisferio.LESTE, Hemisferio.OESTE),
}
MILESIMOS_POR_GRAU = 3_600_000
MILESIMOS_POR_MINUTO = 60_000


class Coordenada(BaseModel):
    """Um eixo da posição, em graus decimais com sinal. Graus, minutos e segundos saem arredondados ao
    milésimo de segundo."""

    eixo: Eixo
    graus_decimais: float = Field(ge=-180, le=180)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def hemisferio(self) -> Hemisferio:
        positivo, negativo = HEMISFERIOS[self.eixo]
        return negativo if self.graus_decimais < 0 else positivo

    # Arredondar cada parte à parte deixaria 59,9997″ virar 60,000″.
    @property
    def _milesimos(self) -> int:
        return round(abs(self.graus_decimais) * MILESIMOS_POR_GRAU)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def graus(self) -> int:
        return self._milesimos // MILESIMOS_POR_GRAU

    @computed_field  # type: ignore[prop-decorator]
    @property
    def minutos(self) -> int:
        return self._milesimos % MILESIMOS_POR_GRAU // MILESIMOS_POR_MINUTO

    @computed_field  # type: ignore[prop-decorator]
    @property
    def segundos(self) -> float:
        return self._milesimos % MILESIMOS_POR_MINUTO / 1000


class Posicao(BaseModel):
    """Onde o ponto está, no CRS geográfico. Guardada: depende do CRS, que não mora no desenho."""

    latitude: Coordenada
    longitude: Coordenada


class DesenhoMedido(BaseModel):
    desenho: Desenho
    medida: Medida | None = None
    posicao: Posicao | None = None


class PocoDesenhos(BaseModel):
    """Um poço da gaveta: os desenhos de um tipo e qual deles está marcado."""

    tipo: TipoDesenho
    desenhos: tuple[DesenhoMedido, ...] = Field(min_length=1)
    id_selecionado: str

    @model_validator(mode="after")
    def _selecionado_esta_no_poco(self) -> Self:
        if self.id_selecionado not in {m.desenho.id_bancada for m in self.desenhos}:
            raise ValueError("O desenho selecionado não está no poço.")
        return self


class GavetaDesenhos(BaseModel):
    """O que a gaveta mostra: um poço por tipo com desenho, na ordem da bancada."""

    pocos: tuple[PocoDesenhos, ...] = ()
