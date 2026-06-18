from requests.exceptions import HTTPError


class WfsHttpError(HTTPError):
    """Levantada quando o GeoServer retorna um status HTTP de erro."""


class WfsInvalidResponseError(Exception):
    """Levantada quando o GeoServer retorna um corpo que não é JSON válido."""
