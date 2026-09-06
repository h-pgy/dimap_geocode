from django.urls import path

from apps.core import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("design_system/", views.design_system, name="design_system"),
    path("_teste/validacao/", views.teste_validacao, name="teste_validacao"),
]
