from enum import StrEnum

from pydantic import BaseModel, Field, computed_field

from services.domain.geometry import para_geos, reprojetar

from .models import LoteAttributes, LoteFeature

LIMITE_ALERTA_PCT = 2.0
LIMITE_ERRO_PCT = 5.0


class DivergenciaArea(StrEnum):
    """Quanto a área do polígono se afasta da área de terreno declarada no cadastro."""

    TOLERAVEL = "toleravel"
    ALERTA = "alerta"
    ERRO = "erro"


class GavetaLote(BaseModel):
    """O lote como a gaveta o apresenta: os atributos do cadastro e o que se mede no polígono."""

    lote: LoteAttributes
    area_poligono_m2: float = Field(ge=0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def diferenca_area_pct(self) -> float | None:
        # Base no cadastro: positivo é polígono maior que o declarado.
        declarada = self.lote.area_terreno_m2
        if not declarada:
            return None
        return (self.area_poligono_m2 - declarada) * 100 / declarada

    @computed_field  # type: ignore[prop-decorator]
    @property
    def divergencia_area(self) -> DivergenciaArea | None:
        diferenca = self.diferenca_area_pct
        if diferenca is None:
            return None
        modulo = abs(diferenca)
        if modulo > LIMITE_ERRO_PCT:
            return DivergenciaArea.ERRO
        if modulo > LIMITE_ALERTA_PCT:
            return DivergenciaArea.ALERTA
        return DivergenciaArea.TOLERAVEL


class GavetaLoteInput(BaseModel):
    lote: LoteFeature
    crs_metrico: int


class MontarGavetaLote:
    def __call__(self, entrada: GavetaLoteInput) -> GavetaLote:
        return self.pipeline(entrada)

    def pipeline(self, entrada: GavetaLoteInput) -> GavetaLote:
        return GavetaLote(
            lote=entrada.lote.attributes,
            area_poligono_m2=self._area_poligono_m2(entrada),
        )

    def _area_poligono_m2(self, entrada: GavetaLoteInput) -> float:
        projetado = reprojetar(entrada.lote.geometry, entrada.lote.crs, entrada.crs_metrico)
        return float(para_geos(projetado, entrada.crs_metrico).area)
