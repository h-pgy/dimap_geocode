"""
Testes de apps/user_admin/administrador.py (SPEC user_admin/022): o ato que escreve `is_superuser`
— torna um servidor administrador do sistema, e desfaz. A única regra do ato é a que garante ao menos um
administrador vivo: ninguém revoga a si mesmo.

Quem PODE praticar o ato é barreira da rota (SPEC autorizacao/004), fixada em
`tests/apps/user_admin/views/test_administrador.py`. Todos levam o marker `banco`: o ato lê e
grava `Perfil`.
"""

import pytest

from apps.competencias.consulta import alcance_do_perfil
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.administrador import ERRO_AUTO_REVOGACAO, mudar_administrador
from apps.user_admin.models import CargoBase, Perfil
from apps.user_admin.schemas import MudancaDeAdministrador

banco = pytest.mark.banco


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Ato Administrador",
        "nivel": 10,
        "pode_ser_raiz": True,
        "nivel_minimo_titular": 1,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(sigla: str, **overrides: object) -> Unidade:
    dados: dict[str, object] = {
        "nome": f"Unidade {sigla}",
        "sigla": sigla,
        "tipo": _tipo_unidade(nome=f"Tipo {sigla}"),
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base(**overrides: object) -> CargoBase:
    dados: dict[str, object] = {"nome": "Cargo Ato Administrador", "sigla": "CGAA"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Ato Administrador",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _mudanca(servidor: Perfil, autor: Perfil, tornar: bool) -> MudancaDeAdministrador:
    return MudancaDeAdministrador(servidor_id=servidor.pk, tornar=tornar, autor_id=autor.pk)


# ---------------------------------------------------------------------------
# Conceder e revogar escrevem is_superuser — e nada mais do cadastro
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_tornar_administrador_grava_is_superuser() -> None:
    autor = _perfil(_unidade("ATO-AUTOR"), "9601000", "Autor")
    alvo = _perfil(_unidade("ATO-ALVO"), "9601010", "Alvo")

    desfecho = mudar_administrador(_mudanca(alvo, autor, tornar=True))

    assert desfecho.recusa.mensagens == ()
    assert desfecho.perfil is not None
    assert desfecho.perfil.is_superuser is True
    assert desfecho.perfil.is_staff is False
    alvo.refresh_from_db()
    assert alvo.is_superuser is True
    assert alvo.is_staff is False


@banco
@pytest.mark.django_db
def test_revogar_administrador_tira_is_superuser() -> None:
    autor = _perfil(_unidade("ATO-REV-AUTOR"), "9601100", "Autor Revoga")
    alvo = _perfil(_unidade("ATO-REV-ALVO"), "9601110", "Alvo Revoga", is_superuser=True)

    desfecho = mudar_administrador(_mudanca(alvo, autor, tornar=False))

    assert desfecho.perfil is not None
    assert desfecho.perfil.is_superuser is False
    alvo.refresh_from_db()
    assert alvo.is_superuser is False


# ---------------------------------------------------------------------------
# Ninguém revoga a si mesmo — é o que mantém ao menos um administrador
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_nao_revoga_a_si_mesmo() -> None:
    unico = _perfil(_unidade("ATO-UNICO"), "9601200", "Único Admin", is_superuser=True)

    desfecho = mudar_administrador(_mudanca(unico, unico, tornar=False))

    assert desfecho.perfil is None
    assert desfecho.recusa.mensagens == (ERRO_AUTO_REVOGACAO,)
    assert desfecho.recusa.realce == {"administrador": "campo-realce-erro"}
    unico.refresh_from_db()
    assert unico.is_superuser is True


# ---------------------------------------------------------------------------
# O alcance vem junto: organograma inteiro, sem concessão gravada
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_administrador_alcanca_organograma_inteiro() -> None:
    autor = _perfil(_unidade("ATO-ALC-AUTOR"), "9601300", "Autor Alcance")
    alvo = _perfil(_unidade("ATO-ALC-ALVO"), "9601310", "Alvo Alcance")
    outro_ramo = _unidade("ATO-ALC-OUTRO-RAMO")

    desfecho = mudar_administrador(_mudanca(alvo, autor, tornar=True))

    assert desfecho.perfil is not None
    novo_admin = Perfil.objects.get(pk=alvo.pk)
    # Ação estrutural real, já registrada: nenhuma concessão foi gravada para ela.
    assert novo_admin.has_perm("user_admin.criar_servidor") is True
    assert outro_ramo.pk in alcance_do_perfil(novo_admin)
