from collections.abc import Callable, Iterable

from services.integrations import wfs
from services.integrations.wfs import WfsFeatureCollection, WfsFeatureRequest

from .constants import ATRIBUTOS_ALVO
from .models import EnderecoFiscal, EnderecosFiscaisRequest

PAGE_SIZE: int = 10_000

WfsBatches = Callable[[WfsFeatureRequest], Iterable[WfsFeatureCollection]]


class EnderecosFiscaisExtractor:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, request: EnderecosFiscaisRequest) -> list[EnderecoFiscal]:
        wfs_request = WfsFeatureRequest(
            nome_camada=request.layer_name,
            property_names=ATRIBUTOS_ALVO,
            count=PAGE_SIZE,
            cql_filter=wfs.utils.cql_eq("cd_situacao", 1),
        )
        records: list[EnderecoFiscal] = []

        for page in self.fetcher(wfs_request):
            for feature in page.features:
                props = feature.properties

                if props.get("cd_identificador") is None:
                    continue

                kwargs = {
                    k: str(props.get(k)) if props.get(k) is not None else None
                    for k in ATRIBUTOS_ALVO
                }
                records.append(EnderecoFiscal(**kwargs))

        return sorted(records, key=lambda x: x.cd_identificador)