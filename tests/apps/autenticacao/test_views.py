"""
Testes de apps/autenticacao/views.py (SPEC autenticacao/001, autenticacao/002, autenticacao/003 e
autenticacao/004): a consulta dinâmica de estado do RF, a autenticação padrão via RF + senha, a
validação da senha de uso único do primeiro acesso, o logout, a definição/redefinição de senha — o
template compartilhado, a política de senha forte e a exigência de senha atual fora do primeiro
login —, o consumo do link de recuperação de senha por e-mail e o reenvio da senha de uso único.

Todos levam o marker `banco`: RF e `senha_provisoria` só se conferem contra o Postgres real.
"""

from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag
from django.contrib.auth.tokens import default_token_generator
from django.test import Client
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

import pytest
from pytest_django.fixtures import SettingsWrapper

from apps.autenticacao import recuperacao, reenvio
from apps.autenticacao.schemas import ReenvioSenhaInput
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


def _link_de_recuperacao(perfil: Perfil, token: str | None = None) -> str:
    """O link de consumo montado direto pelo gerador do Django, sem passar pela emissão cacheada
    de `recuperacao.py` — o que este arquivo fixa é o comportamento da rota de consumo, não o da
    emissão (coberta em `tests/apps/autenticacao/test_recuperacao.py`)."""
    return reverse(
        "autenticacao:recuperar_senha",
        kwargs={
            "uidb64": urlsafe_base64_encode(force_bytes(perfil.pk)),
            "token": token or default_token_generator.make_token(perfil),
        },
    )


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
def test_logout_encerra_a_sessao_por_post_e_recusa_get(client: Client) -> None:
    perfil = _perfil("9501007")
    client.force_login(perfil)

    recusa = client.get(reverse("autenticacao:logout"))

    assert recusa.status_code == 405
    assert "_auth_user_id" in client.session

    resposta = client.post(reverse("autenticacao:logout"))

    assert resposta.status_code == 302
    assert resposta.url == reverse("autenticacao:login")
    assert "_auth_user_id" not in client.session


@banco
@pytest.mark.django_db
def test_logout_sem_o_token_csrf_nao_encerra_a_sessao() -> None:
    cliente = Client(enforce_csrf_checks=True)
    perfil = _perfil("9501008")
    cliente.force_login(perfil)

    resposta = cliente.post(reverse("autenticacao:logout"))

    assert resposta.status_code == 403
    assert "_auth_user_id" in cliente.session


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


# ---------------------------------------------------------------------------
# Aviso de pedido de redefinição em aberto no login (SPEC autenticacao/003)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_login_avisa_pedido_de_redefinicao_em_aberto(client: Client) -> None:
    rf = "9502100"
    perfil = _perfil(rf, senha_provisoria=False)

    antes = client.post(reverse("autenticacao:checar_rf"), {"rf": rf}).content.decode()
    assert "Já pedimos uma redefinição de senha" not in antes

    link = recuperacao.montar_link_recuperacao(perfil, "https://geocoder.dimap.local/")
    depois = client.post(reverse("autenticacao:checar_rf"), {"rf": rf}).content.decode()
    assert "Já pedimos uma redefinição de senha" in depois

    resposta_consumo = client.get(urlparse(link).path)
    assert resposta_consumo.status_code == 302
    client.logout()

    apos_consumo = client.post(reverse("autenticacao:checar_rf"), {"rf": rf}).content.decode()
    assert "Já pedimos uma redefinição de senha" not in apos_consumo


# ---------------------------------------------------------------------------
# Consumo do link de recuperação (SPEC autenticacao/003)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_link_valido_autentica_e_leva_a_definir_senha_sem_senha_atual(client: Client) -> None:
    rf = "9502110"
    perfil = _perfil(rf, senha_provisoria=False)

    resposta = client.get(_link_de_recuperacao(perfil))

    assert resposta.status_code == 302
    assert resposta.url == reverse("autenticacao:definir_senha")
    assert client.session["_auth_user_id"] == str(perfil.pk)

    tela = client.get(reverse("autenticacao:definir_senha")).content.decode()
    assert 'name="senha_atual"' not in tela


@banco
@pytest.mark.django_db
def test_link_reaberto_apos_consumo_responde_410_sem_autenticar(client: Client) -> None:
    rf = "9502120"
    perfil = _perfil(rf, senha_provisoria=False)
    link = _link_de_recuperacao(perfil)

    primeira = client.get(link)
    assert primeira.status_code == 302
    client.logout()

    segunda = client.get(link)

    assert segunda.status_code == 410
    assert "_auth_user_id" not in client.session


@banco
@pytest.mark.django_db
def test_link_vencido_ou_adulterado_responde_410(
    client: Client,
    settings: SettingsWrapper,
) -> None:
    perfil_a = _perfil("9502130", senha_provisoria=False)
    perfil_b = _perfil("9502131", senha_provisoria=False)

    # -1, e não 0: `check_token` recusa só quando o tempo decorrido EXCEDE o timeout, e token
    # emitido e conferido no mesmo segundo decorre 0 — com timeout 0 o link não vence de verdade.
    settings.PASSWORD_RESET_TIMEOUT = -1
    vencido = client.get(_link_de_recuperacao(perfil_a))
    assert vencido.status_code == 410
    assert "_auth_user_id" not in client.session

    settings.PASSWORD_RESET_TIMEOUT = 3600
    token_de_b = default_token_generator.make_token(perfil_b)
    adulterado = client.get(_link_de_recuperacao(perfil_a, token=token_de_b))

    assert adulterado.status_code == 410
    assert "_auth_user_id" not in client.session


