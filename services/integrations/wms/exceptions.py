import requests


class WmsError(Exception):
    """Base de todos os erros desta integration WMS — capture isto para pegar qualquer falha."""


class WmsHttpError(WmsError, requests.HTTPError):
    """Servidor WMS respondeu com status de erro (>= 400).

    Herda de requests.HTTPError, então pode ser capturada como WmsHttpError, como
    WmsError ou como requests.HTTPError.
    """


class WmsResponseNotImageError(WmsError):
    """HTTP 200, mas o corpo não é imagem (provável ServiceException XML do WMS)."""

    def __init__(
        self,
        message: str,
        *,
        content_type: str | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.content_type = content_type
        self.body = body
