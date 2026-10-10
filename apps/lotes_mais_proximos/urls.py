from django.urls import path

from apps.lotes_mais_proximos import views

app_name = "lotes_mais_proximos"

urlpatterns = [
    path("mais-proximo/", views.mais_proximo, name="mais_proximo"),
    path("mais-proximo-do-ponto/", views.mais_proximo_do_ponto, name="mais_proximo_do_ponto"),
    path("do-desenho/", views.lotes_do_desenho, name="lotes_do_desenho"),
    path("do-desenho/remover/", views.remover_do_conjunto, name="remover_do_conjunto"),
    path("do-desenho/limpar/", views.limpar_conjunto, name="limpar_conjunto"),
    path("do-desenho/fechar/", views.fechar_conjunto, name="fechar_conjunto"),
    path("detalhe/", views.detalhe_do_lote, name="detalhe_do_lote"),
]
