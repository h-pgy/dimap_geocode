from django.contrib.gis.geos import GEOSGeometry
from pydantic import BaseModel, ConfigDict, Field

from .models import TipoDespacho


class SugestaoDespachoInput(BaseModel):
    """O desenho e os lotes que restaram, já no CRS métrico: a fração é razão de áreas."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    desenho: GEOSGeometry
    lotes: tuple[GEOSGeometry, ...] = Field(min_length=1)
    fracao_minima_contida: float = Field(gt=0, le=1)


class SugerirTipoDespacho:
    def __call__(self, entrada: SugestaoDespachoInput) -> TipoDespacho:
        return self.pipeline(entrada)

    def pipeline(self, entrada: SugestaoDespachoInput) -> TipoDespacho:
        if all(self._eh_contido(lote, entrada) for lote in entrada.lotes):
            return TipoDespacho.LANCAMENTO_EM_MAIOR_AREA
        return TipoDespacho.LANCAMENTO_PARCIAL

    def _eh_contido(self, lote: GEOSGeometry, entrada: SugestaoDespachoInput) -> bool:
        # A divisa desenhada à mão nunca bate no centímetro com a do cadastro: `contains` puro
        # jogaria em "parcial" todo desenho feito rente aos lotes.
        fracao_contida = lote.intersection(entrada.desenho).area / lote.area
        return bool(fracao_contida >= entrada.fracao_minima_contida)
