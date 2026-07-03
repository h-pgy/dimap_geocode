from django.urls import path

from apps.lote_geocoder import views

app_name = "lote_geocoder"

urlpatterns = [
    path("geocodificar/", views.geocodificar, name="geocodificar"),
]
