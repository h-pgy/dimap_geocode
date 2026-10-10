from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.address_geocoder.views import renderizar_endereco
from apps.mapping.models import ConsultaSobrePonto
from apps.mapping.context import contexto_aviso
from services.domain.address_geocod import (
    EnderecoMaisProximo,
    EnderecoMaisProximoInput,
    NenhumSegmentoNumeradoNoRaioError,
)
from services.domain.logradouro_geocod import (
    LogradouroGeocoder,
    SegmentosNoRaio,
    SegmentosNoRaioInput,
)
from services.integrations.wfs import build_fetcher

MAP_INTERPOLATION_CRS: int = settings.MAP_INTERPOLATION_CRS
MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
MAIS_PROXIMO_RAIO_LIMITE_M: float = settings.MAIS_PROXIMO_RAIO_LIMITE_M
WFS_LAYER_LOGRADOUROS: str = settings.WFS_LAYER_LOGRADOUROS
WFS_LOGRADOUROS_CAMPO_GEOMETRIA: str = settings.WFS_LOGRADOUROS_CAMPO_GEOMETRIA

TEMPLATE_RECUSA_ACAO = "mapping/_recusa_acao.html"

MSG_SEM_ENDERECO_NO_RAIO = (
    "Nenhum logradouro com numeração foi encontrado a {raio_m:.0f} metros do ponto."
)


@require_POST
def do_ponto(request: HttpRequest) -> HttpResponse:
    """Rota aberta (SPEC geocodificacao/008): lê a camada pública de segmentos."""
    consulta = ConsultaSobrePonto.model_validate(request.POST.dict())
    entrada = EnderecoMaisProximoInput(
        consulta=SegmentosNoRaioInput(
            ponto=consulta.desenho,
            crs_ponto=MAP_OUTPUT_CRS,
            raio_m=MAIS_PROXIMO_RAIO_LIMITE_M,
            layer_name=WFS_LAYER_LOGRADOUROS,
            campo_geometria=WFS_LOGRADOUROS_CAMPO_GEOMETRIA,
            crs_metrico=MAP_INTERPOLATION_CRS,
        ),
        output_crs=MAP_OUTPUT_CRS,
    )
    fetcher = build_fetcher(settings)
    segmentos_no_raio = SegmentosNoRaio(fetcher)
    segmentos_do_codlog = LogradouroGeocoder(fetcher)
    buscar_endereco = EnderecoMaisProximo(segmentos_no_raio, segmentos_do_codlog)
    try:
        endereco = buscar_endereco(entrada)
    except NenhumSegmentoNumeradoNoRaioError:
        mensagem = MSG_SEM_ENDERECO_NO_RAIO.format(raio_m=MAIS_PROXIMO_RAIO_LIMITE_M)
        return render(request, TEMPLATE_RECUSA_ACAO, contexto_aviso(mensagem))
    return renderizar_endereco(request, endereco)
