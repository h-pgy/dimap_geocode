from django.urls import path

from apps.endereco_mais_proximo import views

app_name = "endereco_mais_proximo"

urlpatterns = [
    path("do-ponto/", views.do_ponto, name="do_ponto"),
]
