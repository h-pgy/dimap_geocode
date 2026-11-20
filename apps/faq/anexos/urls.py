from django.urls import path

from . import views

urlpatterns = [
    path("anexos/<int:anexo_id>/", views.baixar, name="anexo_baixar"),
    path("gestao/anexos/conferir/", views.conferir, name="admin_anexo_conferir"),
    path("gestao/anexos/buscar/", views.buscar, name="admin_anexo_buscar"),
    path("gestao/anexos/<int:anexo_id>/texto/", views.texto, name="admin_anexo_texto"),
    path("gestao/bloco/anexos/", views.bloco_anexos, name="admin_bloco_anexos"),
]
