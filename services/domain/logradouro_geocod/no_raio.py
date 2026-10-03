from django.contrib.gis.geos import GEOSGeometry

from services.domain.geometry import para_geos, reprojetar
from services.integrations.wfs import CqlDWithin, CqlFilter, WfsFeatureRequest

from .geocoder import WfsBatches, feature_para_segmento
from .models import SegmentoProximo, SegmentosNoRaioInput


class SegmentosNoRaio:
    """Os segmentos de logradouro a até `raio_m` do ponto, do mais perto ao mais longe."""

    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, entrada: SegmentosNoRaioInput) -> tuple[SegmentoProximo, ...]:
        return self.pipeline(entrada)

    def pipeline(self, entrada: SegmentosNoRaioInput) -> tuple[SegmentoProximo, ...]:
        ponto_metrico = reprojetar(entrada.ponto, entrada.crs_ponto, entrada.crs_metrico)
        ponto = para_geos(ponto_metrico, entrada.crs_metrico)
        request = self._montar_request(ponto, entrada)
        proximos = self._medir(request, ponto, entrada.crs_metrico)
        return tuple(sorted(proximos, key=lambda proximo: proximo.distancia_m))

    def _montar_request(
        self,
        ponto: GEOSGeometry,
        entrada: SegmentosNoRaioInput,
    ) -> WfsFeatureRequest:
        return WfsFeatureRequest(
            nome_camada=entrada.layer_name,
            srs_name=f"EPSG:{entrada.crs_metrico}",
            cql_filter=CqlFilter(
                predicates=[
                    CqlDWithin(
                        field=entrada.campo_geometria,
                        wkt=f"POINT({ponto.x} {ponto.y})",  # type: ignore[attr-defined]
                        distancia_m=entrada.raio_m,
                    ),
                ],
            ),
        )

    def _medir(
        self,
        request: WfsFeatureRequest,
        ponto: GEOSGeometry,
        crs_metrico: int,
    ) -> list[SegmentoProximo]:
        proximos: list[SegmentoProximo] = []
        for page in self.fetcher(request):
            for feature in page.features:
                segmento = feature_para_segmento(feature, crs_metrico)
                if segmento is None:
                    continue
                # Distância medida no GEOS: o servidor só garante "dentro do raio", não diz quanto.
                eixo = para_geos(segmento.geometry, crs_metrico)
                distancia_m = eixo.distance(ponto)
                proximos.append(SegmentoProximo(segmento=segmento, distancia_m=distancia_m))
        return proximos
