from services.integrations.wfs import WfsFetcher
from services.scripts.contrato import ScriptRunner
from services.utils.io import write_parquet_to_data
from services.utils.metadados import registrar_execucao

from .extractor import NomesLogradourosExtractor
from .models import LogradouroNome, NomesLogradourosConfig, NomesLogradourosResult

OUTPUT_FILENAME: str = "nomes_logradouros.parquet"


def _to_columns(rows: list[LogradouroNome]) -> dict[str, list[str]]:
    return {
        "codlog": [r.codlog for r in rows],
        "cd_tipo_logradouro": [r.tipo_logradouro for r in rows],
        "nm_logradouro": [r.nm_logradouro for r in rows],
    }


def run(
    config: NomesLogradourosConfig,
    *,
    verbose: bool = False,
    manual: bool = True,
) -> NomesLogradourosResult:
    with registrar_execucao(OUTPUT_FILENAME, manual=manual) as registro:
        fetcher = WfsFetcher(config.conexao, retry_policy=config.retry, verbose=verbose)
        rows = NomesLogradourosExtractor(fetcher)(config)

        output_path = write_parquet_to_data(_to_columns(rows), OUTPUT_FILENAME)
        registro.sucesso(registros=len(rows))

    return NomesLogradourosResult(
        total_unique=len(rows),
        output_path=output_path,
    )


_contrato: ScriptRunner[NomesLogradourosConfig, NomesLogradourosResult] = run
