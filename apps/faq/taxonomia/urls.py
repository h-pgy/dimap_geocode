from django.urls import path

from . import views

urlpatterns = [
    path(
        "gestao/palavras-chave/coluna/",
        views.coluna,
        name="admin_palavras_chave_coluna",
    ),
    path(
        "gestao/palavras-chave/marcadas/",
        views.marcadas,
        name="admin_palavras_chave_marcadas",
    ),
    path(
        "gestao/palavras-chave/nova/",
        views.palavra_chave_nova,
        name="admin_palavra_chave_nova",
    ),
    path(
        "gestao/palavras-chave/<int:palavra_id>/renomear/",
        views.palavra_chave_renomear,
        name="admin_palavra_chave_renomear",
    ),
    path(
        "gestao/palavras-chave/relacionadas/",
        views.relacionadas_palavra,
        name="admin_palavra_chave_relacionadas",
    ),
    path("gestao/temas/novo/", views.tema_novo, name="admin_tema_novo"),
    path("gestao/temas/renomear/", views.tema_renomear, name="admin_tema_renomear"),
]
