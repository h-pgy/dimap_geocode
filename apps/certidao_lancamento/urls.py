from django.urls import path
from . import views

app_name = "certidao_lancamento"

urlpatterns = [
    path("modal/", views.modal, name="modal"),
    path("emitir/", views.emitir, name="emitir"),
]
