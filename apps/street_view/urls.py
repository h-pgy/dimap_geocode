from django.urls import path

from apps.street_view import views

app_name = "street_view"

urlpatterns = [
    path("abrir/", views.abrir, name="abrir"),
    path("fechar/", views.fechar, name="fechar"),
]
