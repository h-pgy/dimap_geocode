from django.urls import path

from apps.logradouro_geocoder import views

app_name = "logradouro_geocoder"

urlpatterns = [
    path("geocodificar/", views.geocodificar, name="geocodificar"),
]
