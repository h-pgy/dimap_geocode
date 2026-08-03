from services.scripts.contrato import ScriptRunner

from .augment_tipos_logradouro import pipeline
from .models import AugmentConfig, AugmentStats


def run(config: AugmentConfig, *, verbose: bool = False) -> AugmentStats:
    return pipeline(config, verbose=verbose)


_contrato: ScriptRunner[AugmentConfig, AugmentStats] = run
