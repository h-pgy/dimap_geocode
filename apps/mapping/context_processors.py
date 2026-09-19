from typing import Any

from django.http import HttpRequest

from .context import COOKIE_ORTOFOTO_FUNDO, ortofoto_do_fundo


def fundo_admin(request: HttpRequest) -> dict[str, Any]:
    return {"ortofoto_fundo": ortofoto_do_fundo(request.COOKIES.get(COOKIE_ORTOFOTO_FUNDO))}
