from requests.exceptions import HTTPError


class WfsHttpError(HTTPError):
    """Levantada quando o GeoServer retorna um status HTTP de erro."""


class WfsInvalidResponseError(Exception):
    """Levantada quando o GeoServer retorna um corpo que não é JSON válido."""


class WfsTimeoutError(WfsHttpError):
    """Levantada quando o GeoServer não respondeu dentro do timeout após esgotar os retries."""


class WfsConnectionError(WfsHttpError):
    """Levantada quando a conexão com o GeoServer falhou após esgotar os retries."""
