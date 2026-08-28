from django.urls import path

from apps.mapping import views

app_name = "mapping"

urlpatterns = [
    path("fundo-ortofoto/", views.fundo_ortofoto, name="fundo_ortofoto"),
]
