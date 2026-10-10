from django.urls import path

from apps.logradouro_mais_proximo import views

app_name = "logradouro_mais_proximo"

urlpatterns = [
    path("do-ponto/", views.do_ponto, name="do_ponto"),
]
