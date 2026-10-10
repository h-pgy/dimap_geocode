from django.urls import path

from services.domain.documento_selado.constants import ROTA_CONFERENCIA

from . import views

app_name = "documentos"

urlpatterns = [
    path(f"{ROTA_CONFERENCIA}/", views.pagina_conferencia, name="pagina"),
    # Antes da rota do código, que casaria com qualquer texto — e "conferir" não é código válido
    # de todo jeito: o alfabeto da SPEC 007 não tem minúscula.
    path(f"{ROTA_CONFERENCIA}/conferir", views.conferir_arquivo, name="conferir_arquivo"),
    path(f"{ROTA_CONFERENCIA}/<str:codigo>", views.conferir_por_codigo, name="conferir"),
    path(f"{ROTA_CONFERENCIA}/<str:codigo>/original", views.segunda_via, name="segunda_via"),
]
