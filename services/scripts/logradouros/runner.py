from services.integrations.wfs import WfsConnectionConfig, WfsFetcher, WfsRetryPolicy
from services.utils.io import write_parquet_to_data

from .extractor import NomesLogradourosExtractor
from .models import LogradouroNome, NomesLogradourosRequest, NomesLogradourosResult

OUTPUT_FILENAME: str = "nomes_logradouros.parquet"


def _to_columns(rows: list[LogradouroNome]) -> dict[str, list[str]]:
    return {
        "codlog": [r.codlog for r in rows],
        "cd_tipo_logradouro": [r.tipo_logradouro for r in rows],
        "nm_logradouro": [r.nm_logradouro for r in rows],
    }


def run(
    config: WfsConnectionConfig,
    request: NomesLogradourosRequest,
    retry_policy: WfsRetryPolicy | None = None,
    verbose: bool = False,
) -> NomesLogradourosResult:
    fetcher = WfsFetcher(config, retry_policy=retry_policy, verbose=verbose)
    rows = NomesLogradourosExtractor(fetcher)(request)

    output_path = write_parquet_to_data(_to_columns(rows), OUTPUT_FILENAME)

    return NomesLogradourosResult(
        total_unique=len(rows),
        output_path=output_path,
    )
