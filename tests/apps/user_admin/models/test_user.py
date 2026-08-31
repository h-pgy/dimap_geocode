"""
Testes de Perfil (SPEC user_admin/001): autenticação por RF e a obrigatoriedade de cargo base
e unidade, com o cargo em comissão como o único vínculo opcional. Inclui também nome/sobrenome
separados, foto opcional e a cor da unidade exposta via `cor_unidade` (SPEC user_admin/006), e o
exercício como leitura derivada de impedimento e exoneração (SPEC user_admin/015).

Os testes de persistência levam o marker `banco`: FK de cargo_base/unidade e a leitura de
impedimento só se verificam contra o Postgres real.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

import pytest

from apps.unidades.models import CorUnidade, TipoUnidade, Unidade
from apps.user_admin.models import (
    CargoBase,
    CargoComissao,
    Impedimento,
    Perfil,
    TipoImpedimento,
)

AUTH_USER_MODEL_ESPERADO = "user_admin.Perfil"

banco = pytest.mark.banco


def _perfil(**overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": "123456",
        "nome": "Fulano",
        "sobrenome": "de Tal",
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    # Sem senha, o próprio full_clean já acusaria "password" — ruído fora do que estes testes
    # verificam.
    perfil.set_password("segredo123")
    return perfil


def _perfil_completo(**overrides: object) -> Perfil:
    # cargo_base/unidade precisam de linha real: full_clean/create_user validam a FK contra o
    # banco. get_or_create porque alguns testes chamam este helper mais de uma vez.
    cargo_base, _ = CargoBase.objects.get_or_create(nome="Cargo Teste", sigla="CT")
    tipo_unidade, _ = TipoUnidade.objects.get_or_create(
        nome="Departamento",
        defaults={"nivel": 10, "pode_ser_raiz": True, "nivel_minimo_titular": 1},
    )
    unidade, _ = Unidade.objects.get_or_create(
        nome="Unidade Teste",
        defaults={"sigla": "UT", "tipo": tipo_unidade},
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
    return perfil


def test_perfil_autentica_por_rf() -> None:
    assert settings.AUTH_USER_MODEL == AUTH_USER_MODEL_ESPERADO
    assert get_user_model() is Perfil
    assert Perfil.USERNAME_FIELD == "rf"


def test_perfil_sem_cargo_base_ou_unidade_nao_valida() -> None:
    perfil = _perfil()

    with pytest.raises(ValidationError) as exc:
        perfil.full_clean(validate_unique=False, validate_constraints=False)

    assert "cargo_base" in exc.value.message_dict
    assert "unidade" in exc.value.message_dict


def test_perfil_sem_cargo_comissao_valida() -> None:
    perfil = _perfil()

    # cargo_base/unidade ficam de fora: validá-los exige linha real no banco (checagem de
    # existência da FK) e já são cobertos pelo teste acima — aqui o alvo é só a
    # opcionalidade do cargo_comissao.
    perfil.full_clean(
        exclude=["cargo_base", "unidade"],
        validate_unique=False,
        validate_constraints=False,
    )


@banco
@pytest.mark.django_db
def test_perfil_exige_sobrenome_e_admite_foto_nula() -> None:
    sem_foto = _perfil_completo()
    sem_foto.full_clean(validate_constraints=False)
    sem_foto.save()
    assert not sem_foto.foto

    sem_sobrenome = _perfil_completo(sobrenome="")
    with pytest.raises(ValidationError) as exc:
        sem_sobrenome.full_clean(validate_constraints=False)
    assert "sobrenome" in exc.value.message_dict


@banco
@pytest.mark.django_db
def test_create_user_guarda_nome_e_sobrenome_separados() -> None:
    cargo_base = CargoBase.objects.create(nome="Cargo Create User", sigla="CCU")
    tipo_unidade = TipoUnidade.objects.create(
        nome="Departamento Create User",
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )
    unidade = Unidade.objects.create(
        nome="Unidade Create User",
        sigla="UCU",
        tipo=tipo_unidade,
    )

    perfil = Perfil.objects.create_user(
        rf="654321",
        nome="Ciclana",
        sobrenome="da Silva",
        password="segredo123",
        cargo_base=cargo_base,
        unidade=unidade,
    )

    assert perfil.nome == "Ciclana"
    assert perfil.sobrenome == "da Silva"


@banco
@pytest.mark.django_db
def test_cor_unidade_reflete_a_cor_da_unidade_vinculada() -> None:
    perfil = _perfil_completo()
    perfil.unidade.cor = CorUnidade.SAKURA_600
    perfil.unidade.save()

    assert perfil.cor_unidade == CorUnidade.SAKURA_600


# ---------------------------------------------------------------------------
# Titularidade — unicidade do vínculo (SPEC user_admin/014)
# ---------------------------------------------------------------------------


def _tipo_unidade_titularizavel(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Titular Único",
        "nivel": 10,
        "pode_ser_raiz": True,
        "nivel_minimo_titular": 4,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_que_titulariza(**overrides: object) -> CargoComissao:
    dados: dict[str, object] = {
        "sigla": "CDA",
        "nivel": 4,
        "e_chefia": True,
        "nome": "Diretor de Divisão Titular Único",
    }
    dados.update(overrides)
    return CargoComissao.objects.create(**dados)  # type: ignore[arg-type]


@banco
@pytest.mark.django_db
def test_unidade_nao_admite_dois_titulares() -> None:
    tipo = _tipo_unidade_titularizavel()
    unidade = Unidade.objects.create(
        nome="Divisão Titular Único", sigla="DIVTU", tipo=tipo
    )
    cargo = _cargo_que_titulariza()
    cargo_base = CargoBase.objects.create(nome="Cargo Titular Único", sigla="CGTU")

    primeiro = Perfil(
        rf="700301",
        nome="Titular",
        sobrenome="Um",
        cargo_base=cargo_base,
        unidade=unidade,
        cargo_comissao=cargo,
        e_titular=True,
    )
    primeiro.set_password("segredo123")
    primeiro.save()

    segundo = Perfil(
        rf="700302",
        nome="Titular",
        sobrenome="Dois",
        cargo_base=cargo_base,
        unidade=unidade,
        cargo_comissao=cargo,
        e_titular=True,
    )
    segundo.set_password("segredo123")
    # save() direto, sem full_clean(): o que este teste fixa é o banco recusando, não a validação.
    with pytest.raises(IntegrityError):
        segundo.save()


# ---------------------------------------------------------------------------
# Exercício — leitura derivada de impedimento e exoneração (SPEC user_admin/015)
# ---------------------------------------------------------------------------


def _tipo_impedimento_exercicio(**overrides: object) -> TipoImpedimento:
    dados: dict[str, object] = {"nome": "Férias Exercício"}
    dados.update(overrides)
    return TipoImpedimento.objects.create(**dados)  # type: ignore[arg-type]


@banco
@pytest.mark.django_db
def test_exercicio_deriva_do_impedimento_e_da_exoneracao() -> None:
    hoje = timezone.localdate()
    perfil = _perfil_completo(rf="700401")
    perfil.save()

    # Sem impedimento e ativo: em exercício.
    assert perfil.em_exercicio is True
    assert perfil.exonerado is False

    # Com impedimento vigente: fora.
    vigente = Impedimento.objects.create(
        perfil=perfil,
        tipo=_tipo_impedimento_exercicio(),
        data_inicio=hoje - timedelta(days=1),
        data_fim=None,
    )
    assert perfil.em_exercicio is False

    # Vencido, volta sem que nada escreva — é o próprio dado passando, não uma rotina.
    vigente.data_fim = hoje - timedelta(days=1)
    vigente.save(update_fields=["data_fim"])
    assert perfil.em_exercicio is True

    # De início futuro: segue em exercício até a data chegar.
    Impedimento.objects.create(
        perfil=perfil,
        tipo=_tipo_impedimento_exercicio(nome="Férias Futuras Exercício"),
        data_inicio=hoje + timedelta(days=10),
        data_fim=hoje + timedelta(days=20),
    )
    assert perfil.em_exercicio is True

    # Inativo e sem impedimento: fora, pela outra causa. exonerado_em acompanha is_active — a
    # CheckConstraint da SPEC user_admin/027 recusa a discordância entre os dois.
    Impedimento.objects.filter(perfil=perfil).delete()
    perfil.is_active = False
    perfil.exonerado_em = hoje
    perfil.save(update_fields=["is_active", "exonerado_em"])
    assert perfil.em_exercicio is False
    assert perfil.exonerado is True


# ---------------------------------------------------------------------------
# exonerado_em é o mesmo fato que is_active, e a discordância é impossível (SPEC user_admin/027)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_banco_recusa_exoneracao_sem_data() -> None:
    inativo_sem_data = _perfil_completo(rf="700410")
    inativo_sem_data.save()
    inativo_sem_data.is_active = False

    # save() direto, sem full_clean(): o que este teste fixa é o banco recusando, não a validação.
    # `transaction.atomic()`: sem o savepoint, o erro esperado deixaria a transação do teste
    # abortada e a segunda checagem abaixo cairia num TransactionManagementError, não no que se
    # quer fixar.
    with transaction.atomic(), pytest.raises(IntegrityError):
        inativo_sem_data.save(update_fields=["is_active"])

    ativo_com_data = _perfil_completo(rf="700411")
    ativo_com_data.save()
    ativo_com_data.exonerado_em = timezone.localdate()

    with transaction.atomic(), pytest.raises(IntegrityError):
        ativo_com_data.save(update_fields=["exonerado_em"])
