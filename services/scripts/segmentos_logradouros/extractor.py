from collections.abc import Callable, Iterable

from services.integrations.wfs import WfsFeatureCollection, WfsFeatureRequest

from .models import SegmentoLogradouro, SegmentosLogradourosRequest

PROPERTY_NAMES: list[str] = [
    "codlog",
    "cd_identificador",
    "cd_numero_inicial_par",
    "cd_numero_final_par",
    "cd_numero_inicial_impar",
    "cd_numero_final_impar",
]
PAGE_SIZE: int = 10_000

WfsBatches = Callable[[WfsFeatureRequest], Iterable[WfsFeatureCollection]]


def _as_str(value: object) -> str | None:
    return None if value is None else str(value)


class SegmentosLogradourosExtractor:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, request: SegmentosLogradourosRequest) -> list[SegmentoLogradouro]:
        wfs_request = WfsFeatureRequest(
            nome_camada=request.layer_name,
            property_names=PROPERTY_NAMES,
            count=PAGE_SIZE,
        )
        records: list[SegmentoLogradouro] = []

        for page in self.fetcher(wfs_request):
            for feature in page.features:
                props = feature.properties
                codlog = props.get("codlog")
                cd_identificador = props.get("cd_identificador")
                if codlog is None or cd_identificador is None:
                    continue
                records.append(SegmentoLogradouro.model_validate(
                    {name: _as_str(props.get(name)) for name in PROPERTY_NAMES}
                ))

        return sorted(records, key=lambda x: (x.codlog, x.cd_identificador))
