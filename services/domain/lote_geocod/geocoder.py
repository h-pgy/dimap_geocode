from collections.abc import Callable, Iterable

from services.integrations.wfs import (
    CqlFilter,
    CqlPredicate,
    WfsFeature,
    WfsFeatureCollection,
    WfsFeatureRequest,
)
from services.domain.geometry import PolygonGeometry

from .models import LoteAttributes, LoteFeature, LoteGeocodInput

WfsBatches = Callable[[WfsFeatureRequest], Iterable[WfsFeatureCollection]]

PAGE_SIZE: int = 10_000

_OPCIONAIS: dict[str, str] = {
    "cd_tipo_quadra": "tipo_quadra",
    "cd_condominio": "condominio",
}


def _as_str(value: object) -> str | None:
    return None if value is None else str(value)


class LoteGeocoder:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, entrada: LoteGeocodInput) -> list[LoteFeature]:
        return self.pipeline(entrada)

    def pipeline(self, entrada: LoteGeocodInput) -> list[LoteFeature]:
        request = self._montar_request(entrada)
        lotes: list[LoteFeature] = []
        for page in self.fetcher(request):
            for feature in page.features:
                lote = self._feature_para_lote(feature, entrada.output_crs)
                if lote is not None:
                    lotes.append(lote)
        return lotes

    def _montar_request(self, entrada: LoteGeocodInput) -> WfsFeatureRequest:
        return WfsFeatureRequest(
            nome_camada=entrada.layer_name,
            cql_filter=CqlFilter(
                logic="AND",
                predicates=[
                    CqlPredicate(field="cd_setor_fiscal", op="=", value=entrada.setor),
                    CqlPredicate(field="cd_quadra_fiscal", op="=", value=entrada.quadra),
                    CqlPredicate(field="cd_lote", op="=", value=entrada.lote),
                    CqlPredicate(field="cd_tipo_lote", op="=", value=entrada.tipo_lote),
                ],
            ),
            srs_name=f"EPSG:{entrada.output_crs}",
            count=PAGE_SIZE,
        )

    def _feature_para_lote(self, feature: WfsFeature, output_crs: int) -> LoteFeature | None:
        props = feature.properties
        id_poligono = _as_str(props.get("cd_identificador"))
        setor = _as_str(props.get("cd_setor_fiscal"))
        quadra = _as_str(props.get("cd_quadra_fiscal"))
        lote = _as_str(props.get("cd_lote"))
        tipo_lote = _as_str(props.get("cd_tipo_lote"))
        if not (feature.geometry and id_poligono and setor and quadra and lote and tipo_lote):
            return None
        try:
            geometry = PolygonGeometry.model_validate(feature.geometry.model_dump())
        except Exception:
            return None
        return LoteFeature(
            geometry=geometry,
            attributes=self._montar_attributes(
                props, id_poligono, setor, quadra, lote, tipo_lote
            ),
            crs=output_crs,
        )

    def _montar_attributes(
        self,
        props: dict[str, object],
        id_poligono: str,
        setor: str,
        quadra: str,
        lote: str,
        tipo_lote: str,
    ) -> LoteAttributes:
        return LoteAttributes(
            id_poligono=id_poligono,
            setor=setor,
            quadra=quadra,
            lote=lote,
            tipo_lote=tipo_lote,
            **{campo: _as_str(props.get(origem)) for origem, campo in _OPCIONAIS.items()},
        )
