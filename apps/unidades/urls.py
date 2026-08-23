from django.urls import path

from apps.unidades import views

app_name = "unidades"

urlpatterns = [
    path("nova/", views.criar_unidade, name="criar_unidade"),
    path(
        "cor-sugerida/",
        views.cor_sugerida_unidade,
        name="cor_sugerida_unidade",
    ),
    path("arvore/", views.arvore_de_unidades, name="arvore_de_unidades"),
    path("<int:pk>/", views.pagina_unidade, name="pagina_unidade"),
]
