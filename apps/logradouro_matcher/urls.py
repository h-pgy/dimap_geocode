from django.urls import path

from apps.logradouro_matcher import views

app_name = "logradouro_matcher"

urlpatterns = [
    path("logradouro/buscar-codlog/", views.buscar_codlog, name="buscar_codlog"),
]
