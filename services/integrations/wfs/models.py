from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class WfsConnectionConfig(BaseModel):
    domain: str
    endpoint: str
    namespace: str
    service: str = "WFS"
    version: str = "2.0.0"

    @property
    def url_base(self) -> str:
        return f"https://{self.domain}/{self.endpoint}"


def _escape_cql_literal(value: str | int | float | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + value.replace("'", "''") + "'"


class CqlPredicate(BaseModel):
    field: str
    op: Literal["=", "<>", ">", "<", ">=", "<=", "LIKE", "ILIKE"]
    value: str | int | float | bool

    def to_cql(self) -> str:
        return f"{self.field} {self.op} {_escape_cql_literal(self.value)}"


class CqlFilter(BaseModel):
    predicates: list[CqlPredicate] = Field(default_factory=list)
    logic: Literal["AND", "OR"] = "AND"
    # escape-hatch: bypassa o escape — usar com cautela
    raw_cql: str | None = None

    def to_cql(self) -> str:
        if self.raw_cql is not None:
            return self.raw_cql
        return f" {self.logic} ".join(p.to_cql() for p in self.predicates)


class WfsFeatureRequest(BaseModel):
    nome_camada: str
    output_format: str = "application/json"
    # WFS 1.x aceita maxFeatures; WFS 2.0 aceita count.
    # GeoSampa responde a maxFeatures — mapear por versão em Patches se necessário.
    count: int | None = None
    start_index: int | None = None
    cql_filter: CqlFilter | None = None
    srs_name: str | None = None
    property_names: list[str] | None = None
    extra_params: dict[str, str | int] = Field(default_factory=dict)

    def to_query_params(self) -> dict[str, str | int]:
        params: dict[str, str | int] = {"outputFormat": self.output_format}
        if self.count is not None:
            params["maxFeatures"] = self.count
        if self.start_index is not None:
            params["startIndex"] = self.start_index
        if self.cql_filter is not None:
            params["cql_filter"] = self.cql_filter.to_cql()
        if self.srs_name:
            params["srsName"] = self.srs_name
        if self.property_names:
            params["propertyName"] = ",".join(self.property_names)
        params.update(self.extra_params)
        return params


class WfsGeometry(BaseModel):
    type: str
    coordinates: Any


class WfsFeature(BaseModel):
    type: Literal["Feature"]
    id: str | None = None
    geometry: WfsGeometry | None = None
    geometry_name: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class WfsFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"]
    features: list[WfsFeature] = Field(default_factory=list)
    total_features: int | None = Field(default=None, alias="totalFeatures")
    number_matched: int | None = Field(default=None, alias="numberMatched")
    number_returned: int | None = Field(default=None, alias="numberReturned")
    crs: dict[str, Any] | None = None
    bbox: list[float] | None = None

    model_config = {"populate_by_name": True}

    @field_validator("total_features", "number_matched", "number_returned", mode="before")
    @classmethod
    def _coerce_unknown(cls, v: Any) -> int | None:
        if isinstance(v, int):
            return v
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
