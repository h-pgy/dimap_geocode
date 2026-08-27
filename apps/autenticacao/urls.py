from django.urls import path

from apps.autenticacao import views

app_name = "autenticacao"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("login/checar-rf/", views.checar_rf_view, name="checar_rf"),
    path("primeiro-login/", views.primeiro_login_otp_view, name="primeiro_login"),
    path("primeiro-login/validar/", views.validar_otp_view, name="validar_otp"),
    # SPEC autenticacao/002: template compartilhado entre primeiro acesso e redefinição voluntária.
    path("definir-senha/", views.definir_senha_view, name="definir_senha"),
    path("redefinir-senha/", views.redefinir_senha_view, name="redefinir_senha"),
    path("gravar-senha/", views.gravar_senha_view, name="gravar_senha"),
    path("logout/", views.logout_view, name="logout"),
]
