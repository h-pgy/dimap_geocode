from django.urls import path

from apps.search import views

app_name = "search"

urlpatterns = [
    path("buscar/", views.rotear_busca, name="rotear_busca"),
]
