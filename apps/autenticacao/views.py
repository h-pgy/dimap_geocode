"""
Orquestração da entrada no sistema (SPEC autenticacao/001): a consulta dinâmica de estado do RF,
a autenticação padrão via `django.contrib.auth`, a validação do OTP de primeiro acesso, o logout, e
a recuperação de senha por link de uso único no e-mail (SPEC autenticacao/003).
"""

from typing import cast

from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from pydantic import HttpUrl, SecretStr

from apps.autenticacao.formularios import traduzir_recusa_login, traduzir_recusa_otp
from apps.autenticacao.recuperacao import (
    SESSAO_SENHA_SEM_ATUAL,
    enviar_link_recuperacao,
    resolver_destino_recuperacao,
    resolver_perfil_do_link,
)
from apps.autenticacao.schemas import (
    ConsultaRfInput,
    LinkRecuperacaoInput,
    PedidoRecuperacaoInput,
    ValidacaoOtpInput,
)
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


def _dispensa_senha_atual(request: HttpRequest) -> bool:
    """Senha de uso único do primeiro acesso e link de recuperação chegam no mesmo lugar: nos dois
    casos não existe senha atual que o servidor consiga informar."""
    perfil = cast(Perfil, request.user)
    return perfil.senha_provisoria or request.session.get(SESSAO_SENHA_SEM_ATUAL, False)


@login_required
def definir_senha_view(request: HttpRequest) -> HttpResponse:
    contexto = {"dispensa_senha_atual": _dispensa_senha_atual(request), **contexto_fundo_admin()}
    return render(request, TEMPLATE_DEFINIR_SENHA, contexto)


@login_required
def redefinir_senha_view(request: HttpRequest) -> HttpResponse:
    contexto = {"dispensa_senha_atual": False, **contexto_fundo_admin()}
    return render(request, TEMPLATE_DEFINIR_SENHA, contexto)


@login_required
@require_POST
def gravar_senha_view(request: HttpRequest) -> HttpResponse:
    perfil = cast(Perfil, request.user)
    dispensa = _dispensa_senha_atual(request)
    desfecho = gravar_senha(perfil, dispensa, request.POST)

    if not desfecho.sucesso:
        contexto = {
            "dispensa_senha_atual": dispensa,
            "recusa": desfecho.recusa,
            **contexto_fundo_admin(),
        }
        return render(request, TEMPLATE_DEFINIR_SENHA, contexto, status=422)

    if dispensa:
        # `logout` esvazia a sessão inteira, e com ela a chave da recuperação: a sessão seguinte
        # nasce com senha definitiva e exigindo a senha atual, como qualquer outra (SPEC, Caveats).
        logout(request)
        return redirect("autenticacao:login")

    update_session_auth_hash(request, perfil)
    return redirect(reverse("user_admin:pagina_perfil", kwargs={"pk": perfil.pk}))


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("autenticacao:login")


def esqueci_senha_view(request: HttpRequest) -> HttpResponse:
    destino = resolver_destino_recuperacao(ConsultaRfInput(rf=request.GET.get("rf", "").strip()))
    return render(
        request,
        "autenticacao/esqueci_senha.html",
        {"destino": destino, **contexto_fundo_admin()},
    )


@require_POST
def enviar_link_view(request: HttpRequest) -> HttpResponse:
    desfecho = enviar_link_recuperacao(
        PedidoRecuperacaoInput(
            rf=request.POST.get("rf", "").strip(),
            base_url=HttpUrl(request.build_absolute_uri("/")),
            validade_horas=settings.RECUPERACAO_SENHA_VALIDADE_HORAS,
        )
    )
    status = 422 if desfecho.recusa.mensagens else 200
    return render(
        request,
        "autenticacao/partials/_envio_recuperacao.html",
        {"desfecho": desfecho},
        status=status,
    )


def recuperar_senha_view(request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
    perfil = resolver_perfil_do_link(LinkRecuperacaoInput(uidb64=uidb64, token=token))
    if perfil is None:
        return render(
            request,
            "autenticacao/link_invalido.html",
            contexto_fundo_admin(),
            status=410,
        )
    # A ordem importa: `login()` atualiza `last_login`, que entra no hash do token — é esta linha
    # que queima o link, e ela só pode rodar depois de o token ter conferido.
    login(request, perfil, backend=BACKEND_AUTENTICACAO)
    request.session[SESSAO_SENHA_SEM_ATUAL] = True
    return redirect("autenticacao:definir_senha")
