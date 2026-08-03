from services.scripts.contrato import ScriptRunner
from services.utils.metadados import registrar_execucao

from .augment_tipos_logradouro import pipeline
from .models import AugmentConfig, AugmentStats


def run(config: AugmentConfig, *, verbose: bool = False, manual: bool = True) -> AugmentStats:
    with registrar_execucao(config.output_parquet_name, manual=manual) as registro:
        stats = pipeline(config, verbose=verbose)
        registro.sucesso(registros=stats.n_total)

    return stats


_contrato: ScriptRunner[AugmentConfig, AugmentStats] = run
