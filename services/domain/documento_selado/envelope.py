from typing import Any

from .constants import CHAVES_RESERVADAS
from .models import EnvelopeAto


class MontarEnvelope:
    """Callable: o ato → os dados opacos do selo. Achatar, e não aninhar os extras sob uma chave, é
    o que faz `campos_publicos` poder nomear qualquer campo do envelope pelo mesmo caminho."""

    def __call__(self, ato: EnvelopeAto) -> dict[str, Any]:
        return self.pipeline(ato)

    def pipeline(self, ato: EnvelopeAto) -> dict[str, Any]:
        self._recusar_colisao(ato.extras)
        nucleo = ato.model_dump(mode="json", exclude={"extras"})
        return {**nucleo, **ato.extras}

    def _recusar_colisao(self, extras: dict[str, Any]) -> None:
        colididas = CHAVES_RESERVADAS & extras.keys()
        if colididas:
            raise ValueError(
                f"{sorted(colididas)} são do núcleo do envelope e não podem vir como extras da ação."
            )


montar_envelope = MontarEnvelope()
