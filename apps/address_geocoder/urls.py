from django.urls import path

from apps.address_geocoder import views

app_name = "address_geocoder"

urlpatterns = [
    path("selecionar/", views.selecionar, name="selecionar"),
]
