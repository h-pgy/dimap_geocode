"""
Testes de TipoImpedimento e Impedimento (SPEC user_admin/002): vigência do impedimento sobre
`Perfil.esta_impedido`, a constraint de fim não anterior ao início, a convivência de períodos
sobrepostos e as regras de sigla do tipo.

Os seis primeiros tocam o banco (UniqueConstraint e CheckConstraint só se verificam contra o
Postgres real) e levam o marker `banco`. Só `test_nome_exibicao_prefere_a_sigla` é propriedade
pura, sem precisar de linha persistida.
"""

from datetime import timedelta

from django.db import IntegrityError
from django.utils import timezone

import pytest

from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, Impedimento, Perfil, TipoImpedimento

banco = pytest.mark.banco


def _perfil(**overrides: object) -> Perfil:
    cargo_base = CargoBase.objects.create(nome="Cargo Teste", sigla="CT")
    tipo_unidade = TipoUnidade.objects.create(
        nome="Departamento",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )
    unidade = Unidade.objects.create(
        nome="Unidade Teste",
        sigla="UT",
        tipo=tipo_unidade,
    )
    dados: dict[str, object] = {
        "rf": "123456",
        "nome": "Fulano",
        "sobrenome": "de Tal",
        "cargo_base": cargo_base,
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _tipo(**overrides: object) -> TipoImpedimento:
    dados: dict[str, object] = {"nome": "Férias"}
    dados.update(overrides)
    return TipoImpedimento.objects.create(**dados)  # type: ignore[arg-type]


@banco
@pytest.mark.django_db
def test_perfil_com_impedimento_vigente_esta_impedido() -> None:
    perfil = _perfil()
    hoje = timezone.localdate()
    Impedimento.objects.create(
        perfil=perfil,
        tipo=_tipo(),
        data_inicio=hoje,
        data_fim=hoje,
    )

    assert perfil.esta_impedido is True


@banco
@pytest.mark.django_db
def test_perfil_com_impedimento_de_fim_aberto_esta_impedido() -> None:
    perfil = _perfil()
    hoje = timezone.localdate()
    Impedimento.objects.create(
        perfil=perfil,
        tipo=_tipo(nome="Licença", sigla="LIC"),
        data_inicio=hoje - timedelta(days=10),
        data_fim=None,
    )

    assert perfil.esta_impedido is True


@banco
@pytest.mark.django_db
def test_perfil_com_impedimento_fora_de_vigencia_nao_esta_impedido() -> None:
    perfil = _perfil()
    hoje = timezone.localdate()
    Impedimento.objects.create(
        perfil=perfil,
        tipo=_tipo(nome="Férias encerradas"),
        data_inicio=hoje - timedelta(days=30),
        data_fim=hoje - timedelta(days=1),
    )
    Impedimento.objects.create(
        perfil=perfil,
        tipo=_tipo(nome="Férias futuras"),
        data_inicio=hoje + timedelta(days=1),
        data_fim=hoje + timedelta(days=10),
    )

    assert perfil.esta_impedido is False


@banco
@pytest.mark.django_db
def test_impedimento_com_fim_anterior_ao_inicio_nao_valida() -> None:
    perfil = _perfil()
    hoje = timezone.localdate()

    with pytest.raises(IntegrityError):
        Impedimento.objects.create(
            perfil=perfil,
            tipo=_tipo(),
            data_inicio=hoje,
            data_fim=hoje - timedelta(days=1),
        )


@banco
@pytest.mark.django_db
def test_impedimentos_sobrepostos_coexistem() -> None:
    perfil = _perfil()
    hoje = timezone.localdate()
    Impedimento.objects.create(
        perfil=perfil,
        tipo=_tipo(nome="Férias"),
        data_inicio=hoje - timedelta(days=5),
        data_fim=hoje + timedelta(days=5),
    )
    Impedimento.objects.create(
        perfil=perfil,
        tipo=_tipo(nome="Licença médica", sigla="LM"),
        data_inicio=hoje - timedelta(days=2),
        data_fim=hoje + timedelta(days=2),
    )

    assert perfil.impedimentos.count() == 2
    assert perfil.esta_impedido is True


@banco
@pytest.mark.django_db
def test_tipos_sem_sigla_convivem() -> None:
    _tipo(nome="Férias")
    _tipo(nome="Licença sem sigla cadastrada")
    _tipo(nome="Outra licença", sigla="LTIP")

    with pytest.raises(IntegrityError):
        _tipo(nome="Licença para Tratar de Interesses Particulares", sigla="LTIP")


def test_nome_exibicao_prefere_a_sigla() -> None:
    com_sigla = TipoImpedimento(nome="Licença para Tratar de Interesses Particulares", sigla="LTIP")
    assert com_sigla.nome_exibicao == "LTIP"

    sem_sigla = TipoImpedimento(nome="Férias")
    assert sem_sigla.nome_exibicao == "Férias"
