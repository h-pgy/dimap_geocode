from typing import Any

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from pydantic import BaseModel

from apps.mapping.context import contexto_aviso, contexto_mapa
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
LOTE_MAIS_PROXIMO_DO_PONTO_RAIO_M: float = settings.LOTE_MAIS_PROXIMO_DO_PONTO_RAIO_M

TEMPLATE_AVISO = "mapping/_aviso.html"
TEMPLATE_RESULTADO_EXTERNO = "geocodificacao_externa/partials/_resultado_externo.html"

MSG_INDISPONIVEL = "O serviço externo de geocodificação está indisponível no momento."
MSG_SEM_RESULTADO = "O serviço externo não localizou este endereço com precisão suficiente."


class SelecaoGeocodificacaoExterna(BaseModel):
    texto: str


def geocodificador_externo() -> GeocodificadorExterno | None:
    # None = provedor não configurado (sem token no ambiente).
    return build_geocodificador_externo(settings)


def geocodificar_externo(
    request: HttpRequest,
    geocodificador: GeocodificadorExterno,
    texto: str,
) -> HttpResponse:
    entrada = GeocodificacaoExternaInput(
        consulta=ConsultaGeocodificacao(texto=texto),
        output_crs=MAP_OUTPUT_CRS,
    )
    try:
        endereco = geocodificador(entrada)
    except ProvedorIndisponivelError:
        return render(request, TEMPLATE_AVISO, contexto_aviso(MSG_INDISPONIVEL))
    except SemResultadoAceitoError:
        return render(request, TEMPLATE_AVISO, contexto_aviso(MSG_SEM_RESULTADO))
    return render(request, TEMPLATE_RESULTADO_EXTERNO, _contexto_externo(endereco))


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
        "raio_m": LOTE_MAIS_PROXIMO_DO_PONTO_RAIO_M,
    }


@login_required  # a cota do provedor é paga: basta estar autenticado, sem contrato de ação
@require_POST
def selecionar(request: HttpRequest) -> HttpResponse:
    selecao = SelecaoGeocodificacaoExterna.model_validate(request.POST.dict())
    geocodificador = geocodificador_externo()
    if geocodificador is None:
        return render(request, TEMPLATE_AVISO, contexto_aviso(MSG_INDISPONIVEL))
    return geocodificar_externo(request, geocodificador, selecao.texto)
