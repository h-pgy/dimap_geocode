from services.utils.http import HttpFetcher

from .constants import USER_AGENT_ITBI
from .models import ItbiPortalConfig


def build_fetcher(config: ItbiPortalConfig, *, verbose: bool = False) -> HttpFetcher:
    """O cliente HTTP já com os defaults da ITBI — o consumidor não os remonta campo a campo."""
    return HttpFetcher(config.retry, user_agent=USER_AGENT_ITBI, verbose=verbose)
