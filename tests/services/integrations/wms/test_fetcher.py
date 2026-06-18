import pytest
import requests
from unittest.mock import Mock, patch

from services.integrations.wms.exceptions import WmsHttpError, WmsResponseNotImageError
from services.integrations.wms.fetcher import WmsFetcher
from services.integrations.wms.models import BoundingBox, WmsConnectionConfig, WmsMapRequest

BBOX = BoundingBox(minx=333000, miny=7390000, maxx=334000, maxy=7391000, crs="EPSG:31983")


@pytest.fixture
def config() -> WmsConnectionConfig:
    return WmsConnectionConfig(
        vector_url="https://wms.test/ows",
        raster_url="https://wms.test/raster",
    )


def _resp(
    *,
    status: int = 200,
    content_type: str = "image/png",
    content: bytes = b"\x89PNG...",
    text: str = "",
) -> Mock:
    r = Mock()
    r.status_code = status
    r.headers = {"Content-Type": content_type}
    r.content = content
    r.text = text
    r.url = "https://wms.test/ows?..."
    if status >= 400:
        r.raise_for_status.side_effect = requests.HTTPError(f"{status} Server Error", response=r)
    else:
        r.raise_for_status.return_value = None
    return r


def _req(**kw: object) -> WmsMapRequest:
    return WmsMapRequest(layer="cam:lote", bbox=BBOX, **kw)


def test_returns_image_bytes(config: WmsConnectionConfig) -> None:
    with patch("services.integrations.wms.fetcher.requests.get", return_value=_resp()) as g:
        img = WmsFetcher(config)(_req())
    assert img.content.startswith(b"\x89PNG")
    assert img.content_type == "image/png"
    params = g.call_args.kwargs["params"]
    assert params["request"] == "GetMap"
    assert params["bbox"] == BBOX.string_wms


def test_http_error_raises_wms_http_error(config: WmsConnectionConfig) -> None:
    with patch(
        "services.integrations.wms.fetcher.requests.get",
        return_value=_resp(status=500, content_type="text/plain", text="boom"),
    ):
        with pytest.raises(WmsHttpError) as exc:
            WmsFetcher(config)(_req())
    assert isinstance(exc.value, requests.HTTPError)


def test_service_exception_on_200_raises(config: WmsConnectionConfig) -> None:
    with patch(
        "services.integrations.wms.fetcher.requests.get",
        return_value=_resp(
            content_type="application/vnd.ogc.se_xml",
            text="<ServiceExceptionReport/>",
        ),
    ):
        with pytest.raises(WmsResponseNotImageError) as exc:
            WmsFetcher(config)(_req())
    assert exc.value.content_type == "application/vnd.ogc.se_xml"


def test_raster_flag_picks_raster_url(config: WmsConnectionConfig) -> None:
    with patch("services.integrations.wms.fetcher.requests.get", return_value=_resp()) as g:
        WmsFetcher(config)(_req(raster=True))
    assert g.call_args.args[0] == config.raster_url


def test_vector_flag_picks_vector_url(config: WmsConnectionConfig) -> None:
    with patch("services.integrations.wms.fetcher.requests.get", return_value=_resp()) as g:
        WmsFetcher(config)(_req(raster=False))
    assert g.call_args.args[0] == config.vector_url


def test_dimensions_default_from_config(config: WmsConnectionConfig) -> None:
    with patch("services.integrations.wms.fetcher.requests.get", return_value=_resp()) as g:
        img = WmsFetcher(config)(_req())
    params = g.call_args.kwargs["params"]
    assert params["width"] == config.default_width
    assert params["height"] == config.default_height
    assert img.width == config.default_width
    assert img.height == config.default_height


def test_custom_dimensions_override_config(config: WmsConnectionConfig) -> None:
    with patch("services.integrations.wms.fetcher.requests.get", return_value=_resp()) as g:
        img = WmsFetcher(config)(_req(width=512, height=512))
    params = g.call_args.kwargs["params"]
    assert params["width"] == 512
    assert params["height"] == 512
    assert img.width == 512
    assert img.height == 512


def test_params_include_required_wms_keys(config: WmsConnectionConfig) -> None:
    with patch("services.integrations.wms.fetcher.requests.get", return_value=_resp()) as g:
        WmsFetcher(config)(_req())
    params = g.call_args.kwargs["params"]
    assert params["service"] == "WMS"
    assert params["version"] == config.version
    assert params["request"] == "GetMap"
    assert params["layers"] == "cam:lote"
    assert params["format"] == config.image_format
    assert params["crs"] == config.default_crs
    assert params["transparent"] == "true"


def test_image_result_carries_provenance(config: WmsConnectionConfig) -> None:
    with patch("services.integrations.wms.fetcher.requests.get", return_value=_resp()):
        img = WmsFetcher(config)(_req())
    assert img.layer == "cam:lote"
    assert img.bbox == BBOX


def test_callable_delegates_to_fetch_map(config: WmsConnectionConfig) -> None:
    with patch("services.integrations.wms.fetcher.requests.get", return_value=_resp()):
        img_direct = WmsFetcher(config).fetch_map(_req())
    with patch("services.integrations.wms.fetcher.requests.get", return_value=_resp()):
        img_call = WmsFetcher(config)(_req())
    assert img_direct.content == img_call.content


def test_wms_http_error_also_catchable_as_wms_error(config: WmsConnectionConfig) -> None:
    from services.integrations.wms.exceptions import WmsError

    with patch(
        "services.integrations.wms.fetcher.requests.get",
        return_value=_resp(status=404, content_type="text/plain"),
    ):
        with pytest.raises(WmsError):
            WmsFetcher(config)(_req())
