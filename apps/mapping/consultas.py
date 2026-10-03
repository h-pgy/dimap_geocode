import json

from pydantic import BaseModel, field_validator

from services.domain.geometry import PointGeometry


class ConsultaSobrePonto(BaseModel):
    """A geometria que o envio.js enxertou. Linha e polígono viram ValidationError."""

    desenho: PointGeometry

    @field_validator("desenho", mode="before")
    @classmethod
    def _do_json(cls, valor: object) -> object:
        # Sem o envio.js o campo não chega: vira ValidationError e cai no middleware.
        return json.loads(valor) if isinstance(valor, str) else valor
