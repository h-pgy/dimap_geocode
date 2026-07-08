from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from pydantic import BaseModel

from apps.mapping.context import contexto_mapa_base


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "core/home.html", contexto_mapa_base())


def teste_validacao(request: HttpRequest) -> HttpResponse:
    class _DTO(BaseModel):
        codigo: int
        nome: str

    _DTO.model_validate({"codigo": "nao-e-inteiro", "nome": ""})
    return HttpResponse("ok")  # nunca chega aqui
