from django.contrib.gis.geos import GEOSGeometry

from services.domain.geometry import para_geos, reprojetar
from services.domain.lote_geocod import feature_para_lote
from services.integrations.wfs import CqlDWithin, CqlFilter, WfsFeatureRequest

from .exceptions import NenhumLoteNoRaioError
from .mais_proximo import WfsBatches
from .models import CamadaLotes, LoteMaisProximoDoPontoInput, LoteProximo


class LoteMaisProximoDoPonto:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, entrada: LoteMaisProximoDoPontoInput) -> LoteProximo:
        return self.pipeline(entrada)

    def pipeline(self, entrada: LoteMaisProximoDoPontoInput) -> LoteProximo:
        camada = entrada.camada
        ponto_camada = reprojetar(entrada.ponto, camada.crs_saida, camada.crs_camada)
        ponto = para_geos(ponto_camada, camada.crs_camada)
        request = self._montar_request(ponto, entrada)
        candidatos = self._candidatos(request, ponto, camada.crs_camada)
        if not candidatos:
            raise NenhumLoteNoRaioError(entrada.raio_m)
        escolhido = min(candidatos, key=lambda c: c.distancia_m)
        return self._para_saida(escolhido, camada)

    def _montar_request(
        self,
        ponto: GEOSGeometry,
        entrada: LoteMaisProximoDoPontoInput,
    ) -> WfsFeatureRequest:
        # Sem codlog oficial, qualquer lote perto do ponto concorre: o raio é o único recorte.
        return WfsFeatureRequest(
            nome_camada=entrada.camada.nome,
            srs_name=f"EPSG:{entrada.camada.crs_camada}",
            cql_filter=CqlFilter(
                predicates=[
                    CqlDWithin(
                        field=entrada.camada.campo_geometria,
                        wkt=f"POINT({ponto.x} {ponto.y})",  # type: ignore[attr-defined]
                        distancia_m=entrada.raio_m,
                    ),
                ],
            ),
        )

    def _candidatos(
        self,
        request: WfsFeatureRequest,
        ponto: GEOSGeometry,
        crs: int,
    ) -> list[LoteProximo]:
        # Distância medida no GEOS, no CRS métrico: o servidor só garante "dentro do raio".
        candidatos: list[LoteProximo] = []
        for page in self.fetcher(request):
            for feature in page.features:
                lote = feature_para_lote(feature, crs)
                if lote is None:
                    continue
                distancia_m = para_geos(lote.geometry, crs).distance(ponto)
                candidatos.append(LoteProximo(lote=lote, distancia_m=distancia_m))
        return candidatos

    def _para_saida(self, escolhido: LoteProximo, camada: CamadaLotes) -> LoteProximo:
        # Reprojeta o polígono vencedor, e só ele, para o CRS do mapa.
        geometria_saida = reprojetar(escolhido.lote.geometry, camada.crs_camada, camada.crs_saida)
        lote_saida = escolhido.lote.model_copy(
            update={"geometry": geometria_saida, "crs": camada.crs_saida}
        )
        return LoteProximo(lote=lote_saida, distancia_m=escolhido.distancia_m)
