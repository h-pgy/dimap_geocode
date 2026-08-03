from services.integrations.wfs import WfsFetcher
from services.scripts.contrato import ScriptRunner
from services.utils.io import write_parquet_to_data
from services.utils.metadados import registrar_execucao

from .extractor import SegmentosLogradourosExtractor
from .models import SegmentoLogradouro, SegmentosLogradourosConfig, SegmentosLogradourosResult

OUTPUT_FILENAME: str = "segmentos_logradouros.parquet"


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
    config: SegmentosLogradourosConfig,
    *,
    verbose: bool = False,
    manual: bool = True,
) -> SegmentosLogradourosResult:
    with registrar_execucao(OUTPUT_FILENAME, manual=manual) as registro:
        fetcher = WfsFetcher(config.conexao, retry_policy=config.retry, verbose=verbose)
        rows = SegmentosLogradourosExtractor(fetcher)(config)

        output_path = write_parquet_to_data(_to_columns(rows), OUTPUT_FILENAME)
        registro.sucesso(registros=len(rows))

    return SegmentosLogradourosResult(
        total_segments=len(rows),
        output_path=output_path,
    )


_contrato: ScriptRunner[SegmentosLogradourosConfig, SegmentosLogradourosResult] = run
