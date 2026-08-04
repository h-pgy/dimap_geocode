from pydantic import BaseModel


class HttpRetryPolicy(BaseModel):
    """O que cada consumidor declara; o laço que a obedece é do `HttpFetcher`."""

    request_timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_wait_min_seconds: float = 1.0
    retry_wait_max_seconds: float = 5.0
    # Vazio por default: quem falha por status (portais de CMS) declara os seus.
    status_para_retry: tuple[int, ...] = ()
