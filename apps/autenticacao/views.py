"""
Orquestração da entrada no sistema (SPEC autenticacao/001): a consulta dinâmica de estado do RF,
a autenticação padrão via `django.contrib.auth`, a validação do OTP de primeiro acesso e o logout.
"""

from typing import cast

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from pydantic import SecretStr

from apps.autenticacao.formularios import traduzir_recusa_login, traduzir_recusa_otp
from apps.autenticacao.schemas import ConsultaRfInput, ValidacaoOtpInput
from apps.autenticacao.senha import gravar_senha
from apps.autenticacao.services import autenticar_primeiro_login, resolver_estado_rf
from apps.mapping.context import contexto_fundo_admin
from apps.user_admin.models import Perfil
from services.utils.erros_formulario import ErroBruto

ERRO_LOGIN = "RF ou senha incorretos."
ERRO_OTP = "Senha de uso único inválida: confira o código recebido no e-mail institucional."
# A validação do OTP confere a senha via `check_password`, e não `authenticate()` — sem backend
# explícito, `login()` não sabe escolher entre os dois de AUTHENTICATION_BACKENDS (autenticação e
# autorização por competência).
BACKEND_AUTENTICACAO = "django.contrib.auth.backends.ModelBackend"


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect(reverse("user_admin:pagina_perfil", kwargs={"pk": request.user.pk}))
    if request.method == "POST":
        rf = request.POST.get("rf", "").strip()
        senha = request.POST.get("password", "")
        user = authenticate(request, username=rf, password=senha)
        if user is None or not user.is_active:
            recusa = traduzir_recusa_login((ErroBruto(controle="rf", tipo="invalido", mensagem=ERRO_LOGIN),))
            # RF limpo, e não preservado: o campo pré-preenchido convidaria a testar senhas em
            # sequência contra o mesmo RF sem digitar nada de novo.
            contexto = {"recusa": recusa, "rf": "", **contexto_fundo_admin()}
            return render(request, "autenticacao/login.html", contexto, status=422)
        login(request, user)
        return redirect(reverse("user_admin:pagina_perfil", kwargs={"pk": user.pk}))
    return render(request, "autenticacao/login.html", contexto_fundo_admin())


@require_POST
def checar_rf_view(request: HttpRequest) -> HttpResponse:
    rf = request.POST.get("rf", "").strip()
    estado = resolver_estado_rf(ConsultaRfInput(rf=rf))
    return render(
        request,
        "autenticacao/partials/_campo_login_dinamico.html",
        {"estado": estado},
    )


def primeiro_login_otp_view(request: HttpRequest) -> HttpResponse:
    rf = request.GET.get("rf", "").strip()
    return render(request, "autenticacao/primeiro_login.html", {"rf": rf, **contexto_fundo_admin()})


@require_POST
def validar_otp_view(request: HttpRequest) -> HttpResponse:
    rf = request.POST.get("rf", "").strip()
    otp = request.POST.get("otp", "").strip()
    validacao = ValidacaoOtpInput(rf=rf, codigo_otp=SecretStr(otp))
    perfil = autenticar_primeiro_login(validacao)
    if perfil is None:
        recusa = traduzir_recusa_otp((ErroBruto(controle="otp", tipo="invalido", mensagem=ERRO_OTP),))
        return render(
            request,
            "autenticacao/primeiro_login.html",
            {"rf": rf, "recusa": recusa, **contexto_fundo_admin()},
            status=422,
        )
    # Sessão de primeiro acesso: `senha_provisoria` segue True até a SPEC autenticacao/002 gravar
    # a senha definitiva — é o que permite `/definir-senha/` proteger por `@login_required` sem
    # token nem cookie fora do motor de sessões do Django.
    login(request, perfil, backend=BACKEND_AUTENTICACAO)
    return redirect("autenticacao:definir_senha")


TEMPLATE_DEFINIR_SENHA = "autenticacao/definir_senha.html"


@login_required
def definir_senha_view(request: HttpRequest) -> HttpResponse:
    # Quem decide o modo é a flag do perfil, não a rota visitada: um servidor com senha definitiva
    # que caia aqui (ex.: link antigo) já recebe o formulário pedindo a senha atual.
    perfil = cast(Perfil, request.user)
    contexto = {"eh_primeiro_login": perfil.senha_provisoria, **contexto_fundo_admin()}
    return render(request, TEMPLATE_DEFINIR_SENHA, contexto)


@login_required
def redefinir_senha_view(request: HttpRequest) -> HttpResponse:
    contexto = {"eh_primeiro_login": False, **contexto_fundo_admin()}
    return render(request, TEMPLATE_DEFINIR_SENHA, contexto)


@login_required
@require_POST
def gravar_senha_view(request: HttpRequest) -> HttpResponse:
    perfil = cast(Perfil, request.user)
    eh_primeiro_login = perfil.senha_provisoria
    desfecho = gravar_senha(perfil, eh_primeiro_login, request.POST)

    if not desfecho.sucesso:
        contexto = {
            "eh_primeiro_login": eh_primeiro_login,
            "recusa": desfecho.recusa,
            **contexto_fundo_admin(),
        }
        return render(request, TEMPLATE_DEFINIR_SENHA, contexto, status=422)

    if eh_primeiro_login:
        # A sessão de primeiro acesso não sobrevive à senha definitiva: o servidor entra de novo,
        # já com a credencial que acabou de escolher (SPEC, Caveats).
        logout(request)
        return redirect("autenticacao:login")

    update_session_auth_hash(request, perfil)
    return redirect(reverse("user_admin:pagina_perfil", kwargs={"pk": perfil.pk}))


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("autenticacao:login")
