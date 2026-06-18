import pytest
from json import JSONDecodeError
from unittest.mock import Mock, patch

import requests as _requests

from services.integrations.wfs.exceptions import WfsHttpError, WfsInvalidResponseError
from services.integrations.wfs.fetcher import WfsFetcher
from services.integrations.wfs.models import WfsConnectionConfig, WfsFeatureRequest


@pytest.fixture
def config() -> WfsConnectionConfig:
    return WfsConnectionConfig(
        domain="wfs.geosampa.test",
        endpoint="geoserver/ows",
        namespace="geoportal",
    )


def _fake_response(
    json_payload: object, status: int = 200, raise_json: bool = False
) -> Mock:
    resp = Mock()
    resp.status_code = status
    if raise_json:
        resp.json.side_effect = JSONDecodeError("x", "x", 0)
        resp.text = "<html>erro</html>"
    else:
        resp.json.return_value = json_payload
    if status != 200:
        resp.raise_for_status.side_effect = _requests.exceptions.HTTPError(f"HTTP {status}", response=resp)
    else:
        resp.raise_for_status.return_value = None
    return resp


def _page(features: list[object], number_matched: int | None = None) -> dict:
    payload: dict = {"type": "FeatureCollection", "features": features}
    if number_matched is not None:
        payload["numberMatched"] = number_matched
    return payload


def _feat(i: int) -> dict:
    return {
        "type": "Feature",
        "id": f"camada.{i}",
        "geometry": {"type": "Point", "coordinates": [0, 0]},
        "properties": {"n": i},
    }


def test_single_page(config: WfsConnectionConfig) -> None:
    with patch("services.integrations.wfs.fetcher.requests.get") as mock_get:
        mock_get.return_value = _fake_response(_page([_feat(1), _feat(2)], 2))
        pages = list(WfsFetcher(config)(WfsFeatureRequest(nome_camada="lote", count=10)))
    assert len(pages) == 1
    assert len(pages[0].features) == 2


def test_paginates_until_number_matched(config: WfsConnectionConfig) -> None:
    responses = [
        _fake_response(_page([_feat(1), _feat(2)], 3)),
        _fake_response(_page([_feat(3)], 3)),
    ]
    with patch("services.integrations.wfs.fetcher.requests.get", side_effect=responses):
        pages = list(WfsFetcher(config)(WfsFeatureRequest(nome_camada="lote", count=2)))
    assert sum(len(p.features) for p in pages) == 3


def test_empty_stops(config: WfsConnectionConfig) -> None:
    with patch("services.integrations.wfs.fetcher.requests.get") as mock_get:
        mock_get.return_value = _fake_response(_page([], 0))
        assert list(WfsFetcher(config)(WfsFeatureRequest(nome_camada="lote"))) == []


def test_http_error_raises_wfs_http_error(config: WfsConnectionConfig) -> None:
    with patch("services.integrations.wfs.fetcher.requests.get") as mock_get:
        mock_get.return_value = _fake_response(None, status=500)
        with pytest.raises(WfsHttpError):
            list(WfsFetcher(config)(WfsFeatureRequest(nome_camada="lote")))


def test_invalid_json_raises_wfs_error(config: WfsConnectionConfig) -> None:
    with patch("services.integrations.wfs.fetcher.requests.get") as mock_get:
        mock_get.return_value = _fake_response(None, raise_json=True)
        with pytest.raises(WfsInvalidResponseError):
            list(WfsFetcher(config)(WfsFeatureRequest(nome_camada="lote")))


def test_features_fetched_count(config: WfsConnectionConfig) -> None:
    responses = [
        _fake_response(_page([_feat(1), _feat(2)], 3)),
        _fake_response(_page([_feat(3)], 3)),
    ]
    with patch("services.integrations.wfs.fetcher.requests.get", side_effect=responses):
        fetcher = WfsFetcher(config)
        list(fetcher(WfsFeatureRequest(nome_camada="lote", count=2)))
    assert fetcher.features_fetched_count == 3


def test_callable_delegates_to_generator(config: WfsConnectionConfig) -> None:
    with patch("services.integrations.wfs.fetcher.requests.get") as mock_get:
        mock_get.return_value = _fake_response(_page([_feat(1)], 1))
        fetcher = WfsFetcher(config)
        result = fetcher(WfsFeatureRequest(nome_camada="lote"))
        # __call__ deve retornar um gerador, não uma lista
        import types
        assert isinstance(result, types.GeneratorType)


def test_no_number_matched_paginates_until_empty(config: WfsConnectionConfig) -> None:
    # sem numberMatched, para quando a página vem vazia
    responses = [
        _fake_response(_page([_feat(1), _feat(2)])),
        _fake_response(_page([])),
    ]
    with patch("services.integrations.wfs.fetcher.requests.get", side_effect=responses):
        pages = list(WfsFetcher(config)(WfsFeatureRequest(nome_camada="lote", count=2)))
    assert len(pages) == 1
    assert len(pages[0].features) == 2
