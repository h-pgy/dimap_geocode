from services.scripts.contrato import ScriptRunner
from services.utils.metadados import registrar_execucao

from .models import TraducaoTitulosConfig, TraducaoTitulosStats
from .traducao_titulos_logradouro import pipeline


def run(
    config: TraducaoTitulosConfig,
    *,
    verbose: bool = False,
    manual: bool = True,
) -> TraducaoTitulosStats:
    with registrar_execucao(config.output_parquet_name, manual=manual) as registro:
        stats = pipeline(config)
        registro.sucesso(registros=stats.n_titulos)

    return stats


_contrato: ScriptRunner[TraducaoTitulosConfig, TraducaoTitulosStats] = run
