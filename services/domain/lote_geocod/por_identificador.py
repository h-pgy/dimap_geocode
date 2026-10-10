from services.integrations.wfs import CqlFilter, CqlPredicate, WfsFeatureRequest

from .geocoder import WfsBatches, feature_para_lote
from .models import LoteFeature, LotePorIdentificadorInput


class LotePorIdentificador:
    """O lote pelo identificador do polígono; `None` quando ele já saiu da camada."""

    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, entrada: LotePorIdentificadorInput) -> LoteFeature | None:
        return self.pipeline(entrada)

    def pipeline(self, entrada: LotePorIdentificadorInput) -> LoteFeature | None:
        request = self._montar_request(entrada)
        for page in self.fetcher(request):
            for feature in page.features:
                lote = feature_para_lote(feature, entrada.output_crs)
                if lote is not None:
                    return lote
        return None

    def _montar_request(self, entrada: LotePorIdentificadorInput) -> WfsFeatureRequest:
        return WfsFeatureRequest(
            nome_camada=entrada.layer_name,
            cql_filter=CqlFilter(
                predicates=[
                    CqlPredicate(field="cd_identificador", op="=", value=entrada.id_poligono),
                ]
            ),
            srs_name=f"EPSG:{entrada.output_crs}",
            count=1,
        )
