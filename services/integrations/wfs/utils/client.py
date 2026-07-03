from typing import Protocol

from ..fetcher import WfsFetcher
from ..models import WfsConnectionConfig, WfsRetryPolicy


class WfsSettingsLike(Protocol):
    """Contrato estrutural do que o factory precisa para montar o cliente WFS.

    Qualquer objeto com estes atributos serve (ex.: o `settings` do Django, injetado pela
    orquestração). O factory NÃO importa Django — recebe o objeto por parâmetro, mantendo
    `services/` desacoplado da interface (§3.3)."""

    WFS_DOMAIN: str
    WFS_ENDPOINT: str
    WFS_NAMESPACE: str
    WFS_SERVICE: str
    WFS_VERSION: str
    WFS_REQUEST_TIMEOUT_SECONDS: float
    WFS_MAX_RETRIES: int
    WFS_RETRY_WAIT_MIN_SECONDS: float
    WFS_RETRY_WAIT_MAX_SECONDS: float


def build_connection_config(source: WfsSettingsLike) -> WfsConnectionConfig:
    return WfsConnectionConfig(
        domain=source.WFS_DOMAIN,
        endpoint=source.WFS_ENDPOINT,
        namespace=source.WFS_NAMESPACE,
        service=source.WFS_SERVICE,
        version=source.WFS_VERSION,
    )


def build_retry_policy(source: WfsSettingsLike) -> WfsRetryPolicy:
    return WfsRetryPolicy(
        request_timeout_seconds=source.WFS_REQUEST_TIMEOUT_SECONDS,
        max_retries=source.WFS_MAX_RETRIES,
        retry_wait_min_seconds=source.WFS_RETRY_WAIT_MIN_SECONDS,
        retry_wait_max_seconds=source.WFS_RETRY_WAIT_MAX_SECONDS,
    )


def build_fetcher(source: WfsSettingsLike, *, verbose: bool = False) -> WfsFetcher:
    """Monta o `WfsFetcher` (cliente WFS) a partir de um objeto settings-like injetado."""
    return WfsFetcher(
        build_connection_config(source),
        retry_policy=build_retry_policy(source),
        verbose=verbose,
    )
