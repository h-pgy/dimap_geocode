from django.urls import path
from . import views

app_name = "acoes_lote"

urlpatterns = [
    path("acoes/", views.acoes, name="acoes"),
]
