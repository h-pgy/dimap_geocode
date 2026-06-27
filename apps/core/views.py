from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from pydantic import BaseModel


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "core/home.html")


def teste_validacao(request: HttpRequest) -> HttpResponse:
    class _DTO(BaseModel):
        codigo: int
        nome: str

    _DTO.model_validate({"codigo": "nao-e-inteiro", "nome": ""})
    return HttpResponse("ok")  # nunca chega aqui
