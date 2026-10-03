from typing import Self

from pydantic import BaseModel, Field, computed_field, model_validator

from services.domain.geometry import para_geos, reprojetar
from services.domain.logradouro import Logradouro

from .models import SegmentoLogradouroFeature


class FaixaNumeracao(BaseModel):
    """O menor e o maior número do logradouro inteiro: os dois lados de todos os segmentos."""

    menor: int = Field(gt=0)
    maior: int = Field(gt=0)


class GavetaLogradouro(BaseModel):
    """O logradouro como a gaveta o apresenta: a identidade e o que se apura no conjunto dos segmentos."""

    logradouro: Logradouro
    extensao_m: float = Field(ge=0)
    quantidade_segmentos: int = Field(ge=1)
    numeracao: FaixaNumeracao | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def extensao_km(self) -> float:
        return self.extensao_m / 1000


class GavetaLogradouroInput(BaseModel):
    segmentos: list[SegmentoLogradouroFeature] = Field(min_length=1)
    crs_metrico: int

    # A identidade vem do primeiro segmento: dois logradouros dariam o nome de um com a medida dos dois.
    @model_validator(mode="after")
    def _um_so_logradouro(self) -> Self:
        codlogs = {segmento.attributes.codlog for segmento in self.segmentos}
        if len(codlogs) > 1:
            raise ValueError("Os segmentos são de mais de um logradouro.")
        return self


class MontarGavetaLogradouro:
    def __call__(self, entrada: GavetaLogradouroInput) -> GavetaLogradouro:
        return self.pipeline(entrada)

    def pipeline(self, entrada: GavetaLogradouroInput) -> GavetaLogradouro:
        return GavetaLogradouro(
            logradouro=entrada.segmentos[0].attributes.logradouro,
            extensao_m=self._extensao_m(entrada),
            quantidade_segmentos=len(entrada.segmentos),
            numeracao=self._numeracao(entrada.segmentos),
        )

    def _extensao_m(self, entrada: GavetaLogradouroInput) -> float:
        extensao_m = 0.0
        for segmento in entrada.segmentos:
            eixo = reprojetar(segmento.geometry, segmento.crs, entrada.crs_metrico)
            extensao_m += float(para_geos(eixo, entrada.crs_metrico).length)
        return extensao_m

    def _numeracao(self, segmentos: list[SegmentoLogradouroFeature]) -> FaixaNumeracao | None:
        numeros: list[int] = []
        for segmento in segmentos:
            a = segmento.attributes
            extremos = [
                a.numero_inicial_par,
                a.numero_final_par,
                a.numero_inicial_impar,
                a.numero_final_impar,
            ]
            # Zero é como a camada marca o lado sem numeração, não o número 0.
            numeros.extend(n for n in extremos if n)
        if not numeros:
            return None
        return FaixaNumeracao(menor=min(numeros), maior=max(numeros))
