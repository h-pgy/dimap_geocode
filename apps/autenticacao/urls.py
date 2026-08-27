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
    # SPEC autenticacao/003: recuperação de senha por link de uso único no e-mail.
    path("esqueci-minha-senha/", views.esqueci_senha_view, name="esqueci_senha"),
    path("esqueci-minha-senha/enviar/", views.enviar_link_view, name="enviar_link_recuperacao"),
    path(
        "recuperar-senha/<str:uidb64>/<str:token>/",
        views.recuperar_senha_view,
        name="recuperar_senha",
    ),
    # SPEC autenticacao/004: reenvio da senha de uso único do primeiro acesso.
    path(
        "esqueci-minha-senha/reenviar-senha/",
        views.reenviar_senha_unico_view,
        name="reenviar_senha_unico",
    ),
]
