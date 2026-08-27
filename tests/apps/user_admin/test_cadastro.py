"""
Testes de apps/user_admin/cadastro.py (SPEC criacao_usuarios/004): o ato de criar servidor —
gravar e entregar a senha temporária são a mesma transação; falha na entrega desfaz o cadastro, e
envio desligado por configuração o conclui. A política de e-mail institucional é conferida antes de
gerar senha ou abrir conversa com o SMTP.

O enviador é sempre um fake (monkeypatch de `entrega_email.EnviadorSmtp`, no molde de
`tests/apps/user_admin/test_enviar_email_teste.py`): nenhum destes testes abre conexão real. Todos levam
o marker `banco`: o cadastro grava `Perfil`.
"""

from typing import Any

from pydantic import SecretStr
import pytest
from pytest_django.fixtures import SettingsWrapper

from apps.core import entrega_email
from apps.user_admin import cadastro
from apps.user_admin.cadastro import ERRO_DOMINIO, ERRO_ENVIO, ERRO_SEM_CANETA, criar_servidor
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, Perfil
from services.utils.smtp import MensagemEmail, ResultadoEnvio, SmtpEnvioError

banco = pytest.mark.banco

SENHA_FIXA = SecretStr("12345678")


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


class EnviadorFake:
    """Substitui o `EnviadorSmtp`: guarda a mensagem entregue e devolve o desfecho combinado, ou
    levanta o que a chamada precisar simular."""

    def __init__(self, resultado: ResultadoEnvio | None = None, erro: Exception | None = None) -> None:
        self.resultado = resultado
        self.erro = erro
        self.mensagens: list[MensagemEmail] = []

    def __call__(self, mensagem: MensagemEmail) -> ResultadoEnvio:
        self.mensagens.append(mensagem)
        if self.erro is not None:
            raise self.erro
        assert self.resultado is not None
        return self.resultado


