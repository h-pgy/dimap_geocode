"""
Testes de `sincronizar_acoes` (SPEC autorizacao/002): a projeção do catálogo em código é
idempotente, e ação que sai do registro é desativada sem perder o que já foi concedido — voltando,
reativa e reencontra atribuições e concessões intactas.
"""

import pytest

from apps.competencias.models import Acao as AcaoModel
from apps.competencias.models import AtribuicaoUnidade, Concessao
from apps.competencias.schemas import AcaoImplementada, RegistroAcoes
from apps.competencias.sync import sincronizar_acoes
from apps.user_admin.models import CargoBase, TipoUnidade, Unidade
from services.domain.autorizacao import Acao as AcaoContrato

banco = pytest.mark.banco


def _acao_contrato(**overrides: object) -> AcaoContrato:
    dados: dict[str, object] = {
        "slug": "competencias.teste",
        "nome": "Ação de Teste",
        "tooltip": "Tooltip de teste",
        "estrutural": False,
    }
    dados.update(overrides)
    return AcaoContrato(**dados)  # type: ignore[arg-type]


def _acao_implementada(**overrides: object) -> AcaoImplementada:
    dados: dict[str, object] = {
        "acao": _acao_contrato(),
        "url_name": "competencias:teste",
        "partial": "competencias/_teste.html",
    }
    dados.update(overrides)
    return AcaoImplementada(**dados)  # type: ignore[arg-type]


def _registro(*implementadas: AcaoImplementada) -> RegistroAcoes:
    return RegistroAcoes(acoes=tuple(implementadas))


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Teste",
        "nivel": 10,
        "pode_ser_raiz": True,
        "nivel_minimo_titular": 1,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(**overrides: object) -> Unidade:
    dados: dict[str, object] = {
        "nome": "Unidade Teste",
        "sigla": "UT",
        "tipo": _tipo_unidade(),
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base(**overrides: object) -> CargoBase:
    dados: dict[str, object] = {"nome": "Cargo Teste", "sigla": "CT"}
    dados.update(overrides)
    return CargoBase.objects.create(**dados)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Projeção do registro e idempotência
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_sync_projeta_registro_e_e_idempotente() -> None:
    registro = _registro(_acao_implementada())

    primeira = sincronizar_acoes(registro)
    segunda = sincronizar_acoes(registro)

    assert primeira.criadas == 1
    assert segunda.criadas == 0
    assert segunda.desativadas == 0
    assert segunda.reativadas == 0
    assert AcaoModel.objects.count() == 1

    registro_alterado = _registro(
        _acao_implementada(acao=_acao_contrato(nome="Nome Novo", estrutural=True))
    )
    sincronizar_acoes(registro_alterado)

    projetada = AcaoModel.objects.get(slug="competencias.teste")
    assert projetada.nome == "Nome Novo"
    assert projetada.estrutural is True
    assert AcaoModel.objects.count() == 1


# ---------------------------------------------------------------------------
# Ação que sai e volta ao registro
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_sync_desativa_ausente_e_reativa_no_retorno() -> None:
    registro_com_acao = _registro(_acao_implementada())
    sincronizar_acoes(registro_com_acao)

    atribuicao = AtribuicaoUnidade.objects.create(
        unidade=_unidade(),
        acao=AcaoModel.objects.get(slug="competencias.teste"),
    )
    concessao = Concessao.objects.create(
        atribuicao=atribuicao, cargo_base=_cargo_base()
    )

    registro_vazio = _registro()
    contagem_saida = sincronizar_acoes(registro_vazio)

    projetada = AcaoModel.objects.get(slug="competencias.teste")
    assert projetada.ativa is False
    assert contagem_saida.desativadas == 1
    assert AtribuicaoUnidade.objects.filter(pk=atribuicao.pk).exists()
    assert Concessao.objects.filter(pk=concessao.pk).exists()

    contagem_retorno = sincronizar_acoes(registro_com_acao)

    projetada.refresh_from_db()
    assert projetada.ativa is True
    assert contagem_retorno.reativadas == 1
    assert AtribuicaoUnidade.objects.filter(pk=atribuicao.pk).exists()
    assert Concessao.objects.filter(pk=concessao.pk).exists()
