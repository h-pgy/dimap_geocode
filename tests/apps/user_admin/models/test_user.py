"""
Testes de Perfil (SPEC user_admin/001): autenticação por RF e a obrigatoriedade de cargo base
e unidade, com o cargo em comissão como o único vínculo opcional.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

import pytest

from apps.user_admin.models import Perfil

AUTH_USER_MODEL_ESPERADO = "user_admin.Perfil"


def _perfil(**overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": "123456",
        "nome": "Fulano de Tal",
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    # Sem senha, o próprio full_clean já acusaria "password" — ruído fora do que estes testes
    # verificam.
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
