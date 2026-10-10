from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.competencias.resolucao import slugs_liberados
from apps.mapping.acoes_desenho import OfertarNoPoco
from apps.mapping.historico_gaveta import abrir_no_historico, tirar_do_historico
from apps.mapping.models import OfertaPocoInput
from apps.mapping.registro_desenho import REGISTRO_DESENHO
from services.domain.desenho import GavetaDesenhos, GavetaDesenhosInput, MontarGavetaDesenhos
from services.domain.historico_gaveta import Etiqueta, ItemHistorico, TipoGaveta

MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
MAP_INTERPOLATION_CRS: int = settings.MAP_INTERPOLATION_CRS
MAP_GEOGRAPHIC_CRS: int = settings.MAP_GEOGRAPHIC_CRS
TEMPLATE_GAVETA_DESENHOS = "mapping/_gaveta_desenhos.html"
CHAVE_GAVETA_DESENHOS = "desenhos"


def etiqueta_dos_desenhos(gaveta: GavetaDesenhos) -> Etiqueta:
    total = sum(len(poco.desenhos) for poco in gaveta.pocos)
    resumo = "1 desenho" if total == 1 else f"{total} desenhos"
    return Etiqueta(chave=CHAVE_GAVETA_DESENHOS, tipo=TipoGaveta.DESENHOS, resumo=resumo)


@require_POST
def desenhos_da_bancada(request: HttpRequest) -> HttpResponse:
    """Rota aberta (design/020 §3.5): monta a gaveta a partir dos traços que estão no mapa —
    sem ato administrativo, sem login exigido."""
    # `desenhos` chega como texto: o `_do_json` de GavetaDesenhosInput o decodifica antes de
    # validar, então o tipo estático do parâmetro não bate com o valor aceito em runtime.
    entrada = GavetaDesenhosInput(
        desenhos=request.POST.get("desenhos", "[]"),  # type: ignore[arg-type]
        id_selecionado=request.POST.get("selecionado") or None,
        crs_mapa=MAP_OUTPUT_CRS,
        crs_metrico=MAP_INTERPOLATION_CRS,
        crs_geografico=MAP_GEOGRAPHIC_CRS,
    )
    gaveta = MontarGavetaDesenhos()(entrada)
    etiqueta = etiqueta_dos_desenhos(gaveta)
    # Entra sem cena — é o mapa que a remonta — e sai quando não sobra desenho.
    if gaveta.pocos:
        abrir_no_historico(request.session, ItemHistorico(etiqueta=etiqueta))
    else:
        tirar_do_historico(request.session, etiqueta.chave)
    ofertar = OfertarNoPoco(REGISTRO_DESENHO)
    liberados = slugs_liberados(request.user)
    pocos = [
        (poco, ofertar(OfertaPocoInput(tipo=poco.tipo, slugs_liberados=liberados)))
        for poco in gaveta.pocos
    ]
    contexto = {"gaveta": gaveta, "pocos": pocos, "etiqueta": etiqueta}
    return render(request, TEMPLATE_GAVETA_DESENHOS, contexto)
