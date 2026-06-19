import pytest
from pydantic import ValidationError

from services.integrations.wfs.models import (
    CqlFilter,
    CqlPredicate,
    WfsFeatureCollection,
    WfsRetryPolicy,
)


def test_cql_escapes_single_quote() -> None:
    assert CqlPredicate(field="nm", op="=", value="O'Brien").to_cql() == "nm = 'O''Brien'"


def test_cql_and_join() -> None:
    f = CqlFilter(
        predicates=[
            CqlPredicate(field="cod", op="=", value=123),
            CqlPredicate(field="nm", op="LIKE", value="PAULISTA%"),
        ]
    )
    assert f.to_cql() == "cod = 123 AND nm LIKE 'PAULISTA%'"


def test_cql_or_join() -> None:
    f = CqlFilter(
        predicates=[
            CqlPredicate(field="tipo", op="=", value="A"),
            CqlPredicate(field="tipo", op="=", value="B"),
        ],
        logic="OR",
    )
    assert f.to_cql() == "tipo = 'A' OR tipo = 'B'"


def test_cql_raw_bypasses_escape() -> None:
    f = CqlFilter(raw_cql="BBOX(geom, -46.7, -23.7, -46.5, -23.5, 'EPSG:4326')")
    assert f.to_cql() == "BBOX(geom, -46.7, -23.7, -46.5, -23.5, 'EPSG:4326')"


def test_cql_bool_literal() -> None:
    assert CqlPredicate(field="ativo", op="=", value=True).to_cql() == "ativo = true"


def test_cql_numeric_literal() -> None:
    assert CqlPredicate(field="area", op=">=", value=100.5).to_cql() == "area >= 100.5"


def test_collection_coerces_unknown() -> None:
    fc = WfsFeatureCollection.model_validate(
        {"type": "FeatureCollection", "numberMatched": "unknown", "features": []}
    )
    assert fc.number_matched is None


def test_collection_coerces_absent() -> None:
    fc = WfsFeatureCollection.model_validate(
        {"type": "FeatureCollection", "features": []}
    )
    assert fc.number_matched is None
    assert fc.total_features is None


def test_collection_parses_int_matched() -> None:
    fc = WfsFeatureCollection.model_validate(
        {"type": "FeatureCollection", "numberMatched": 42, "features": []}
    )
    assert fc.number_matched == 42


def test_retry_policy_defaults() -> None:
    p = WfsRetryPolicy()
    assert p.request_timeout_seconds == 30.0
    assert p.max_retries == 3
    assert p.retry_wait_min_seconds == 1.0
    assert p.retry_wait_max_seconds == 5.0


def test_retry_policy_rejects_negative_max_retries() -> None:
    with pytest.raises(ValidationError):
        WfsRetryPolicy(max_retries=-1)


def test_retry_policy_rejects_negative_wait() -> None:
    with pytest.raises(ValidationError):
        WfsRetryPolicy(retry_wait_min_seconds=-1.0)


def test_retry_policy_rejects_inverted_wait_bounds() -> None:
    with pytest.raises(ValidationError):
        WfsRetryPolicy(retry_wait_min_seconds=5.0, retry_wait_max_seconds=1.0)


def test_collection_parses_geometry_point() -> None:
    fc = WfsFeatureCollection.model_validate(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": "camada.1",
                    "geometry": {"type": "Point", "coordinates": [-46.6, -23.5]},
                    "properties": {},
                }
            ],
        }
    )
    assert fc.features[0].geometry is not None
    assert fc.features[0].geometry.type == "Point"
