from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from services.domain.desenho import GavetaDesenhosInput, MontarGavetaDesenhos
from services.utils.sorteio import sortear_diferente

from .context import ortofotos_disponiveis

MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
MAP_INTERPOLATION_CRS: int = settings.MAP_INTERPOLATION_CRS
MAP_GEOGRAPHIC_CRS: int = settings.MAP_GEOGRAPHIC_CRS
TEMPLATE_GAVETA_DESENHOS = "mapping/_gaveta_desenhos.html"


def fundo_ortofoto(request: HttpRequest) -> HttpResponse:
    """Rota aberta (design/010 §3): a tela de login é anônima e mostra o mesmo fundo."""
    disponiveis = ortofotos_disponiveis()
    escolhida = sortear_diferente(disponiveis, request.GET.get("atual")) if disponiveis else None
    return render(
        request,
        "mapping/_camada_ortofoto.html",
        {"ortofoto_fundo": escolhida, "entrando": True},
    )


@require_POST
def desenhos_da_bancada(request: HttpRequest) -> HttpResponse:
    """Rota aberta (design/020 §3.5): monta a gaveta a partir dos traços que estão no mapa —
    sem ato administrativo, sem login exigido."""
    # Os dois campos chegam como texto: o `_do_json` de GavetaDesenhosInput os decodifica antes
    # de validar, então o tipo estático do parâmetro não bate com o valor aceito em runtime.
    entrada = GavetaDesenhosInput(
        desenhos=request.POST.get("desenhos", "[]"),  # type: ignore[arg-type]
        ids_selecionados=request.POST.get("selecionados", "[]"),  # type: ignore[arg-type]
        crs_mapa=MAP_OUTPUT_CRS,
        crs_metrico=MAP_INTERPOLATION_CRS,
        crs_geografico=MAP_GEOGRAPHIC_CRS,
    )
    gaveta = MontarGavetaDesenhos()(entrada)
    return render(request, TEMPLATE_GAVETA_DESENHOS, {"gaveta": gaveta})
