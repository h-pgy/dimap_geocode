from django.urls import path

from apps.geocodificacao_externa import views

app_name = "geocodificacao_externa"

urlpatterns = [
    path("selecionar/", views.selecionar, name="selecionar"),
]
