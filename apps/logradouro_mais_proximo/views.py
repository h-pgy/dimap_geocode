from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.logradouro_geocoder.views import geocodificar_codlog
from apps.mapping.consultas import ConsultaSobrePonto
from apps.mapping.context import contexto_aviso
from services.domain.logradouro_geocod import SegmentosNoRaio, SegmentosNoRaioInput
from services.integrations.wfs import build_fetcher

MAP_INTERPOLATION_CRS: int = settings.MAP_INTERPOLATION_CRS
MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
MAIS_PROXIMO_RAIO_LIMITE_M: float = settings.MAIS_PROXIMO_RAIO_LIMITE_M
WFS_LAYER_LOGRADOUROS: str = settings.WFS_LAYER_LOGRADOUROS
WFS_LOGRADOUROS_CAMPO_GEOMETRIA: str = settings.WFS_LOGRADOUROS_CAMPO_GEOMETRIA

TEMPLATE_RECUSA_ACAO = "mapping/_recusa_acao.html"

MSG_SEM_LOGRADOURO_NO_RAIO = "Nenhum logradouro foi encontrado a {raio_m:.0f} metros do ponto."


@require_POST
def do_ponto(request: HttpRequest) -> HttpResponse:
    """Rota aberta (SPEC geocodificacao/005): lê a camada pública de segmentos."""
    consulta = ConsultaSobrePonto.model_validate(request.POST.dict())
    entrada = SegmentosNoRaioInput(
        ponto=consulta.desenho,
        crs_ponto=MAP_OUTPUT_CRS,
        raio_m=MAIS_PROXIMO_RAIO_LIMITE_M,
        layer_name=WFS_LAYER_LOGRADOUROS,
        campo_geometria=WFS_LOGRADOUROS_CAMPO_GEOMETRIA,
        crs_metrico=MAP_INTERPOLATION_CRS,
    )
    fetcher = build_fetcher(settings)
    buscar_segmentos = SegmentosNoRaio(fetcher)
    proximos = buscar_segmentos(entrada)
    if not proximos:
        mensagem = MSG_SEM_LOGRADOURO_NO_RAIO.format(raio_m=MAIS_PROXIMO_RAIO_LIMITE_M)
        return render(request, TEMPLATE_RECUSA_ACAO, contexto_aviso(mensagem))
    mais_proximo = proximos[0]
    return geocodificar_codlog(request, mais_proximo.segmento.attributes.codlog)
