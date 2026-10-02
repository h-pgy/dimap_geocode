from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET
from pydantic import BaseModel, Field

from apps.mapping.context import contexto_aviso
from services.domain.geometry import PointGeometry
from services.domain.street_view import LinkStreetViewInput, MontarLinkStreetView

MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS
STREET_VIEW_CRS: int = settings.STREET_VIEW_CRS

TEMPLATE_AVISO_POPUP_BLOQUEADO = "street_view/partials/_aviso_popup_bloqueado.html"

MSG_POPUP_BLOQUEADO = (
    "O navegador bloqueou a janela da Visão da rua. "
    "Libere os pop-ups para este site e tente de novo."
)


class ConsultaStreetView(BaseModel):
    lon: float
    lat: float


class AvisoPopupBloqueado(BaseModel):
    # A forma barra qualquer coisa que não seja id: a rota desmarca o toggle que o cliente nomear.
    toggle: str = Field(pattern=r"^[a-z][a-z0-9-]*$")


@login_required  # basta estar autenticado: sem contrato de ação
@require_GET
def abrir(request: HttpRequest) -> HttpResponse:
    consulta = ConsultaStreetView.model_validate(request.GET.dict())
    entrada = LinkStreetViewInput(
        ponto=PointGeometry(type="Point", coordinates=[consulta.lon, consulta.lat]),
        crs_ponto=MAP_OUTPUT_CRS,
        crs_street_view=STREET_VIEW_CRS,
    )
    montar_link = MontarLinkStreetView()
    link = montar_link(entrada)
    return redirect(link.url)


@login_required
@require_GET
def popup_bloqueado(request: HttpRequest) -> HttpResponse:
    aviso = AvisoPopupBloqueado.model_validate(request.GET.dict())
    contexto = contexto_aviso(MSG_POPUP_BLOQUEADO, tom="error") | {"toggle": aviso.toggle}
    return render(request, TEMPLATE_AVISO_POPUP_BLOQUEADO, contexto)
