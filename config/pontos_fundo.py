from pydantic import BaseModel, Field, RootModel, field_validator

# Bounding box do município de São Paulo (com folga), usada só para recusar ponto fora do
# território no boot — não é geometria: SPEC design/010 não usa polígono de município.
LAT_MINIMA = -24.05
LAT_MAXIMA = -23.35
LNG_MINIMA = -46.85
LNG_MAXIMA = -46.35


class PontoFundo(BaseModel):
    """Ponto do território paulistano que enquadra uma ortofoto de fundo."""

    descricao: str
    lat: float = Field(ge=LAT_MINIMA, le=LAT_MAXIMA)
    lng: float = Field(ge=LNG_MINIMA, le=LNG_MAXIMA)


class CatalogoPontosFundo(RootModel[dict[str, PontoFundo]]):
    """A chave é o nome do arquivo .png — é ela que liga o catálogo ao disco."""

    @field_validator("root")
    @classmethod
    def _catalogo_nao_vazio(cls, pontos: dict[str, PontoFundo]) -> dict[str, PontoFundo]:
        if not pontos:
            raise ValueError("o catálogo de pontos de fundo não pode ser vazio")
        return pontos
