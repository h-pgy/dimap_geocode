from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from pydantic import ValidationError


class PydanticValidationMiddleware:
    """Intercepta pydantic.ValidationError em qualquer view e devolve
    um partial HTML de erro com status 422."""

    def __init__(self, get_response: object) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)  # type: ignore[return-value]

    def process_exception(
        self, request: HttpRequest, exception: Exception
    ) -> HttpResponse | None:
        if not isinstance(exception, ValidationError):
            return None
        return render(
            request,
            "partials/erro_validacao.html",
            {"erros": exception.errors()},
            status=422,
        )
