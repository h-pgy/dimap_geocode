from services.integrations.wfs import WfsFetcher
from services.scripts.contrato import ScriptRunner
from services.utils.io import write_parquet_to_data

from .constants import ATRIBUTOS_ALVO
from .extractor import EnderecosFiscaisExtractor
from .models import EnderecoFiscal, EnderecosFiscaisConfig, EnderecosFiscaisResult

OUTPUT_FILENAME: str = "enderecos_fiscais.parquet"


def _to_columns(rows: list[EnderecoFiscal]) -> dict[str, list[str | None]]:
    cols: dict[str, list[str | None]] = {attr: [] for attr in ATRIBUTOS_ALVO}
    for row in rows:
        for attr in ATRIBUTOS_ALVO:
            cols[attr].append(getattr(row, attr))
    return cols


def run(config: EnderecosFiscaisConfig, *, verbose: bool = False) -> EnderecosFiscaisResult:
    fetcher = WfsFetcher(config.conexao, retry_policy=config.retry, verbose=verbose)
    rows = EnderecosFiscaisExtractor(fetcher)(config)

    output_path = write_parquet_to_data(_to_columns(rows), OUTPUT_FILENAME)

    return EnderecosFiscaisResult(
        total_records=len(rows),
        output_path=output_path,
    )


_contrato: ScriptRunner[EnderecosFiscaisConfig, EnderecosFiscaisResult] = run
