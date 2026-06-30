from collections.abc import Callable, Iterable

from services.integrations.wfs import (
    WfsFeatureCollection,
    WfsFeatureRequest,
    WfsFeature,
    utils,
)
from services.domain.geometry import LineGeometry

from .models import (
    LogradouroGeocodInput,
    SegmentoLogradouroAttributes,
    SegmentoLogradouroFeature,
)

WfsBatches = Callable[[WfsFeatureRequest], Iterable[WfsFeatureCollection]]

PAGE_SIZE: int = 10_000


def _as_str(value: object) -> str | None:
    return None if value is None else str(value)


def _as_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(value)  # type: ignore[call-overload]


class LogradouroGeocoder:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, entrada: LogradouroGeocodInput) -> list[SegmentoLogradouroFeature]:
        return self.pipeline(entrada)

    def pipeline(self, entrada: LogradouroGeocodInput) -> list[SegmentoLogradouroFeature]:
        request = self._montar_request(entrada)
        segmentos: list[SegmentoLogradouroFeature] = []
        for page in self.fetcher(request):
            for feature in page.features:
                segmento = self._feature_para_segmento(feature, entrada.output_crs)
                if segmento is not None:
                    segmentos.append(segmento)
        return segmentos

    def _montar_request(self, entrada: LogradouroGeocodInput) -> WfsFeatureRequest:
        return WfsFeatureRequest(
            nome_camada=entrada.layer_name,
            cql_filter=utils.cql_eq("codlog", entrada.codlog_int),
            srs_name=f"EPSG:{entrada.output_crs}",
            count=PAGE_SIZE,
        )

    def _feature_para_segmento(
        self, feature: WfsFeature, output_crs: int
    ) -> SegmentoLogradouroFeature | None:
        props = feature.properties
        id_segmento = _as_str(props.get("cd_identificador"))
        codlog = _as_str(props.get("codlog"))
        cd_tipo = _as_str(props.get("cd_tipo_logradouro"))
        nome = _as_str(props.get("nm_logradouro"))
        if not (feature.geometry and id_segmento and codlog and cd_tipo and nome):
            return None
        try:
            geometry = LineGeometry.model_validate(feature.geometry.model_dump())
        except Exception:
            return None
        return SegmentoLogradouroFeature(
            geometry=geometry,
            attributes=self._montar_attributes(props, id_segmento, codlog, cd_tipo, nome),
            crs=output_crs,
        )

    def _montar_attributes(
        self,
        props: dict[str, object],
        id_segmento: str,
        codlog: str,
        cd_tipo: str,
        nome: str,
    ) -> SegmentoLogradouroAttributes:
        return SegmentoLogradouroAttributes(
            id_segmento=id_segmento,
            codlog=codlog,
            cd_tipo_logradouro=cd_tipo,
            nome_logradouro=nome,
            titulo=_as_str(props.get("cd_titulo_logradouro")),
            preposicao=_as_str(props.get("tx_preposicao_logradouro")),
            numero_inicial_par=_as_int(props.get("cd_numero_inicial_par")),
            numero_final_par=_as_int(props.get("cd_numero_final_par")),
            numero_inicial_impar=_as_int(props.get("cd_numero_inicial_impar")),
            numero_final_impar=_as_int(props.get("cd_numero_final_impar")),
        )
