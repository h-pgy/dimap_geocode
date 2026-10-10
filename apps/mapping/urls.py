from django.urls import path

from apps.mapping import views

app_name = "mapping"

urlpatterns = [
    path("fundo-ortofoto/", views.fundo_ortofoto, name="fundo_ortofoto"),
    path("desenhos-da-bancada/", views.desenhos_da_bancada, name="desenhos_da_bancada"),
    path("historico-da-gaveta/", views.historico_gaveta, name="historico_gaveta"),
    path("devolver-cena/", views.devolver_cena, name="devolver_cena"),
]
