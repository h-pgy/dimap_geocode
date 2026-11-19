from collections.abc import Callable
from functools import wraps
from typing import Any

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse


def superusuario_requerido(
    view: Callable[..., HttpResponse],
) -> Callable[..., HttpResponse]:
    @wraps(view)
    @login_required
    def _protegida(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not request.user.is_superuser:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return _protegida
