from typing import Protocol

from pydantic import SecretStr

from services.utils.http import HttpFetcher

from .client import Cliente
from .models import RETRY


class SettingsLike(Protocol):
    GOOGLE_GEOCODING_TOKEN: SecretStr


def build_cliente(source: SettingsLike) -> Cliente | None:
    if not source.GOOGLE_GEOCODING_TOKEN.get_secret_value():
        return None
    return Cliente(
        token=source.GOOGLE_GEOCODING_TOKEN,
        fetcher=HttpFetcher(RETRY),
    )
