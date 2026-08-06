from django.urls import path

from apps.user_admin import views

app_name = "user_admin"

urlpatterns = [
    path("servidores/novo/", views.criar_perfil, name="criar_perfil"),
    path("servidores/<int:pk>/editar/", views.editar_perfil, name="editar_perfil"),
    path("unidades/nova/", views.criar_unidade, name="criar_unidade"),
    path(
        "unidades/cor-sugerida/",
        views.cor_sugerida_unidade,
        name="cor_sugerida_unidade",
    ),
]
