from pydantic import BaseModel

from services.utils.http import HttpRetryPolicy

from .constants import RETRY_ITBI, URL_PAGINA_ITBI


class ItbiPortalConfig(BaseModel):
    url_pagina: str = URL_PAGINA_ITBI
    retry: HttpRetryPolicy = RETRY_ITBI


class PlanilhaItbi(BaseModel):
    """Uma publicação anual do portal: o ano declarado no <strong> e a URL já absoluta."""

    ano: int
    url: str
