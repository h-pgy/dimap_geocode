from services.integrations.wfs import WfsConnectionConfig, WfsFetcher
from services.utils.io import write_parquet_to_data

from .constants import ATRIBUTOS_ALVO
from .extractor import EnderecosFiscaisExtractor
from .models import EnderecoFiscal, EnderecosFiscaisRequest, EnderecosFiscaisResult

OUTPUT_FILENAME: str = "enderecos_fiscais.parquet"

__all__ = [
    "run",
    "OUTPUT_FILENAME",
    "EnderecosFiscaisExtractor",
    "EnderecosFiscaisRequest",
    "EnderecosFiscaisResult",
    "EnderecoFiscal",
]


def _to_columns(rows: list[EnderecoFiscal]) -> dict[str, list[str | None]]:
    cols: dict[str, list[str | None]] = {attr: [] for attr in ATRIBUTOS_ALVO}
    for row in rows:
        for attr in ATRIBUTOS_ALVO:
            cols[attr].append(getattr(row, attr))
    return cols


def run(
    config: WfsConnectionConfig,
    request: EnderecosFiscaisRequest,
    verbose: bool = False,
) -> EnderecosFiscaisResult:
    fetcher = WfsFetcher(config, verbose=verbose)
    rows = EnderecosFiscaisExtractor(fetcher)(request)

    output_path = write_parquet_to_data(_to_columns(rows), OUTPUT_FILENAME)

    return EnderecosFiscaisResult(
        total_records=len(rows),
        output_path=output_path,
    )
