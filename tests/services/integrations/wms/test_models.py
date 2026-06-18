from services.integrations.wms.models import BoundingBox, WmsConnectionConfig


def test_bbox_string_wms() -> None:
    bb = BoundingBox(minx=1, miny=2, maxx=3, maxy=4)
    assert bb.string_wms == "1.0,2.0,3.0,4.0"
    assert bb.crs == "EPSG:31983"


def test_bbox_float_precision() -> None:
    bb = BoundingBox(minx=333000.5, miny=7390000.1, maxx=334000.5, maxy=7391000.1)
    assert bb.string_wms == "333000.5,7390000.1,334000.5,7391000.1"


def test_config_picks_vector_url() -> None:
    cfg = WmsConnectionConfig(vector_url="https://v", raster_url="https://r")
    assert cfg.base_url_for(raster=False) == "https://v"


def test_config_picks_raster_url() -> None:
    cfg = WmsConnectionConfig(vector_url="https://v", raster_url="https://r")
    assert cfg.base_url_for(raster=True) == "https://r"


def test_config_defaults() -> None:
    cfg = WmsConnectionConfig(vector_url="https://v", raster_url="https://r")
    assert cfg.version == "1.3.0"
    assert cfg.default_crs == "EPSG:31983"
    assert cfg.image_format == "image/png"
    assert cfg.default_width == 256
    assert cfg.default_height == 256
