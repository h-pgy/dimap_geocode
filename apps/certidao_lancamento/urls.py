from django.urls import path
from . import views

app_name = "certidao_lancamento"

urlpatterns = [
    path("modal/", views.modal, name="modal"),
    path("emitir/", views.emitir, name="emitir"),
    path("conjunto/modal/", views.modal_conjunto, name="modal_conjunto"),
    path("conjunto/emitir/", views.emitir_conjunto, name="emitir_conjunto"),
]
