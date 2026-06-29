from django.urls import path

from apps.logradouro_matcher import views

app_name = "logradouro_matcher"

urlpatterns = [
    path("selecionar/", views.selecionar, name="selecionar"),
]
