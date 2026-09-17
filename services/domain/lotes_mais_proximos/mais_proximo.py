import json
from collections.abc import Callable, Iterable

from django.contrib.gis.geos import GEOSGeometry

from services.domain.geometry import PointGeometry, PolygonGeometry, reprojetar
from services.domain.lote_geocod import LoteFeature, feature_para_lote
from services.integrations.wfs import (
    CqlDWithin,
    CqlFilter,
    CqlPredicate,
    WfsFeatureCollection,
    WfsFeatureRequest,
)

from .exceptions import NenhumLoteProximoError
from .models import CamadaLotes, LoteMaisProximoInput, LoteProximo

WfsBatches = Callable[[WfsFeatureRequest], Iterable[WfsFeatureCollection]]


def _wkt(ponto: GEOSGeometry) -> str:
    return f"POINT({ponto.x} {ponto.y})"  # type: ignore[attr-defined]


class LoteMaisProximo:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, entrada: LoteMaisProximoInput) -> LoteProximo:
        return self.pipeline(entrada)

    def pipeline(self, entrada: LoteMaisProximoInput) -> LoteProximo:
        ponto_camada = reprojetar(entrada.ponto, entrada.camada.crs_saida, entrada.camada.crs_camada)
        ponto_geos = self._para_geos(ponto_camada, entrada.camada.crs_camada)
        request = self._montar_request(ponto_geos, entrada)
        candidatos = self._candidatos(request, ponto_geos, entrada.camada.crs_camada)
        if not candidatos:
            raise NenhumLoteProximoError(entrada.codlog, entrada.raio_m)
        # O codlog já filtrou no servidor, então nenhum vizinho de outra rua chega aqui.
        escolhido = min(candidatos, key=lambda c: c.distancia_m)
        return self._para_saida(escolhido, entrada.camada)

    def _para_geos(self, geometria: PointGeometry | PolygonGeometry, srid: int) -> GEOSGeometry:
        geos = GEOSGeometry(json.dumps(geometria.model_dump()))
        geos.srid = srid
        return geos

    def _montar_request(self, ponto: GEOSGeometry, entrada: LoteMaisProximoInput) -> WfsFeatureRequest:
        return WfsFeatureRequest(
            nome_camada=entrada.camada.nome,
            srs_name=f"EPSG:{entrada.camada.crs_camada}",
            cql_filter=CqlFilter(
                logic="AND",
                predicates=[
                    CqlDWithin(
                        field=entrada.camada.campo_geometria,
                        wkt=_wkt(ponto),
                        distancia_m=entrada.raio_m,
                    ),
                    CqlPredicate(field="cd_logradouro", op="=", value=entrada.codlog),
                ],
            ),
        )

    def _candidatos(
        self, request: WfsFeatureRequest, ponto: GEOSGeometry, crs_camada: int
    ) -> list[LoteProximo]:
        # Distância medida no GEOS, no CRS métrico: o servidor só garante "dentro do raio".
        candidatos: list[LoteProximo] = []
        for page in self.fetcher(request):
            for feature in page.features:
                lote = feature_para_lote(feature, crs_camada)
                if lote is None:
                    continue
                candidatos.append(
                    LoteProximo(lote=lote, distancia_m=self._distancia_m(lote, ponto, crs_camada))
                )
        return candidatos

    def _distancia_m(self, lote: LoteFeature, ponto: GEOSGeometry, crs_camada: int) -> float:
        poligono = self._para_geos(lote.geometry, crs_camada)
        return poligono.distance(ponto)

    def _para_saida(self, escolhido: LoteProximo, camada: CamadaLotes) -> LoteProximo:
        # Reprojeta o polígono vencedor, e só ele, para o CRS do mapa.
        geometria_saida = reprojetar(escolhido.lote.geometry, camada.crs_camada, camada.crs_saida)
        lote_saida = escolhido.lote.model_copy(
            update={"geometry": geometria_saida, "crs": camada.crs_saida}
        )
        return LoteProximo(lote=lote_saida, distancia_m=escolhido.distancia_m)
