from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from pydantic import BaseModel, SecretStr

from apps.mapping.models import Limpeza
from services.domain.geometry import PointGeometry
from services.domain.street_view import MontarPedidoPanorama, PedidoPanoramaInput

MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
STREET_VIEW_CRS: int = settings.STREET_VIEW_CRS
STREET_VIEW_RAIO_M: float = settings.STREET_VIEW_RAIO_M
GOOGLE_MAPS_BROWSER_KEY: SecretStr = settings.GOOGLE_MAPS_BROWSER_KEY

SLUG_CONTEXTO = "street-view"
TEMPLATE_GAVETA = "street_view/partials/_gaveta_panorama.html"
TEMPLATE_ENCERRAMENTO = "street_view/partials/_encerramento.html"

MSG_SEM_IMAGEM = "O Google não tem imagem de rua a até {raio} m deste ponto."
MSG_SEM_IMAGEM_NO_DESTINO = "Não há imagem de rua a até {raio} m de onde o pino foi solto."
MSG_INDISPONIVEL = "A Visão da rua está indisponível no momento."


class ConsultaStreetView(BaseModel):
    lon: float
    lat: float


def _faltas(raio_m: float) -> dict[str, str]:
    raio = f"{raio_m:.0f}"
    return {
        "sem_imagem": MSG_SEM_IMAGEM.format(raio=raio),
        "sem_imagem_no_destino": MSG_SEM_IMAGEM_NO_DESTINO.format(raio=raio),
        "indisponivel": MSG_INDISPONIVEL,
    }


@login_required  # basta estar autenticado: sem contrato de ação
@require_GET
def abrir(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaStreetView.model_validate(request.GET.dict())
    entrada = PedidoPanoramaInput(
        ponto=PointGeometry(type="Point", coordinates=[consulta.lon, consulta.lat]),
        crs_ponto=MAP_OUTPUT_CRS,
        crs_street_view=STREET_VIEW_CRS,
        raio_m=STREET_VIEW_RAIO_M,
    )
    montar_pedido = MontarPedidoPanorama()
    pedido = montar_pedido(entrada)
    contexto = {
        "pedido": pedido,
        "chave": GOOGLE_MAPS_BROWSER_KEY.get_secret_value(),
        "faltas": _faltas(pedido.raio_m),
        "acao": SLUG_CONTEXTO,
        # O contexto não nasceu de um desenho: nenhum fica inerte ao clique.
        "desenho": "",
        "limpeza_ao_fechar": Limpeza(url=reverse("street_view:fechar"), aviso=None),
    }
    return render(request, TEMPLATE_GAVETA, contexto)


@login_required
@require_POST
def fechar(request: HttpRequest) -> HttpResponse:
    return render(request, TEMPLATE_ENCERRAMENTO)
