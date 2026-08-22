"""
Testes de apps/user_admin/cadastro.py (SPEC criacao_usuarios/004): o ato de criar servidor —
gravar e entregar a senha temporária são a mesma transação; falha na entrega desfaz o cadastro, e
envio desligado por configuração o conclui. A política de e-mail institucional é conferida antes de
gerar senha ou abrir conversa com o SMTP.

O enviador é sempre um fake (monkeypatch de `cadastro.EnviadorSmtp`, no molde de
`tests/apps/user_admin/test_enviar_email_teste.py`): nenhum destes testes abre conexão real. Todos levam
o marker `banco`: o cadastro grava `Perfil`.
"""

from typing import Any

from pydantic import SecretStr
import pytest
from pytest_django.fixtures import SettingsWrapper

from apps.user_admin import cadastro
from apps.user_admin.cadastro import ERRO_DOMINIO, ERRO_ENVIO, criar_servidor
from apps.user_admin.models import CargoBase, Perfil, TipoUnidade, Unidade
from apps.user_admin.schemas import NovoServidor
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


def _novo_servidor(unidade: Unidade, cargo_base: CargoBase, **overrides: object) -> NovoServidor:
    dados: dict[str, object] = {
        "rf": "920100",
        "nome": "Fulano",
        "sobrenome": "de Cadastro",
        "email": "fulano.cadastro@prefeitura.sp.gov.br",
        "unidade_id": unidade.pk,
        "cargo_base_id": cargo_base.pk,
        "cargo_comissao_id": None,
        "url_acesso": "https://geocoder.dimap.local/",
    }
    dados.update(overrides)
    return NovoServidor(**dados)  # type: ignore[arg-type]


def _preparar(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
    enviador: EnviadorFake,
) -> None:
    # EMAIL_SMTP_USUARIO precisa validar como EmailStr mesmo com o enviador trocado: é
    # `build_smtp_config` quem monta o `SmtpConfig`, e ele roda antes de `EnviadorSmtp` ser chamado.
    settings.EMAIL_SMTP_USUARIO = "dimap.geocoder@example.com"
    monkeypatch.setattr(cadastro, "gerar_senha_temporaria", lambda *args, **kwargs: SENHA_FIXA)
    monkeypatch.setattr(cadastro, "EnviadorSmtp", lambda *args: enviador)


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
        _novo_servidor(unidade, cargo, rf="920101", email="ciclano@prefeitura.sp.gov.br")
    )

    assert desfecho.erros == ()
    assert desfecho.perfil is not None
    perfil = Perfil.objects.get(rf="920101")
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
            unidade, cargo, rf="920102", nome="Beltrano", email="beltrano@prefeitura.sp.gov.br"
        )
    )

    mensagem = enviador.mensagens[0]
    assert mensagem.destinatarios == ("beltrano@prefeitura.sp.gov.br",)
    assert "920102" in mensagem.corpo_texto
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
        _novo_servidor(unidade, cargo, rf="920103", email="indisponivel@prefeitura.sp.gov.br")
    )
    assert indisponivel.perfil is None
    assert indisponivel.erros == (ERRO_ENVIO.format(email="indisponivel@prefeitura.sp.gov.br"),)
    assert not Perfil.objects.filter(rf="920103").exists()

    _preparar(
        monkeypatch,
        settings,
        EnviadorFake(_resultado(destinatarios_recusados=("recusado@prefeitura.sp.gov.br",))),
    )
    recusado = criar_servidor(
        _novo_servidor(unidade, cargo, rf="920104", email="recusado@prefeitura.sp.gov.br")
    )
    assert recusado.perfil is None
    assert not Perfil.objects.filter(rf="920104").exists()

    _preparar(monkeypatch, settings, EnviadorFake(_resultado(entregue_ao_servidor=False)))
    desligado = criar_servidor(
        _novo_servidor(unidade, cargo, rf="920105", email="desligado@prefeitura.sp.gov.br")
    )
    assert desligado.erros == ()
    assert desligado.perfil is not None
    assert Perfil.objects.filter(rf="920105").exists()


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

    recusado = criar_servidor(_novo_servidor(unidade, cargo, rf="920106", email="fulano@gmail.com"))
    assert recusado.perfil is None
    assert recusado.erros == (ERRO_DOMINIO,)
    assert enviador.mensagens == []
    assert not Perfil.objects.filter(rf="920106").exists()

    settings.ENFORCE_PREFEITURA_EMAIL = False
    aceito = criar_servidor(_novo_servidor(unidade, cargo, rf="920107", email="fulano2@gmail.com"))
    assert aceito.erros == ()
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
        _novo_servidor(unidade, cargo, rf="920108", email="existente@prefeitura.sp.gov.br")
    ).perfil
    assert existente is not None

    rf_repetido = criar_servidor(
        _novo_servidor(unidade, cargo, rf="920108", email="outro@prefeitura.sp.gov.br")
    )
    assert rf_repetido.perfil is None
    assert rf_repetido.erros != ()
    assert Perfil.objects.filter(rf="920108").count() == 1

    email_repetido = criar_servidor(
        _novo_servidor(unidade, cargo, rf="920109", email="existente@prefeitura.sp.gov.br")
    )
    assert email_repetido.perfil is None
    assert email_repetido.erros != ()
    assert Perfil.objects.filter(email="existente@prefeitura.sp.gov.br").count() == 1
