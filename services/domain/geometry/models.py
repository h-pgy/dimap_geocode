from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, model_validator

from .coordinates import eh_linha, eh_multilinha, eh_poligono, eh_multipoligono, eh_ponto


class PointGeometry(BaseModel):
    """GeoJSON de ponto gerado no domínio. `coordinates` tem a forma `Position` (list[float] de
    tamanho 2) — ver `coordinates.py`. Validação estrutural rasa via `eh_ponto` (que também rejeita
    bool e posições 3D), por isso o campo é `list[Any]` e não `list[float]`: o alias documenta a
    forma sem delegar a checagem ao Pydantic (que coagiria bool->float e aceitaria posições 3D)."""
    type: Literal["Point"]
    coordinates: list[Any]

    @model_validator(mode="after")
    def _validar_forma(self) -> "PointGeometry":
        if not eh_ponto(self.coordinates):
            raise ValueError("coordinates não tem a forma de Point")
        return self


class LineGeometry(BaseModel):
    """GeoJSON de linha vindo do WFS. `coordinates` tem a forma `LineCoords` (LineString) ou
    `MultiLineCoords` (MultiLineString) — ver `coordinates.py`. Validação estrutural rasa da forma
    (sem converter em objeto geométrico nem varrer todos os vértices), por isso o campo é
    `list[Any]` e não o alias aninhado (que forçaria revalidação profunda)."""
    type: Literal["LineString", "MultiLineString"]
    coordinates: list[Any]

    @model_validator(mode="after")
    def _validar_forma(self) -> "LineGeometry":
        valida = eh_linha if self.type == "LineString" else eh_multilinha
        if not valida(self.coordinates):
            raise ValueError(f"coordinates não tem a forma de {self.type}")
        return self


class PolygonGeometry(BaseModel):
    """GeoJSON de polígono vindo do WFS. `coordinates` tem a forma `PolygonCoords` (Polygon) ou
    `MultiPolygonCoords` (MultiPolygon) — ver `coordinates.py`. Validação estrutural rasa da forma
    (sem converter em objeto geométrico nem varrer todos os anéis/vértices), por isso o campo é
    `list[Any]`. Espelha o `LineGeometry`: um único model cobre o tipo simples e o múltiplo."""
    type: Literal["Polygon", "MultiPolygon"]
    coordinates: list[Any]

    @model_validator(mode="after")
    def _validar_forma(self) -> "PolygonGeometry":
        valida = eh_poligono if self.type == "Polygon" else eh_multipoligono
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
