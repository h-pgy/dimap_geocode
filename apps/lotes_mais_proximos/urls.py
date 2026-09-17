from django.urls import path

from apps.lotes_mais_proximos import views

app_name = "lotes_mais_proximos"

urlpatterns = [
    path("mais-proximo/", views.mais_proximo, name="mais_proximo"),
]
