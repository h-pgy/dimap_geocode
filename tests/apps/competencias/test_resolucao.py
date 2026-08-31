"""Testes de apps/competencias/resolucao.py (SPEC autorizacao/005): a borda entre o request e o
router — resolve o conjunto de slugs liberados ao perfil, com o atalho do superusuário que o
`PermissionsMixin.get_all_permissions` não cobre (só `has_perm` enumera tudo para ele).
"""

from django.contrib.auth.models import AnonymousUser

import pytest

from apps.competencias.resolucao import slugs_liberados
from apps.competencias.schemas import RegistroAcoes
from apps.competencias.utils import instanciar_acao
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, Perfil

banco = pytest.mark.banco


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Resolução",
        "nivel": 10,
        "pode_ser_raiz": True,
        "nivel_minimo_titular": 1,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(sigla: str, **overrides: object) -> Unidade:
    dados: dict[str, object] = {
        "nome": f"Divisão {sigla}",
        "sigla": sigla,
        "tipo": _tipo_unidade(nome=f"Tipo {sigla}"),
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Resolução",
        "cargo_base": CargoBase.objects.create(nome="Cargo Resolução", sigla="CGRS"),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _registro(*slugs: str) -> RegistroAcoes:
    return RegistroAcoes(
        acoes=tuple(
            instanciar_acao(
                slug=slug,
                nome=slug,
                tooltip="tt",
                url_name="core:home",
            )
            for slug in slugs
        )
    )


# ---------------------------------------------------------------------------
# Superusuário recebe o registro inteiro; anônimo, nada
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_resolvedor_libera_o_catalogo_inteiro_para_superusuario(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "apps.competencias.resolucao.REGISTRO",
        _registro("menus.acao_um", "menus.acao_dois"),
    )
    superusuario = _perfil(_unidade("URESO"), "900900", "Super", is_superuser=True)

    assert slugs_liberados(superusuario) == frozenset(
        {"menus.acao_um", "menus.acao_dois"}
    )
    assert slugs_liberados(AnonymousUser()) == frozenset()
