from django.urls import path

from . import views

urlpatterns = [
    path("gestao/", views.lista, name="admin_lista"),
    path("gestao/corpo/", views.corpo, name="admin_corpo"),
    path("gestao/nova/", views.nova, name="admin_nova"),
    path("gestao/<int:faq_id>/", views.editar, name="admin_editar"),
    path("gestao/<int:faq_id>/situacao/", views.situacao, name="admin_situacao"),
    path("gestao/<int:faq_id>/excluir/", views.excluir, name="admin_excluir"),
    path("gestao/<int:faq_id>/restaurar/", views.restaurar, name="admin_restaurar"),
    path(
        "gestao/bloco/perguntas/", views.bloco_perguntas, name="admin_bloco_perguntas"
    ),
    path("gestao/bloco/links/", views.bloco_links, name="admin_bloco_links"),
    path(
        "gestao/bloco/relacionadas/",
        views.bloco_relacionadas,
        name="admin_bloco_relacionadas",
    ),
]
