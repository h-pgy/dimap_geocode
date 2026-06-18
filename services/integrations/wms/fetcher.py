import requests

from .exceptions import WmsHttpError, WmsResponseNotImageError
from .models import WmsConnectionConfig, WmsImage, WmsMapRequest

IMAGE_PREFIX = "image/"


class WmsFetcher:
    """Cliente WMS callable e fino: bbox + camada -> imagem (bytes). Sem Django, sem geopandas."""

    def __init__(self, config: WmsConnectionConfig, *, verbose: bool = False) -> None:
        self.config = config
        self.verbose = verbose

    def _build_params(self, request: WmsMapRequest) -> dict[str, str | int]:
        width = request.width or self.config.default_width
        height = request.height or self.config.default_height
        # WMS 1.3.0 usa "crs"; para 1.1.1 trocar a chave por "srs" (ver Notas da SPEC).
        return {
            "service": "WMS",
            "version": self.config.version,
            "request": "GetMap",
            "layers": request.layer,
            "styles": request.styles,
            "crs": request.crs or self.config.default_crs,
            "bbox": request.bbox.string_wms,
            "width": width,
            "height": height,
            "format": request.image_format or self.config.image_format,
            "transparent": str(request.transparent).lower(),
        }

    def fetch_map(self, request: WmsMapRequest) -> WmsImage:
        base_url = self.config.base_url_for(raster=request.raster)
        params = self._build_params(request)
        resp = requests.get(base_url, params=params)
        if self.verbose:
            print(f"[WmsFetcher] {resp.url}")
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            raise WmsHttpError(str(exc), response=resp) from exc
        content_type = resp.headers.get("Content-Type", "")
        if not content_type.startswith(IMAGE_PREFIX):
            raise WmsResponseNotImageError(
                "Resposta WMS não é imagem (provável ServiceException)",
                content_type=content_type,
                body=resp.text[:1000],
            )
        return WmsImage(
            content=resp.content,
            content_type=content_type,
            width=int(params["width"]),
            height=int(params["height"]),
            layer=request.layer,
            bbox=request.bbox,
        )

    def __call__(self, request: WmsMapRequest) -> WmsImage:
        return self.fetch_map(request)
