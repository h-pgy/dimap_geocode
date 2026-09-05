"""
Testes de apps/autenticacao/recuperacao.py (SPEC autenticacao/003): a emissão do link de uso único
por e-mail — quem pode recebê-lo, a janela de reenvio e a exibição do link em desenvolvimento.

O enviador é sempre um fake (monkeypatch de `recuperacao.entregar_email`, no molde de
`tests/apps/user_admin/test_cadastro.py`): nenhum destes testes abre conexão real. Todos levam o
marker `banco`: a recuperação lê `Perfil` e usa o cache do processo para o token e a janela.
"""

import time
from typing import Any

from django.utils import timezone
from pytest_django.fixtures import SettingsWrapper
import pytest

from apps.autenticacao import recuperacao
from apps.autenticacao.schemas import PedidoRecuperacaoInput
from apps.unidades.models import TipoUnidade, Unidade
from apps.cargos.models import CargoBase
from apps.user_admin.models import Perfil
from services.utils.smtp import MensagemEmail

banco = pytest.mark.banco

BASE_URL = "https://geocoder.dimap.local/"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


class EntregaEmailFake:
    """Substitui `recuperacao.entregar_email`: guarda as mensagens entregues e devolve o desfecho
    combinado, ou levanta o que a chamada precisar simular."""

    def __init__(self, entregue: bool = True, erro: Exception | None = None) -> None:
        self.entregue = entregue
        self.erro = erro
        self.mensagens: list[MensagemEmail] = []

    def __call__(self, mensagem: MensagemEmail) -> bool:
        self.mensagens.append(mensagem)
        if self.erro is not None:
            raise self.erro
        return self.entregue


class _Relogio:
    """Substitui `time.time` do módulo: `enviar_link_recuperacao` mede a janela de reenvio em
    tempo real, e o teste precisa andar o relógio sem dormir de verdade."""

    def __init__(self, agora: float) -> None:
        self._agora = agora

    def __call__(self) -> float:
        return self._agora

    def avancar(self, segundos: float) -> None:
        self._agora += segundos


def _tipo_unidade(rf: str) -> TipoUnidade:
    return TipoUnidade.objects.create(
        nome=f"Divisão Recuperação {rf}",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )


def _unidade(rf: str) -> Unidade:
    return Unidade.objects.create(
        nome=f"Unidade Recuperação {rf}",
        sigla=f"REC-{rf}",
        tipo=_tipo_unidade(rf),
    )


def _cargo_base() -> CargoBase:
    cargo, _ = CargoBase.objects.get_or_create(nome="Cargo Recuperação", sigla="CGRC")
    return cargo


def _perfil(rf: str, **overrides: Any) -> Perfil:
    dados: dict[str, Any] = {
        "rf": rf,
        "nome": "Fulana",
        "sobrenome": "Recuperação",
        "email": f"{rf}@prefeitura.sp.gov.br",
        "cargo_base": _cargo_base(),
        "unidade": _unidade(rf),
    }
    dados.update(overrides)
    perfil = Perfil(**dados)
    perfil.set_password("SenhaAtual123!")
    perfil.save()
    return perfil


def _pedido(rf: str, validade_horas: int = 1) -> PedidoRecuperacaoInput:
    return PedidoRecuperacaoInput(rf=rf, base_url=BASE_URL, validade_horas=validade_horas)


# ---------------------------------------------------------------------------
# Quem pode receber o link
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_pedido_com_rf_ativo_entrega_mensagem_com_o_link(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    settings.PASSWORD_RESET_TIMEOUT = 3600
    entrega = EntregaEmailFake()
    monkeypatch.setattr(recuperacao, "entregar_email", entrega)
    perfil = _perfil("9510010", senha_provisoria=False)

    desfecho = recuperacao.enviar_link_recuperacao(_pedido("9510010"))

    assert desfecho.enviado is True
    assert desfecho.email == perfil.email
    assert len(entrega.mensagens) == 1
    mensagem = entrega.mensagens[0]
    assert mensagem.destinatarios == (perfil.email,)
    link = recuperacao.montar_link_recuperacao(perfil, BASE_URL)
    assert link in mensagem.corpo_texto


@banco
@pytest.mark.django_db
def test_pedido_para_rf_nao_recuperavel_nao_entrega_nada(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    settings.PASSWORD_RESET_TIMEOUT = 3600
    entrega = EntregaEmailFake()
    monkeypatch.setattr(recuperacao, "entregar_email", entrega)
    _perfil(
        "9510021", senha_provisoria=False, is_active=False, exonerado_em=timezone.localdate()
    )
    _perfil("9510022", senha_provisoria=True)

    inexistente = recuperacao.enviar_link_recuperacao(_pedido("9510020"))
    inativo = recuperacao.enviar_link_recuperacao(_pedido("9510021"))
    primeiro_acesso = recuperacao.enviar_link_recuperacao(_pedido("9510022"))

    assert inexistente.enviado is False
    assert inativo.enviado is False
    assert primeiro_acesso.enviado is False
    assert entrega.mensagens == []


# ---------------------------------------------------------------------------
# Janela de reenvio: mesmo link enquanto ele valer, um novo depois de vencida
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_pedido_repetido_segura_o_envio_na_janela_e_reaproveita_o_link_depois(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    settings.PASSWORD_RESET_TIMEOUT = 3600
    entrega = EntregaEmailFake()
    monkeypatch.setattr(recuperacao, "entregar_email", entrega)
    relogio = _Relogio(1_700_000_000.0)
    monkeypatch.setattr(time, "time", relogio)
    perfil = _perfil("9510030", senha_provisoria=False)

    primeiro = recuperacao.enviar_link_recuperacao(_pedido("9510030"))
    assert primeiro.enviado is True
    assert primeiro.espera_segundos == 0
    assert len(entrega.mensagens) == 1

    relogio.avancar(60)
    segundo = recuperacao.enviar_link_recuperacao(_pedido("9510030"))
    assert segundo.espera_segundos > 0
    assert len(entrega.mensagens) == 1

    link_na_janela = recuperacao.montar_link_recuperacao(perfil, BASE_URL)

    relogio.avancar(120)
    terceiro = recuperacao.enviar_link_recuperacao(_pedido("9510030"))
    assert terceiro.espera_segundos == 0
    assert len(entrega.mensagens) == 2

    link_apos_janela = recuperacao.montar_link_recuperacao(perfil, BASE_URL)
    assert link_apos_janela == link_na_janela


# ---------------------------------------------------------------------------
# Exibição do link com o envio desligado (SPEC criacao_usuarios/007)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_com_envio_desligado_o_link_aparece_na_tela_e_com_envio_ligado_nao(
    monkeypatch: pytest.MonkeyPatch,
    settings: SettingsWrapper,
) -> None:
    settings.PASSWORD_RESET_TIMEOUT = 3600
    perfil = _perfil("9510040", senha_provisoria=False)

    monkeypatch.setattr(recuperacao, "entregar_email", EntregaEmailFake(entregue=False))
    desligado = recuperacao.enviar_link_recuperacao(_pedido("9510040"))
    assert desligado.link_a_exibir is not None
    assert desligado.link_a_exibir == recuperacao.montar_link_recuperacao(perfil, BASE_URL)

    monkeypatch.setattr(recuperacao, "entregar_email", EntregaEmailFake(entregue=True))
    ligado = recuperacao.enviar_link_recuperacao(_pedido("9510040"))
    assert ligado.link_a_exibir is None
