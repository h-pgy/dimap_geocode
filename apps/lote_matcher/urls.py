from django.urls import path

from apps.lote_matcher import views

app_name = "lote_matcher"

urlpatterns = [
    path("selecionar/", views.selecionar, name="selecionar"),
]
