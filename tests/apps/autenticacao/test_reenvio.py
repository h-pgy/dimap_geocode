"""
Testes de apps/autenticacao/reenvio.py (SPEC autenticacao/004): o reenvio da senha de uso único do
primeiro acesso — reenviar a mesma senha enquanto ela valer, emitir outra quando não houver cópia
guardada, e a janela de reenvio compartilhada com a recuperação de senha.

O enviador é sempre um fake (monkeypatch de `reenvio.entregar_email_de_acesso`, no molde de
`tests/apps/autenticacao/test_recuperacao.py`): nenhum destes testes abre conexão real. Todos levam
o marker `banco`: o reenvio lê `Perfil` e usa o cache do processo para a senha e a janela.
"""

import time
from typing import Any

from django.core.cache import cache
from django.utils import timezone

import pytest

from apps.autenticacao import reenvio
from apps.autenticacao.schemas import ReenvioSenhaInput
from apps.unidades.models import TipoUnidade, Unidade
from apps.cargos.models import CargoBase
from apps.user_admin.models import Perfil
from services.domain.email import EmailAcessoInput
from services.utils.smtp import SmtpEnvioError

banco = pytest.mark.banco

URL_ACESSO = "https://geocoder.dimap.local/"
SENHA_ORIGINAL = "11112222"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


class EntregaAcessoFake:
    """Substitui `reenvio.entregar_email_de_acesso`: guarda os pedidos entregues e devolve o
    desfecho combinado, ou levanta o que a chamada precisar simular."""

    def __init__(self, entregue: bool = True, erro: Exception | None = None) -> None:
        self.entregue = entregue
        self.erro = erro
        self.pedidos: list[EmailAcessoInput] = []

    def __call__(self, pedido: EmailAcessoInput) -> bool:
        self.pedidos.append(pedido)
        if self.erro is not None:
            raise self.erro
        return self.entregue


class _Relogio:
    """Substitui `time.time`: a janela de reenvio e o prazo da mesma senha são medidos em tempo
    real, e o teste precisa andar o relógio sem dormir de verdade."""

    def __init__(self, agora: float) -> None:
        self._agora = agora

    def __call__(self) -> float:
        return self._agora

    def avancar(self, segundos: float) -> None:
        self._agora += segundos


def _tipo_unidade(rf: str) -> TipoUnidade:
    return TipoUnidade.objects.create(
        nome=f"Divisão Reenvio {rf}",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )


def _unidade(rf: str) -> Unidade:
    return Unidade.objects.create(
        nome=f"Unidade Reenvio {rf}",
        sigla=f"REV-{rf}",
        tipo=_tipo_unidade(rf),
    )


def _cargo_base() -> CargoBase:
    cargo, _ = CargoBase.objects.get_or_create(nome="Cargo Reenvio", sigla="CGRV")
    return cargo


def _perfil(rf: str, senha: str = SENHA_ORIGINAL, **overrides: Any) -> Perfil:
    dados: dict[str, Any] = {
        "rf": rf,
        "nome": "Fulana",
        "sobrenome": "Reenvio",
        "email": f"{rf}@prefeitura.sp.gov.br",
        "cargo_base": _cargo_base(),
        "unidade": _unidade(rf),
        "senha_provisoria": True,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)
    perfil.set_password(senha)
    perfil.save()
    return perfil


def _pedido(rf: str) -> ReenvioSenhaInput:
    return ReenvioSenhaInput(rf=rf, url_acesso=URL_ACESSO)


