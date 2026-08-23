"""
Testes do superusuário criado pela linha de comando (SPEC criacao_usuarios/006): `createsuperuser`
preenche só RF, nome e sobrenome, e unidade e cargo base são obrigatórios — o que ele produz não
grava. O que este arquivo fixa é o caminho que produz um `Perfil` completo.

Marker `banco`: perfil, unidade, cargos e titularidade são tabelas.
"""

from django.core.management import call_command

import pytest

from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, CargoComissao, Perfil

banco = pytest.mark.banco

SENHA = "segredo-do-superusuario"
PROMPT_DE_SENHA = "apps.user_admin.management.commands.criar_superusuario.getpass"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _unidade() -> Unidade:
    """A DIMAP como o comando a encontra: pela sigla, com um tipo cujo porte o cargo em comissão
    do superusuário titulariza."""
    tipo = TipoUnidade.objects.create(
        nome="Divisão Superusuário",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=4,
    )
    return Unidade.objects.create(nome="Divisão de Mapeamento", sigla="DIMAP", tipo=tipo)


def _cargo_base() -> CargoBase:
    return CargoBase.objects.create(nome="Auditor Fiscal Tributário Municipal", sigla="AFTM")


def _cargo_comissao() -> CargoComissao:
    return CargoComissao.objects.create(
        nome="Diretor de Divisão",
        sigla="CDA",
        nivel=4,
        e_chefia=True,
    )


# ---------------------------------------------------------------------------
# O superusuário nasce servidor completo
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_superusuario_nasce_lotado_e_titular(monkeypatch: pytest.MonkeyPatch) -> None:
    unidade = _unidade()
    _cargo_base()
    _cargo_comissao()
    # A senha nunca vem por argumento: quem a pede é o comando, e o teste responde ao prompt.
    # Pelo caminho do módulo, e não por import: o comando é do runtime, não da coleta.
    monkeypatch.setattr(PROMPT_DE_SENHA, lambda *args, **kwargs: SENHA)

    call_command(
        "criar_superusuario",
        "--rf",
        "8123456",
        "--nome",
        "Henrique",
        "--sobrenome",
        "Pougy",
        "--email",
        "henrique@prefeitura.sp.gov.br",
        "--unidade",
        "DIMAP",
        "--cargo-base",
        "AFTM",
        "--cargo-comissao",
        "Diretor de Divisão",
        "--titular",
    )

    perfil = Perfil.objects.get(rf="8123456")
    assert perfil.is_superuser is True
    assert perfil.is_staff is True
    assert perfil.unidade_id == unidade.pk
    assert perfil.cargo_base.sigla == "AFTM"
    assert perfil.cargo_comissao is not None
    assert perfil.cargo_comissao.nome == "Diretor de Divisão"
    assert perfil.e_titular is True
    assert perfil.check_password(SENHA)
