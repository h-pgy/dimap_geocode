from collections.abc import Callable, Iterable

from services.integrations.wfs import WfsFeatureCollection, WfsFeatureRequest

from .models import LogradouroNome, NomesLogradourosRequest

PROPERTY_NAMES: list[str] = ["codlog", "cd_tipo_logradouro", "nm_logradouro"]
PAGE_SIZE: int = 10_000

WfsBatches = Callable[[WfsFeatureRequest], Iterable[WfsFeatureCollection]]


def _as_str(value: object) -> str:
    return "" if value is None else str(value)


class NomesLogradourosExtractor:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, request: NomesLogradourosRequest) -> list[LogradouroNome]:
        wfs_request = WfsFeatureRequest(
            nome_camada=request.layer_name,
            property_names=PROPERTY_NAMES,
            count=PAGE_SIZE,
        )
        seen: set[tuple[str, str, str]] = set()

        for page in self.fetcher(wfs_request):
            for feature in page.features:
                props = feature.properties
                codlog = props.get("codlog")
                if codlog is None:
                    continue
                seen.add((
                    str(codlog),
                    _as_str(props.get("cd_tipo_logradouro")),
                    _as_str(props.get("nm_logradouro")),
                ))

        return [
            LogradouroNome(codlog=c, cd_tipo_logradouro=t, nm_logradouro=n)
            for c, t, n in sorted(seen, key=lambda k: (k[0], k[2]))
        ]