# ---------------------------------------------------------------------------
# Emissão: sem cópia guardada, o pedido sorteia e grava uma senha nova
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_sem_copia_guardada_o_pedido_emite_uma_senha_nova(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entrega = EntregaAcessoFake()
    monkeypatch.setattr(reenvio, "entregar_email_de_acesso", entrega)
    perfil = _perfil("9520001")

    desfecho = reenvio.reenviar_senha_uso_unico(_pedido("9520001"))

    assert desfecho.enviado is True
    assert len(entrega.pedidos) == 1
    nova_senha = entrega.pedidos[0].senha_temporaria.get_secret_value()
    assert nova_senha != SENHA_ORIGINAL
    perfil.refresh_from_db()
    assert not perfil.check_password(SENHA_ORIGINAL)
    assert perfil.check_password(nova_senha)


# ---------------------------------------------------------------------------
# Reenvio: enquanto a senha guardada valer, o pedido seguinte repete; perdida a cópia, emite outra
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_pedido_seguinte_reenvia_a_mesma_senha(monkeypatch: pytest.MonkeyPatch) -> None:
    entrega = EntregaAcessoFake()
    monkeypatch.setattr(reenvio, "entregar_email_de_acesso", entrega)
    relogio = _Relogio(1_700_000_000.0)
    monkeypatch.setattr(time, "time", relogio)
    perfil = _perfil("9520010")

    reenvio.reenviar_senha_uso_unico(_pedido("9520010"))
    senha_emitida = entrega.pedidos[0].senha_temporaria.get_secret_value()

    # Vence a janela de 120s entre envios, mas não o prazo de 300s da mesma senha guardada.
    relogio.avancar(130)
    segundo = reenvio.reenviar_senha_uso_unico(_pedido("9520010"))

    assert segundo.enviado is True
    assert len(entrega.pedidos) == 2
    assert entrega.pedidos[1].senha_temporaria.get_secret_value() == senha_emitida
    perfil.refresh_from_db()
    assert perfil.check_password(senha_emitida)

    # Cópia perdida (expirada ou reiniciada): o pedido seguinte emite outra senha.
    cache.delete(reenvio.CHAVE_SENHA.format(pk=perfil.pk))
    relogio.avancar(130)
    reenvio.reenviar_senha_uso_unico(_pedido("9520010"))
    terceira_senha = entrega.pedidos[2].senha_temporaria.get_secret_value()

    assert terceira_senha != senha_emitida
    perfil.refresh_from_db()
    assert perfil.check_password(terceira_senha)


# ---------------------------------------------------------------------------
# Falha na entrega não troca a senha
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_falha_na_entrega_nao_troca_a_senha(monkeypatch: pytest.MonkeyPatch) -> None:
    entrega = EntregaAcessoFake(erro=SmtpEnvioError("destinatário recusado"))
    monkeypatch.setattr(reenvio, "entregar_email_de_acesso", entrega)
    perfil = _perfil("9520020")

    desfecho = reenvio.reenviar_senha_uso_unico(_pedido("9520020"))

    assert desfecho.enviado is False
    assert desfecho.recusa.mensagens
    perfil.refresh_from_db()
    assert perfil.check_password(SENHA_ORIGINAL)
    assert cache.get(reenvio.CHAVE_SENHA.format(pk=perfil.pk)) is None


# ---------------------------------------------------------------------------
# RF sem senha de uso único a reenviar não produz nenhum efeito
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_rf_sem_primeiro_acesso_nao_envia_nada(monkeypatch: pytest.MonkeyPatch) -> None:
    entrega = EntregaAcessoFake()
    monkeypatch.setattr(reenvio, "entregar_email_de_acesso", entrega)
    _perfil("9520031", senha_provisoria=False)
    _perfil("9520032", is_active=False, exonerado_em=timezone.localdate())
    _perfil("9520033", email="")

    inexistente = reenvio.reenviar_senha_uso_unico(_pedido("9520030"))
    definitiva = reenvio.reenviar_senha_uso_unico(_pedido("9520031"))
    inativo = reenvio.reenviar_senha_uso_unico(_pedido("9520032"))
    sem_email = reenvio.reenviar_senha_uso_unico(_pedido("9520033"))

    assert inexistente.enviado is False
    assert definitiva.enviado is False
    assert inativo.enviado is False
    assert sem_email.enviado is False
    assert entrega.pedidos == []


# ---------------------------------------------------------------------------
# Janela entre envios: pedido repetido não chama o SMTP; vencida, a mensagem sai
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_pedido_repetido_segura_o_envio_na_janela(monkeypatch: pytest.MonkeyPatch) -> None:
    entrega = EntregaAcessoFake()
    monkeypatch.setattr(reenvio, "entregar_email_de_acesso", entrega)
    relogio = _Relogio(1_700_000_000.0)
    monkeypatch.setattr(time, "time", relogio)
    perfil = _perfil("9520040")

    primeiro = reenvio.reenviar_senha_uso_unico(_pedido("9520040"))
    assert primeiro.enviado is True
    assert primeiro.espera_segundos == 0
    perfil.refresh_from_db()
    hash_apos_primeiro = perfil.password

    relogio.avancar(30)
    segundo = reenvio.reenviar_senha_uso_unico(_pedido("9520040"))
    assert segundo.espera_segundos > 0
    assert len(entrega.pedidos) == 1
    perfil.refresh_from_db()
    assert perfil.password == hash_apos_primeiro

    relogio.avancar(130)
    terceiro = reenvio.reenviar_senha_uso_unico(_pedido("9520040"))
    assert terceiro.espera_segundos == 0
    assert len(entrega.pedidos) == 2


# ---------------------------------------------------------------------------
# Exibição da senha em tela com o envio desligado (SPEC criacao_usuarios/007)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_com_envio_desligado_a_senha_sai_no_modal_e_com_envio_ligado_nao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _perfil("9520050")

    monkeypatch.setattr(reenvio, "entregar_email_de_acesso", EntregaAcessoFake(entregue=False))
    desligado = reenvio.reenviar_senha_uso_unico(_pedido("9520050"))
    assert desligado.enviado is False
    assert desligado.senha_a_exibir is not None

    monkeypatch.setattr(reenvio, "entregar_email_de_acesso", EntregaAcessoFake(entregue=True))
    ligado = reenvio.reenviar_senha_uso_unico(_pedido("9520050"))
    assert ligado.enviado is True
    assert ligado.senha_a_exibir is None
