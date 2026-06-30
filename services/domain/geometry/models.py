from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, model_validator

from .coordinates import eh_linha, eh_multilinha


class LineGeometry(BaseModel):
    """GeoJSON de linha vindo do WFS. Validação estrutural rasa da forma de `coordinates`
    (sem converter em objeto geométrico nem varrer todos os vértices)."""
    type: Literal["LineString", "MultiLineString"]
    coordinates: list[Any]

    @model_validator(mode="after")
    def _validar_forma(self) -> "LineGeometry":
        valida = eh_linha if self.type == "LineString" else eh_multilinha
        if not valida(self.coordinates):
            raise ValueError(f"coordinates não tem a forma de {self.type}")
        return self


GeomT = TypeVar("GeomT", bound=BaseModel)
AttrT = TypeVar("AttrT", bound=BaseModel)


class GeoFeature(BaseModel, Generic[GeomT, AttrT]):
    """Envelope estilo GeoJSON Feature: geometria + atributos do domínio + CRS (SRID inteiro).
    Genérico para ser reusado por qualquer resultado de geocodificação (linha/ponto/polígono),
    com `attributes` tipado pelo modelo específico de cada 'bicho'."""
    geometry: GeomT
    attributes: AttrT
    crs: int
