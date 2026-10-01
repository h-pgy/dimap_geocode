from django.urls import path
from . import views

app_name = "acoes_lote"

urlpatterns = [
    path("acoes/", views.acoes, name="acoes"),
    path("acoes-conjunto/", views.acoes_conjunto, name="acoes_conjunto"),
]
