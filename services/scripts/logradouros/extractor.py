from collections.abc import Callable, Iterable

from services.integrations.wfs import WfsFeatureCollection, WfsFeatureRequest

from .models import LogradouroNome, NomesLogradourosConfig

PROPERTY_NAMES: list[str] = [
    "codlog",
    "cd_tipo_logradouro",
    "cd_titulo_logradouro",
    "tx_preposicao_logradouro",
    "nm_logradouro",
]
PAGE_SIZE: int = 10_000

WfsBatches = Callable[[WfsFeatureRequest], Iterable[WfsFeatureCollection]]


def _as_str(value: object) -> str:
    return "" if value is None else str(value)


def _opcional(value: object) -> str | None:
    # A camada manda título e preposição em branco em algumas linhas: em branco é ausência.
    texto = "" if value is None else str(value).strip()
    return texto or None


class NomesLogradourosExtractor:
    def __init__(self, fetcher: WfsBatches) -> None:
        self.fetcher = fetcher

    def __call__(self, request: NomesLogradourosConfig) -> list[LogradouroNome]:
        wfs_request = WfsFeatureRequest(
            nome_camada=request.layer_name,
            property_names=PROPERTY_NAMES,
            count=PAGE_SIZE,
        )
        seen: set[tuple[str, str, str | None, str | None, str]] = set()

        for page in self.fetcher(wfs_request):
            for feature in page.features:
                props = feature.properties
                codlog = props.get("codlog")
                if codlog is None:
                    continue
                seen.add((
                    str(codlog),
                    _as_str(props.get("cd_tipo_logradouro")),
                    _opcional(props.get("cd_titulo_logradouro")),
                    _opcional(props.get("tx_preposicao_logradouro")),
                    _as_str(props.get("nm_logradouro")),
                ))

        return [
            LogradouroNome(codlog=c, tipo_logradouro=t, titulo=ti, preposicao=p, nm_logradouro=n)
            for c, t, ti, p, n in sorted(seen, key=lambda k: (k[0], k[4]))
        ]