def _resultado(**overrides: Any) -> ResultadoEnvio:
    defaults: dict[str, Any] = {"entregue_ao_servidor": True, "destinatarios_recusados": ()}
    return ResultadoEnvio(**(defaults | overrides))


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Cadastro",
        "nivel": 10,
        "pode_ser_raiz": True,
        "nivel_minimo_titular": 1,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(**overrides: object) -> Unidade:
    dados: dict[str, object] = {
        "nome": "Divisão de Cadastro",
        "sigla": "CAD-1",
        "tipo": _tipo_unidade(),
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base(**overrides: object) -> CargoBase:
    dados: dict[str, object] = {"nome": "Analista de Cadastro", "sigla": "ANC"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _novo_servidor(unidade: Unidade, cargo_base: CargoBase, **overrides: object) -> dict[str, Any]:
    """O formulário cru, como o POST o entrega: quem monta o DTO é o `LeitorDeFormulario`."""
    dados: dict[str, Any] = {
        "rf": "9201000",
        "nome": "Fulano",
        "sobrenome": "de Cadastro",
        "email": "fulano.cadastro@prefeitura.sp.gov.br",
        "unidade_id": str(unidade.pk),
        "cargo_base_id": str(cargo_base.pk),
        "cargo_comissao_id": "",
        "url_acesso": "https://geocoder.dimap.local/",
    }
    dados.update(overrides)
    return dados


def _preparar(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
    enviador: EnviadorFake,
) -> None:
    # O envio precisa estar ligado para o código chegar ao `EnviadorSmtp` (aqui trocado pelo fake):
    # com a guarda de `EMAIL_ENVIO_HABILITADO` em `entregar_email`, envio desligado retorna antes.
    settings.EMAIL_ENVIO_HABILITADO = True
    settings.EMAIL_SMTP_USUARIO = "dimap.geocoder@example.com"
    monkeypatch.setattr(cadastro, "gerar_senha_temporaria", lambda *args, **kwargs: SENHA_FIXA)
    monkeypatch.setattr(entrega_email, "EnviadorSmtp", lambda *args: enviador)


# ---------------------------------------------------------------------------
# O cadastro em si: gravação e senha
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_cadastro_grava_o_servidor(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    _preparar(monkeypatch, settings, EnviadorFake(_resultado()))
    unidade = _unidade()
    cargo = _cargo_base()

    desfecho = criar_servidor(
        _novo_servidor(unidade, cargo, rf="9201010", email="ciclano@prefeitura.sp.gov.br")
    )

    assert desfecho.recusa.mensagens == ()
    assert desfecho.perfil is not None
    perfil = Perfil.objects.get(rf="9201010")
    assert perfil.email == "ciclano@prefeitura.sp.gov.br"
    assert perfil.check_password(SENHA_FIXA.get_secret_value())
    assert perfil.senha_provisoria is True


@banco
@pytest.mark.django_db
def test_senha_temporaria_sai_no_email_do_servidor(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    enviador = EnviadorFake(_resultado())
    _preparar(monkeypatch, settings, enviador)
    unidade = _unidade()
    cargo = _cargo_base()

    criar_servidor(
        _novo_servidor(
            unidade, cargo, rf="9201020", nome="Beltrano", email="beltrano@prefeitura.sp.gov.br"
        )
    )

    mensagem = enviador.mensagens[0]
    assert mensagem.destinatarios == ("beltrano@prefeitura.sp.gov.br",)
    assert "9201020" in mensagem.corpo_texto
    assert SENHA_FIXA.get_secret_value() in mensagem.corpo_texto


# ---------------------------------------------------------------------------
# Falha na entrega desfaz o cadastro; envio desligado por configuração o conclui
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_falha_na_entrega_desfaz_o_cadastro(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    unidade = _unidade()
    cargo = _cargo_base()

    _preparar(monkeypatch, settings, EnviadorFake(erro=SmtpEnvioError("servidor fora do ar")))
    indisponivel = criar_servidor(
        _novo_servidor(unidade, cargo, rf="9201030", email="indisponivel@prefeitura.sp.gov.br")
    )
    assert indisponivel.perfil is None
    assert indisponivel.recusa.mensagens == (
        ERRO_ENVIO.format(email="indisponivel@prefeitura.sp.gov.br"),
    )
    # Falha de entrega realça o e-mail: é o endereço que precisa mudar (SPEC 004, Caveats).
    assert indisponivel.recusa.realce["email"] == "campo-realce-erro"
    assert not Perfil.objects.filter(rf="9201030").exists()

    _preparar(
        monkeypatch,
        settings,
        EnviadorFake(_resultado(destinatarios_recusados=("recusado@prefeitura.sp.gov.br",))),
    )
    recusado = criar_servidor(
        _novo_servidor(unidade, cargo, rf="9201040", email="recusado@prefeitura.sp.gov.br")
    )
    assert recusado.perfil is None
    assert not Perfil.objects.filter(rf="9201040").exists()

    _preparar(monkeypatch, settings, EnviadorFake(_resultado(entregue_ao_servidor=False)))
    desligado = criar_servidor(
        _novo_servidor(unidade, cargo, rf="9201050", email="desligado@prefeitura.sp.gov.br")
    )
    assert desligado.recusa.mensagens == ()
    assert desligado.perfil is not None
    assert Perfil.objects.filter(rf="9201050").exists()


# ---------------------------------------------------------------------------
# Política de e-mail institucional
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_email_fora_do_dominio_e_recusado_com_a_politica_ligada(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    enviador = EnviadorFake(_resultado())
    _preparar(monkeypatch, settings, enviador)
    unidade = _unidade()
    cargo = _cargo_base()
    settings.ENFORCE_PREFEITURA_EMAIL = True

    recusado = criar_servidor(_novo_servidor(unidade, cargo, rf="9201060", email="fulano@gmail.com"))
    assert recusado.perfil is None
    assert recusado.recusa.mensagens == (ERRO_DOMINIO,)
    assert recusado.recusa.realce["email"] == "campo-realce-erro"
    assert enviador.mensagens == []
    assert not Perfil.objects.filter(rf="9201060").exists()

    settings.ENFORCE_PREFEITURA_EMAIL = False
    aceito = criar_servidor(_novo_servidor(unidade, cargo, rf="9201070", email="fulano2@gmail.com"))
    assert aceito.recusa.mensagens == ()
    assert aceito.perfil is not None


# ---------------------------------------------------------------------------
# RF e e-mail únicos: cadastro existente segue intocado
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_rf_ou_email_repetido_e_recusado_sem_gravar(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    _preparar(monkeypatch, settings, EnviadorFake(_resultado()))
    unidade = _unidade()
    cargo = _cargo_base()
    existente = criar_servidor(
        _novo_servidor(unidade, cargo, rf="9201080", email="existente@prefeitura.sp.gov.br")
    ).perfil
    assert existente is not None

    rf_repetido = criar_servidor(
        _novo_servidor(unidade, cargo, rf="9201080", email="outro@prefeitura.sp.gov.br")
    )
    assert rf_repetido.perfil is None
    # A mensagem é a do model, e o realce cai no controle que repetiu — não na tarja do `__all__`.
    assert rf_repetido.recusa.mensagens == ("Já existe servidor cadastrado com este RF.",)
    assert rf_repetido.recusa.realce == {"rf": "campo-realce-erro"}
    assert Perfil.objects.filter(rf="9201080").count() == 1

    email_repetido = criar_servidor(
        _novo_servidor(unidade, cargo, rf="9201090", email="existente@prefeitura.sp.gov.br")
    )
    assert email_repetido.perfil is None
    assert email_repetido.recusa.mensagens == ("Já existe servidor cadastrado com este e-mail.",)
    assert email_repetido.recusa.realce == {"email": "campo-realce-erro"}
    assert Perfil.objects.filter(email="existente@prefeitura.sp.gov.br").count() == 1


# ---------------------------------------------------------------------------
# A marca de administrador (SPEC user_admin/022): nasce junto do cadastro, e só com a caneta
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_cadastro_com_marca_nasce_administrador(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    _preparar(monkeypatch, settings, EnviadorFake(_resultado()))
    unidade = _unidade()
    cargo = _cargo_base()

    desfecho = criar_servidor(
        _novo_servidor(
            unidade, cargo, rf="9202000", email="admin.novo@prefeitura.sp.gov.br", administrador="true"
        ),
        administrador_permitido=True,
    )

    assert desfecho.recusa.mensagens == ()
    assert desfecho.perfil is not None
    assert desfecho.perfil.is_superuser is True
    perfil = Perfil.objects.get(rf="9202000")
    assert perfil.is_superuser is True


@banco
@pytest.mark.django_db
def test_cadastro_com_marca_sem_caneta_recusa_tudo(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    enviador = EnviadorFake(_resultado())
    _preparar(monkeypatch, settings, enviador)
    unidade = _unidade()
    cargo = _cargo_base()

    desfecho = criar_servidor(
        _novo_servidor(
            unidade, cargo, rf="9202010", email="sem.caneta@prefeitura.sp.gov.br", administrador="true"
        ),
        administrador_permitido=False,
    )

    assert desfecho.perfil is None
    assert desfecho.recusa.mensagens == (ERRO_SEM_CANETA,)
    assert desfecho.recusa.realce == {"administrador": "campo-realce-erro"}
    assert not Perfil.objects.filter(rf="9202010").exists()
    # Nada tenta sair pela rede: a recusa acontece antes da senha e do envio.
    assert enviador.mensagens == []


# ---------------------------------------------------------------------------
# Envio desligado devolve a senha para a tela (SPEC criacao_usuarios/007)
# ---------------------------------------------------------------------------


def _preparar_sem_envio(monkeypatch: pytest.MonkeyPatch, settings: SettingsWrapper) -> None:
    """Envio desligado: `entregar_email` volta antes do SMTP, e a senha sobrevive ao ato."""
    settings.EMAIL_ENVIO_HABILITADO = False
    monkeypatch.setattr(cadastro, "gerar_senha_temporaria", lambda *args, **kwargs: SENHA_FIXA)


@banco
@pytest.mark.django_db
def test_envio_desligado_devolve_senha_no_desfecho(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    _preparar_sem_envio(monkeypatch, settings)
    unidade = _unidade()
    cargo = _cargo_base()

    desfecho = criar_servidor(
        _novo_servidor(unidade, cargo, rf="9203000", email="sem.envio@prefeitura.sp.gov.br")
    )

    assert desfecho.perfil is not None
    assert desfecho.senha_a_exibir is not None
    assert desfecho.senha_a_exibir.get_secret_value() == SENHA_FIXA.get_secret_value()


@banco
@pytest.mark.django_db
def test_envio_ligado_nao_devolve_senha_no_desfecho(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    _preparar(monkeypatch, settings, EnviadorFake(_resultado()))
    unidade = _unidade()
    cargo = _cargo_base()

    desfecho = criar_servidor(
        _novo_servidor(unidade, cargo, rf="9203010", email="com.envio@prefeitura.sp.gov.br")
    )

    assert desfecho.perfil is not None
    assert desfecho.senha_a_exibir is None


@banco
@pytest.mark.django_db
def test_senha_exibida_autentica_o_servidor(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    """A senha da tela é a que foi gravada — não outra sorteada no caminho de exibição."""
    _preparar_sem_envio(monkeypatch, settings)
    unidade = _unidade()
    cargo = _cargo_base()

    desfecho = criar_servidor(
        _novo_servidor(unidade, cargo, rf="9203020", email="autentica@prefeitura.sp.gov.br")
    )

    assert desfecho.perfil is not None
    assert desfecho.senha_a_exibir is not None
    perfil = Perfil.objects.get(rf="9203020")
    assert perfil.check_password(desfecho.senha_a_exibir.get_secret_value())
