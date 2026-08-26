from django.urls import path

from apps.autenticacao import views

app_name = "autenticacao"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("login/checar-rf/", views.checar_rf_view, name="checar_rf"),
    path("primeiro-login/", views.primeiro_login_otp_view, name="primeiro_login"),
    path("primeiro-login/validar/", views.validar_otp_view, name="validar_otp"),
    # Rota reservada pela SPEC autenticacao/002: o redirecionamento pós-OTP já aponta para cá.
    path("definir-senha/", views.definir_senha_view, name="definir_senha"),
    path("logout/", views.logout_view, name="logout"),
]
