from typing import Any

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from pydantic import BaseModel

from apps.mapping.context import contexto_aviso, contexto_mapa
from apps.search.tentativas import FalhaBaseOficial
from services.domain.geocodificador_externo import (
    ConsultaGeocodificacao,
    EnderecoExternoFeature,
    GeocodificacaoExternaInput,
    GeocodificadorExterno,
    ProvedorIndisponivelError,
    SemResultadoAceitoError,
    build_geocodificador_externo,
)
from services.domain.geometry import to_geojson_feature_collection
from services.domain.geometry.models import GeoJsonProperties

MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
MAP_COR_PONTO: str = settings.MAP_COR_PONTO
MAIS_PROXIMO_RAIO_LIMITE_M: float = settings.MAIS_PROXIMO_RAIO_LIMITE_M

TEMPLATE_AVISO = "mapping/_aviso.html"
TEMPLATE_RESULTADO_EXTERNO = "geocodificacao_externa/partials/_resultado_externo.html"

MSG_INDISPONIVEL = "O serviço externo de geocodificação está indisponível no momento."
MSG_SEM_RESULTADO = "O serviço externo não localizou este endereço com precisão suficiente."
MSG_FALLBACK = "{motivo} O resultado veio do serviço externo ({provedor}), fora da base oficial."


class SelecaoGeocodificacaoExterna(BaseModel):
    texto: str


def geocodificador_externo() -> GeocodificadorExterno | None:
    # None = provedor não configurado (sem token no ambiente).
    return build_geocodificador_externo(settings)


def geocodificar_externo(
    request: HttpRequest,
    geocodificador: GeocodificadorExterno,
    texto: str,
    falha: FalhaBaseOficial | None = None,
) -> HttpResponse:
    entrada = GeocodificacaoExternaInput(
        consulta=ConsultaGeocodificacao(texto=texto),
        output_crs=MAP_OUTPUT_CRS,
    )
    try:
        endereco = geocodificador(entrada)
    except ProvedorIndisponivelError:
        return _aviso(request, MSG_INDISPONIVEL, falha, tom="error")
    except SemResultadoAceitoError:
        return _aviso(request, MSG_SEM_RESULTADO, falha, tom="warning")
    contexto = _contexto_externo(endereco) | {"aviso_fallback": _aviso_fallback(falha, endereco)}
    return render(request, TEMPLATE_RESULTADO_EXTERNO, contexto)


def _aviso(
    request: HttpRequest,
    mensagem: str,
    falha: FalhaBaseOficial | None,
    tom: str = "warning",
) -> HttpResponse:
    # no Enter, o aviso diz primeiro o que a base oficial não encontrou
    texto = mensagem if falha is None else f"{falha.motivo} {mensagem}"
    return render(request, TEMPLATE_AVISO, contexto_aviso(texto, tom=tom))


def _aviso_fallback(falha: FalhaBaseOficial | None, endereco: EnderecoExternoFeature) -> str | None:
    if falha is None:
        return None  # veio do clique: a pessoa escolheu o externo
    provedor = endereco.attributes.provedor.rotulo
    return MSG_FALLBACK.format(motivo=falha.motivo, provedor=provedor)


def _contexto_externo(endereco: EnderecoExternoFeature) -> dict[str, Any]:
    geojson = to_geojson_feature_collection(
        [endereco],
        lambda f: GeoJsonProperties(rotulo=f.attributes.endereco_formatado),
    )
    a = endereco.attributes
    return contexto_mapa(geojson, MAP_COR_PONTO) | {
        "endereco": a,
        "ponto": endereco.geometry,
        "provedor": a.provedor.rotulo,
        "precisao": a.precisao.rotulo,
        "raio_m": MAIS_PROXIMO_RAIO_LIMITE_M,
    }


@login_required  # a cota do provedor é paga: basta estar autenticado, sem contrato de ação
@require_POST
def selecionar(request: HttpRequest) -> HttpResponse:
    selecao = SelecaoGeocodificacaoExterna.model_validate(request.POST.dict())
    geocodificador = geocodificador_externo()
    if geocodificador is None:
        return render(request, TEMPLATE_AVISO, contexto_aviso(MSG_INDISPONIVEL, tom="error"))
    return geocodificar_externo(request, geocodificador, selecao.texto)

