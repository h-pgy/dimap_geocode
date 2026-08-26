"""
Testes de apps/autenticacao/views.py (SPEC autenticacao/001): a consulta dinâmica de estado do RF,
a autenticação padrão via RF + senha, a validação da senha de uso único do primeiro acesso e o
logout — o contrato HTTP das cinco rotas do app.

Todos levam o marker `banco`: RF e `senha_provisoria` só se conferem contra o Postgres real.
"""

from django.test import Client
from django.urls import reverse

import pytest

from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, Perfil

banco = pytest.mark.banco

SENHA_DEFINITIVA = "SenhaForte123!"
OTP_VALIDO = "84921730"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(rf: str) -> TipoUnidade:
    return TipoUnidade.objects.create(
        nome=f"Divisão Autenticação {rf}",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )


def _unidade(rf: str) -> Unidade:
    return Unidade.objects.create(
        nome=f"Unidade Autenticação {rf}",
        sigla=f"AUT-{rf}",
        tipo=_tipo_unidade(rf),
    )


def _cargo_base() -> CargoBase:
    cargo, _ = CargoBase.objects.get_or_create(nome="Cargo Autenticação", sigla="CGAU")
    return cargo


def _perfil(rf: str, senha: str = SENHA_DEFINITIVA, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": "Fulana",
        "sobrenome": "Autenticação",
        "cargo_base": _cargo_base(),
        "unidade": _unidade(rf),
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password(senha)
    perfil.save()
    return perfil


# ---------------------------------------------------------------------------
# Consulta dinâmica de RF
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_checar_rf_com_senha_provisoria_devolve_botao_primeiro_login(client: Client) -> None:
    rf = "9501001"
    _perfil(rf, senha_provisoria=True)

    resposta = client.post(reverse("autenticacao:checar_rf"), {"rf": rf})
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "Primeiro Login" in html
    assert reverse("autenticacao:primeiro_login") in html


@banco
@pytest.mark.django_db
def test_checar_rf_com_senha_definitiva_devolve_campo_senha(client: Client) -> None:
    rf = "9501002"
    _perfil(rf, senha_provisoria=False)

    resposta = client.post(reverse("autenticacao:checar_rf"), {"rf": rf})
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert 'name="password"' in html
    assert "Primeiro Login" not in html


@banco
@pytest.mark.django_db
def test_checar_rf_inexistente_devolve_campo_senha_sem_revelar_inexistencia(client: Client) -> None:
    resposta = client.post(reverse("autenticacao:checar_rf"), {"rf": "9509999"})
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert 'name="password"' in html
    assert "Primeiro Login" not in html


# ---------------------------------------------------------------------------
# Autenticação padrão (RF + senha)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_login_com_credenciais_validas_autentica_e_redireciona(client: Client) -> None:
    rf = "9501003"
    perfil = _perfil(rf, senha_provisoria=False)

    resposta = client.post(
        reverse("autenticacao:login"), {"rf": rf, "password": SENHA_DEFINITIVA}
    )

    assert resposta.status_code == 302
    assert resposta.url == reverse("user_admin:pagina_perfil", kwargs={"pk": perfil.pk})
    assert client.session["_auth_user_id"] == str(perfil.pk)


@banco
@pytest.mark.django_db
def test_login_com_senha_invalida_recusa_com_mensagem_em_portugues_e_limpa_rf(
    client: Client,
) -> None:
    rf = "9501004"
    _perfil(rf, senha_provisoria=False)

    resposta = client.post(reverse("autenticacao:login"), {"rf": rf, "password": "senha-errada"})
    html = resposta.content.decode()

    assert resposta.status_code == 422
    assert "RF ou senha incorretos" in html
    assert f'value="{rf}"' not in html
    assert "_auth_user_id" not in client.session


# ---------------------------------------------------------------------------
# Validação do OTP de primeiro acesso
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_validar_otp_correto_autentica_sessao_e_redireciona_para_definir_senha(
    client: Client,
) -> None:
    rf = "9501005"
    perfil = _perfil(rf, senha=OTP_VALIDO, senha_provisoria=True)

    resposta = client.post(reverse("autenticacao:validar_otp"), {"rf": rf, "otp": OTP_VALIDO})

    assert resposta.status_code == 302
    assert resposta.url == reverse("autenticacao:definir_senha")
    assert client.session["_auth_user_id"] == str(perfil.pk)


@banco
@pytest.mark.django_db
def test_validar_otp_incorreto_devolve_recusa_com_campo_realcado(client: Client) -> None:
    rf = "9501006"
    _perfil(rf, senha=OTP_VALIDO, senha_provisoria=True)

    resposta = client.post(reverse("autenticacao:validar_otp"), {"rf": rf, "otp": "00000000"})
    html = resposta.content.decode()

    assert resposta.status_code == 422
    assert "campo-realce-erro" in html
    assert "Senha de uso único inválida" in html
    assert "_auth_user_id" not in client.session


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_logout_encerra_a_sessao_e_redireciona_ao_login(client: Client) -> None:
    perfil = _perfil("9501007")
    client.force_login(perfil)

    resposta = client.get(reverse("autenticacao:logout"))

    assert resposta.status_code == 302
    assert resposta.url == reverse("autenticacao:login")
    assert "_auth_user_id" not in client.session
