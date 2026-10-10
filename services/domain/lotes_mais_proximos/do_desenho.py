from typing import Self

from pydantic import BaseModel, Field, model_validator

from services.domain.desenho import Desenho, TipoDesenho
from services.domain.geometry import PolygonGeometry, para_geos, reprojetar
from services.domain.lote_geocod import LoteFeature, feature_para_lote
from services.integrations.wfs import CqlFilter, CqlIntersects, WfsFeatureRequest

from .exceptions import DesenhoGrandeDemaisError, DesenhoInvalidoError
from .mais_proximo import WfsBatches
from .models import CamadaLotes, LotesDoDesenho

PAGE_SIZE: int = 10_000


class LotesDoDesenhoInput(BaseModel):
    desenho: Desenho
    crs_mapa: int  # o desenho não carrega CRS: vem do mapa, pela orquestração
    camada: CamadaLotes
    area_maxima_m2: float = Field(gt=0)

    @model_validator(mode="after")
    def _so_poligono(self) -> Self:
        if self.desenho.tipo is not TipoDesenho.POLIGONO:
            raise ValueError("A busca de lotes precisa de um polígono.")
        return self


class ConferenciaDesenhoInput(BaseModel):
    geometria: PolygonGeometry
    crs_mapa: int
    crs_metrico: int
    area_maxima_m2: float = Field(gt=0)


class DesenhoConferido(BaseModel):
    projetado: PolygonGeometry  # no CRS métrico
    area_m2: float = Field(gt=0)


def _wkt(poligono: PolygonGeometry, crs: int) -> str:
    # O GEOS escreve "POLYGON ((": colado, o WKT tem a mesma grafia do POINT( da consulta vizinha.
    return para_geos(poligono, crs).wkt.replace(" (", "(", 1)


class ConferirDesenho:
    """Recusa o polígono que o GeoServer não deve receber: laço que se cruza ou área acima do corte."""

    def __call__(self, entrada: ConferenciaDesenhoInput) -> DesenhoConferido:
        return self.pipeline(entrada)

    def pipeline(self, entrada: ConferenciaDesenhoInput) -> DesenhoConferido:
        projetado = reprojetar(entrada.geometria, entrada.crs_mapa, entrada.crs_metrico)
        geos = para_geos(projetado, entrada.crs_metrico)
        if not geos.valid:
            raise DesenhoInvalidoError(geos.valid_reason)
        if geos.area > entrada.area_maxima_m2:
            raise DesenhoGrandeDemaisError(geos.area, entrada.area_maxima_m2)
        return DesenhoConferido(projetado=projetado, area_m2=geos.area)


class BuscarLotesDoDesenho:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher
        self._conferir = ConferirDesenho()

    def __call__(self, entrada: LotesDoDesenhoInput) -> LotesDoDesenho:
        return self.pipeline(entrada)

    def pipeline(self, entrada: LotesDoDesenhoInput) -> LotesDoDesenho:
        # A conferência vem antes da rede: o GeoServer não paga por desenho que vai ser recusado.
        conferido = self._conferir(
            ConferenciaDesenhoInput(
                geometria=entrada.desenho.geometria,  # type: ignore[arg-type]
                crs_mapa=entrada.crs_mapa,
                crs_metrico=entrada.camada.crs_camada,
                area_maxima_m2=entrada.area_maxima_m2,
            )
        )
        lotes = self._consultar(conferido.projetado, entrada.camada)
        return LotesDoDesenho(
            desenho=entrada.desenho,
            area_m2=conferido.area_m2,
            lotes=lotes,
        )

    def _consultar(self, projetado: PolygonGeometry, camada: CamadaLotes) -> tuple[LoteFeature, ...]:
        request = WfsFeatureRequest(
            nome_camada=camada.nome,
            # A intersecção é do servidor; a saída já vem no CRS do mapa.
            srs_name=f"EPSG:{camada.crs_saida}",
            cql_filter=CqlFilter(
                predicates=[
                    CqlIntersects(
                        field=camada.campo_geometria,
                        wkt=_wkt(projetado, camada.crs_camada),
                    ),
                ]
            ),
            count=PAGE_SIZE,
        )
        return tuple(
            lote
            for page in self.fetcher(request)
            for feature in page.features
            if (lote := feature_para_lote(feature, camada.crs_saida)) is not None
        )
