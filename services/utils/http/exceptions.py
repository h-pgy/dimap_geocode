class HttpFetchError(Exception):
    """Levantada quando a URL não pôde ser buscada após esgotadas as tentativas da política."""


class HttpStatusError(HttpFetchError):
    """Levantada quando o servidor respondeu com status de erro que repetir não resolve."""
