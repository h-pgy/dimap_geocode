from services.integrations.wfs import WfsConnectionConfig, WfsFetcher, WfsRetryPolicy
from services.utils.io import write_parquet_to_data

from .extractor import SegmentosLogradourosExtractor
from .models import SegmentoLogradouro, SegmentosLogradourosRequest, SegmentosLogradourosResult

OUTPUT_FILENAME: str = "segmentos_logradouros.parquet"

__all__ = [
    "run",
    "OUTPUT_FILENAME",
    "SegmentosLogradourosExtractor",
    "SegmentosLogradourosRequest",
    "SegmentosLogradourosResult",
    "SegmentoLogradouro",
]


def _to_columns(rows: list[SegmentoLogradouro]) -> dict[str, list[str | None]]:
    return {
        "codlog": [r.codlog for r in rows],
        "cd_identificador": [r.cd_identificador for r in rows],
        "cd_numero_inicial_par": [r.cd_numero_inicial_par for r in rows],
        "cd_numero_final_par": [r.cd_numero_final_par for r in rows],
        "cd_numero_inicial_impar": [r.cd_numero_inicial_impar for r in rows],
        "cd_numero_final_impar": [r.cd_numero_final_impar for r in rows],
    }


def run(
    config: WfsConnectionConfig,
    request: SegmentosLogradourosRequest,
    retry_policy: WfsRetryPolicy | None = None,
    verbose: bool = False,
) -> SegmentosLogradourosResult:
    fetcher = WfsFetcher(config, retry_policy=retry_policy, verbose=verbose)
    rows = SegmentosLogradourosExtractor(fetcher)(request)

    output_path = write_parquet_to_data(_to_columns(rows), OUTPUT_FILENAME)

    return SegmentosLogradourosResult(
        total_segments=len(rows),
        output_path=output_path,
    )
