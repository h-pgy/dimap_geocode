from typing import Protocol

from .fetcher import WmsFetcher
from .models import WmsConnectionConfig


class WmsSettingsLike(Protocol):
    WMS_URL: str
    WMS_RASTER_URL: str
    WMS_VERSION: str
    WMS_REQUEST_TIMEOUT_SECONDS: float


def build_wms_fetcher(source: WmsSettingsLike) -> WmsFetcher:
    return WmsFetcher(
        WmsConnectionConfig(
            vector_url=source.WMS_URL,
            raster_url=source.WMS_RASTER_URL,
            version=source.WMS_VERSION,
            request_timeout_seconds=source.WMS_REQUEST_TIMEOUT_SECONDS,
        )
    )