# ---------------------------------------------------------------------------
# Definir senha pela recuperação encerra a sessão, como no primeiro acesso (SPEC autenticacao/003)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_gravar_senha_pela_recuperacao_encerra_a_sessao_e_leva_ao_login(client: Client) -> None:
    rf = "9502140"
    perfil = _perfil(rf, senha_provisoria=False)
    client.get(_link_de_recuperacao(perfil))

    resposta = client.post(
        reverse("autenticacao:gravar_senha"),
        {"nova_senha": NOVA_SENHA_FORTE, "confirmacao_senha": NOVA_SENHA_FORTE},
    )

    assert resposta.status_code == 302
    assert resposta.url == reverse("autenticacao:login")
    assert "_auth_user_id" not in client.session
    perfil.refresh_from_db()
    assert perfil.check_password(NOVA_SENHA_FORTE)


# ---------------------------------------------------------------------------
# Reenvio da senha de uso único do primeiro acesso (SPEC autenticacao/004)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_codigo_substituido_recusa_dizendo_que_foi_trocado(
    client: Client,
    settings: SettingsWrapper,
) -> None:
    settings.EMAIL_ENVIO_HABILITADO = False
    rf = "9503200"
    codigo_antigo = OTP_VALIDO
    _perfil(rf, senha=codigo_antigo, senha_provisoria=True, email=f"{rf}@prefeitura.sp.gov.br")

    desfecho = reenvio.reenviar_senha_uso_unico(
        ReenvioSenhaInput(rf=rf, url_acesso="https://geocoder.dimap.local/")
    )
    assert desfecho.senha_a_exibir is not None
    codigo_novo = desfecho.senha_a_exibir.get_secret_value()

    resposta_substituido = client.post(
        reverse("autenticacao:validar_otp"), {"rf": rf, "otp": codigo_antigo}
    )
    assert resposta_substituido.status_code == 422
    assert "foi substituída por um reenvio" in resposta_substituido.content.decode()

    resposta_errado = client.post(
        reverse("autenticacao:validar_otp"), {"rf": rf, "otp": "00000000"}
    )
    html_errado = resposta_errado.content.decode()
    assert resposta_errado.status_code == 422
    assert "foi substituída" not in html_errado
    assert "Senha de uso único inválida" in html_errado

    resposta_novo = client.post(
        reverse("autenticacao:validar_otp"), {"rf": rf, "otp": codigo_novo}
    )
    assert resposta_novo.status_code == 302


@banco
@pytest.mark.django_db
def test_login_em_primeiro_acesso_oferece_o_reenvio(client: Client) -> None:
    rf_primeiro_acesso = "9503210"
    _perfil(rf_primeiro_acesso, senha_provisoria=True)
    rf_senha_definitiva = "9503211"
    _perfil(rf_senha_definitiva, senha_provisoria=False)

    primeiro_acesso = client.post(
        reverse("autenticacao:checar_rf"), {"rf": rf_primeiro_acesso}
    ).content.decode()
    ramo_senha = client.post(
        reverse("autenticacao:checar_rf"), {"rf": rf_senha_definitiva}
    ).content.decode()

    alvo_reenvio = f"{reverse('autenticacao:esqueci_senha')}?rf={rf_primeiro_acesso}"
    assert "Reenviar senha de uso único" in primeiro_acesso
    assert alvo_reenvio in primeiro_acesso
    assert "Reenviar senha de uso único" not in ramo_senha


@banco
@pytest.mark.django_db
def test_telas_de_recuperacao_e_de_codigo_oferecem_o_reenvio_ativo(client: Client) -> None:
    rf = "9503220"
    _perfil(rf, senha_provisoria=True, email=f"{rf}@prefeitura.sp.gov.br")
    url_reenvio = reverse("autenticacao:reenviar_senha_unico")

    tela_recuperacao = client.get(
        reverse("autenticacao:esqueci_senha"), {"rf": rf}
    ).content.decode()
    soup_recuperacao = BeautifulSoup(tela_recuperacao, "html.parser")
    botao_recuperacao = soup_recuperacao.select_one("[data-reenvio-acionador]")
    assert isinstance(botao_recuperacao, Tag)
    assert botao_recuperacao.get("disabled") is None
    assert url_reenvio in tela_recuperacao

    tela_codigo = client.get(
        f"{reverse('autenticacao:primeiro_login')}?rf={rf}"
    ).content.decode()
    soup_codigo = BeautifulSoup(tela_codigo, "html.parser")
    botao_codigo = soup_codigo.select_one("[data-reenvio-acionador]")
    assert isinstance(botao_codigo, Tag)
    assert botao_codigo.get("disabled") is None
    assert url_reenvio in tela_codigo
