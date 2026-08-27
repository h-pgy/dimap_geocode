"""
Testes de apps/autenticacao/views.py (SPEC autenticacao/001 e autenticacao/002): a consulta
dinâmica de estado do RF, a autenticação padrão via RF + senha, a validação da senha de uso único
do primeiro acesso, o logout, e a definição/redefinição de senha — o template compartilhado, a
política de senha forte e a exigência de senha atual fora do primeiro login.

Todos levam o marker `banco`: RF e `senha_provisoria` só se conferem contra o Postgres real.
"""

from bs4 import BeautifulSoup, Tag
from django.test import Client
from django.urls import reverse

import pytest

from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, Perfil

banco = pytest.mark.banco

SENHA_DEFINITIVA = "SenhaForte123!"
NOVA_SENHA_FORTE = "NovaSenhaForte456!"
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


def _controle(soup: BeautifulSoup, tag: str, nome: str) -> Tag:
    controle = soup.find(tag, attrs={"name": nome})
    assert isinstance(controle, Tag), f"a tela não trouxe o {tag} de {nome}"
    return controle


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


# ---------------------------------------------------------------------------
# Definição de senha no primeiro login (SPEC autenticacao/002)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_definir_senha_primeiro_login_grava_senha_e_desmarca_provisoria(client: Client) -> None:
    rf = "9501008"
    perfil = _perfil(rf, senha=OTP_VALIDO, senha_provisoria=True)
    client.force_login(perfil)

    client.post(
        reverse("autenticacao:gravar_senha"),
        {"nova_senha": NOVA_SENHA_FORTE, "confirmacao_senha": NOVA_SENHA_FORTE},
    )

    perfil.refresh_from_db()
    assert perfil.senha_provisoria is False
    assert perfil.check_password(NOVA_SENHA_FORTE)


@banco
@pytest.mark.django_db
def test_definir_senha_primeiro_login_desloga_e_redireciona_ao_login(client: Client) -> None:
    rf = "9501009"
    perfil = _perfil(rf, senha=OTP_VALIDO, senha_provisoria=True)
    client.force_login(perfil)

    resposta = client.post(
        reverse("autenticacao:gravar_senha"),
        {"nova_senha": NOVA_SENHA_FORTE, "confirmacao_senha": NOVA_SENHA_FORTE},
    )

    assert resposta.status_code == 302
    assert resposta.url == reverse("autenticacao:login")
    assert "_auth_user_id" not in client.session


# ---------------------------------------------------------------------------
# Redefinição voluntária de senha (SPEC autenticacao/002)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_redefinir_senha_com_senha_atual_correta_grava_nova_e_mantem_sessao(
    client: Client,
) -> None:
    rf = "9501010"
    perfil = _perfil(rf, senha_provisoria=False)
    client.force_login(perfil)

    resposta = client.post(
        reverse("autenticacao:gravar_senha"),
        {
            "senha_atual": SENHA_DEFINITIVA,
            "nova_senha": NOVA_SENHA_FORTE,
            "confirmacao_senha": NOVA_SENHA_FORTE,
        },
    )

    assert resposta.status_code == 302
    assert resposta.url == reverse("user_admin:pagina_perfil", kwargs={"pk": perfil.pk})
    assert client.session["_auth_user_id"] == str(perfil.pk)
    perfil.refresh_from_db()
    assert perfil.check_password(NOVA_SENHA_FORTE)


@banco
@pytest.mark.django_db
def test_redefinir_senha_com_senha_atual_incorreta_recusa_sem_alterar(client: Client) -> None:
    rf = "9501011"
    perfil = _perfil(rf, senha_provisoria=False)
    client.force_login(perfil)

    resposta = client.post(
        reverse("autenticacao:gravar_senha"),
        {
            "senha_atual": "senha-errada",
            "nova_senha": NOVA_SENHA_FORTE,
            "confirmacao_senha": NOVA_SENHA_FORTE,
        },
    )
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 422
    assert "campo-realce-erro" in _controle(soup, "input", "senha_atual")["class"]
    assert "A senha atual informada está incorreta." in html
    perfil.refresh_from_db()
    assert perfil.check_password(SENHA_DEFINITIVA)


# ---------------------------------------------------------------------------
# Validações compartilhadas pelo template de senha (SPEC autenticacao/002)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_senhas_divergentes_devolvem_recusa_no_formulario(client: Client) -> None:
    rf = "9501012"
    perfil = _perfil(rf, senha=OTP_VALIDO, senha_provisoria=True)
    client.force_login(perfil)

    resposta = client.post(
        reverse("autenticacao:gravar_senha"),
        {"nova_senha": NOVA_SENHA_FORTE, "confirmacao_senha": "SenhaDiferente789!"},
    )
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 422
    assert "campo-realce-erro" in _controle(soup, "input", "nova_senha")["class"]
    assert "campo-realce-erro" in _controle(soup, "input", "confirmacao_senha")["class"]
    assert "As senhas digitadas não coincidem" in html
    perfil.refresh_from_db()
    assert perfil.senha_provisoria is True


@banco
@pytest.mark.django_db
def test_senha_que_viola_politica_forte_e_recusada(client: Client) -> None:
    rf = "9501013"
    perfil = _perfil(rf, senha=OTP_VALIDO, senha_provisoria=True)
    client.force_login(perfil)

    resposta = client.post(
        reverse("autenticacao:gravar_senha"),
        {"nova_senha": "fraca123", "confirmacao_senha": "fraca123"},
    )
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 422
    assert "campo-realce-erro" in _controle(soup, "input", "nova_senha")["class"]
    assert "A nova senha deve conter pelo menos uma letra maiúscula." in html
    perfil.refresh_from_db()
    assert perfil.senha_provisoria is True


@banco
@pytest.mark.django_db
def test_anonimo_acessando_definir_ou_redefinir_e_redirecionado_ao_login(client: Client) -> None:
    resposta_definir = client.get(reverse("autenticacao:definir_senha"))
    resposta_redefinir = client.get(reverse("autenticacao:redefinir_senha"))

    assert resposta_definir.status_code == 302
    assert resposta_definir.url.startswith(reverse("autenticacao:login"))
    assert resposta_redefinir.status_code == 302
    assert resposta_redefinir.url.startswith(reverse("autenticacao:login"))


@banco
@pytest.mark.django_db
def test_servidor_com_senha_definitiva_acessando_definir_senha_exige_senha_atual(
    client: Client,
) -> None:
    rf = "9501014"
    perfil = _perfil(rf, senha_provisoria=False)
    client.force_login(perfil)

    # A URL de primeiro acesso não basta para dispensar a senha atual: quem decide é a flag do
    # perfil, não a rota visitada — por isso o form já chega pedindo o campo aqui também.
    html_definir = client.get(reverse("autenticacao:definir_senha")).content.decode()
    assert 'name="senha_atual"' in html_definir

    resposta = client.post(
        reverse("autenticacao:gravar_senha"),
        {"nova_senha": NOVA_SENHA_FORTE, "confirmacao_senha": NOVA_SENHA_FORTE},
    )
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 422
    assert "campo-realce-erro" in _controle(soup, "input", "senha_atual")["class"]
    perfil.refresh_from_db()
    assert perfil.check_password(SENHA_DEFINITIVA)
