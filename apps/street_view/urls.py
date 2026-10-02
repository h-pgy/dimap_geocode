from django.urls import path

from apps.street_view import views

app_name = "street_view"

urlpatterns = [
    path("abrir/", views.abrir, name="abrir"),
    path("popup-bloqueado/", views.popup_bloqueado, name="popup_bloqueado"),
]
