import pytest
from collections.abc import Iterator
from json import JSONDecodeError
from unittest.mock import MagicMock, Mock, patch

import requests as _requests

from services.integrations.wfs.exceptions import (
    WfsConnectionError,
    WfsHttpError,
    WfsInvalidResponseError,
    WfsTimeoutError,
)
from services.integrations.wfs.fetcher import WfsFetcher
from services.integrations.wfs.models import (
    WfsConnectionConfig,
    WfsFeatureRequest,
    WfsRetryPolicy,
)


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


@pytest.fixture
def no_sleep() -> Iterator[tuple[MagicMock, MagicMock]]:
    """Neutraliza a espera real: time.sleep vira mock e random.uniform devolve constante."""
    with (
        patch("services.integrations.wfs.fetcher.time.sleep") as sleep_mock,
        patch("services.integrations.wfs.fetcher.random.uniform", return_value=0.01) as uniform_mock,
    ):
        yield sleep_mock, uniform_mock


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


# ---------- Resiliência a timeout/conexão (patch v2) ----------


def test_retries_then_succeeds(config: WfsConnectionConfig, no_sleep: tuple[MagicMock, MagicMock]) -> None:
    # falha transitória (timeout e conexão) e depois recupera; dorme entre as falhas, não após o sucesso
    sleep_mock, _ = no_sleep
    responses = [
        _requests.exceptions.Timeout(),
        _requests.exceptions.ConnectionError(),
        _fake_response(_page([_feat(1)], 1)),
    ]
    policy = WfsRetryPolicy(max_retries=3)
    with patch(
        "services.integrations.wfs.fetcher.requests.get", side_effect=responses
    ) as mock_get:
        pages = list(WfsFetcher(config, retry_policy=policy)(WfsFeatureRequest(nome_camada="lote")))
    assert len(pages) == 1
    assert len(pages[0].features) == 1
    assert mock_get.call_count == 3
    assert sleep_mock.call_count == 2


def test_timeout_exhausts_retries_raises(config: WfsConnectionConfig, no_sleep: tuple[MagicMock, MagicMock]) -> None:
    sleep_mock, uniform_mock = no_sleep
    policy = WfsRetryPolicy(max_retries=2, retry_wait_min_seconds=1.0, retry_wait_max_seconds=5.0)
    with patch(
        "services.integrations.wfs.fetcher.requests.get",
        side_effect=_requests.exceptions.Timeout,
    ) as mock_get:
        with pytest.raises(WfsTimeoutError):
            list(WfsFetcher(config, retry_policy=policy)(WfsFeatureRequest(nome_camada="lote")))
    assert mock_get.call_count == 3  # 1 original + 2 retries (limite duro)
    assert sleep_mock.call_count == 2  # não dorme após a falha final
    uniform_mock.assert_called_with(1.0, 5.0)


def test_connection_error_exhausts_retries_raises(
    config: WfsConnectionConfig, no_sleep: tuple[MagicMock, MagicMock]
) -> None:
    policy = WfsRetryPolicy(max_retries=2)
    with patch(
        "services.integrations.wfs.fetcher.requests.get",
        side_effect=_requests.exceptions.ConnectionError,
    ) as mock_get:
        with pytest.raises(WfsConnectionError):
            list(WfsFetcher(config, retry_policy=policy)(WfsFeatureRequest(nome_camada="lote")))
    assert mock_get.call_count == 3


def test_connect_timeout_dispatches_to_timeout_error(
    config: WfsConnectionConfig, no_sleep: tuple[MagicMock, MagicMock]
) -> None:
    # ConnectTimeout herda de ConnectionError E Timeout → despacho "Timeout primeiro" → WfsTimeoutError
    policy = WfsRetryPolicy(max_retries=0)
    with patch(
        "services.integrations.wfs.fetcher.requests.get",
        side_effect=_requests.exceptions.ConnectTimeout,
    ):
        with pytest.raises(WfsTimeoutError):
            list(WfsFetcher(config, retry_policy=policy)(WfsFeatureRequest(nome_camada="lote")))


def test_max_retries_zero_single_attempt_no_sleep(
    config: WfsConnectionConfig, no_sleep: tuple[MagicMock, MagicMock]
) -> None:
    sleep_mock, _ = no_sleep
    policy = WfsRetryPolicy(max_retries=0)
    with patch(
        "services.integrations.wfs.fetcher.requests.get",
        side_effect=_requests.exceptions.Timeout,
    ) as mock_get:
        with pytest.raises(WfsTimeoutError):
            list(WfsFetcher(config, retry_policy=policy)(WfsFeatureRequest(nome_camada="lote")))
    assert mock_get.call_count == 1
    sleep_mock.assert_not_called()


def test_timeout_error_chains_original_cause(
    config: WfsConnectionConfig, no_sleep: tuple[MagicMock, MagicMock]
) -> None:
    policy = WfsRetryPolicy(max_retries=0)
    original = _requests.exceptions.Timeout("estourou")
    with patch("services.integrations.wfs.fetcher.requests.get", side_effect=original):
        with pytest.raises(WfsTimeoutError) as excinfo:
            list(WfsFetcher(config, retry_policy=policy)(WfsFeatureRequest(nome_camada="lote")))
    assert excinfo.value.__cause__ is original


def test_http_error_not_retried(config: WfsConnectionConfig) -> None:
    # erro de status é determinístico, não transitório → uma única chamada, sem retry
    policy = WfsRetryPolicy(max_retries=3)
    with patch("services.integrations.wfs.fetcher.requests.get") as mock_get:
        mock_get.return_value = _fake_response(None, status=500)
        with pytest.raises(WfsHttpError):
            list(WfsFetcher(config, retry_policy=policy)(WfsFeatureRequest(nome_camada="lote")))
    assert mock_get.call_count == 1
