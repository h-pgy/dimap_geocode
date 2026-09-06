"""
Testes de apps/cargos/views.py — `gravar_edicao_cargo_base` (SPEC user_admin/030): a edição nunca
recusa nome nem sigla, ocupado ou extinto — cargo base não tem nível, natureza nem alta
administração, e não há nada a travar (diferente de `gravar_edicao_cargo`, SPEC user_admin/029).

`ACAO_EDITAR_CARGO_BASE` é exclusiva do superusuário — o contrato de segurança comum às quatro ações
está em test_seguranca_cargos_base.py. Todos levam o marker `banco`.
"""

from datetime import date

from django.test import Client
from django.urls import reverse

import pytest

from apps.cargos.extincao import extinguir_cargo_base
from apps.cargos.models import CargoBase
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil

banco = pytest.mark.banco


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(nome: str, **overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {"nome": nome, "nivel": 10, "pode_ser_raiz": True, "nivel_minimo_titular": 1}
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(sigla: str, **overrides: object) -> Unidade:
    dados: dict[str, object] = {"nome": f"Unidade {sigla}", "sigla": sigla, "tipo": _tipo_unidade(f"Tipo {sigla}")}
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base(nome: str, **overrides: object) -> CargoBase:
    dados: dict[str, object] = {"sigla": nome[:3].upper(), "nome": nome}
    dados.update(overrides)
    return CargoBase.objects.create(**dados)  # type: ignore[arg-type]


def _perfil(unidade: Unidade, rf: str, cargo_base: CargoBase, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": "Servidor",
        "sobrenome": "Edição Base",
        "cargo_base": cargo_base,
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _superusuario(rf: str, unidade: Unidade | None = None) -> Perfil:
    return Perfil.objects.create_superuser(
        rf=rf,
        nome="Super",
        sobrenome="Usuário",
        password="segredo123",
        unidade=unidade or _unidade(f"CB-ED-SU-{rf}"),
        cargo_base=_cargo_base(f"Cargo Base Super {rf}"),
    )


def _url_gravar(cargo_pk: int) -> str:
    return reverse("cargos:gravar_edicao_cargo_base", kwargs={"cargo": cargo_pk})


# ---------------------------------------------------------------------------
# Nome e sigla mudam sempre — ocupado ou extinto
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_edicao_altera_nome_e_sigla_de_cargo_base_ocupado_e_extinto(client: Client) -> None:
    unidade = _unidade("CARGOBASE-EDNOME")
    superusuario = _superusuario("9610300")
    ocupado = _cargo_base("Cargo Base Nome Ocupado", sigla="CBNO")
    _perfil(unidade, "9610301", ocupado)
    extinto = _cargo_base("Cargo Base Nome Extinto", sigla="CBNE")
    extinguir_cargo_base(extinto, date(2026, 9, 4))

    client.force_login(superusuario)

    resposta_ocupado = client.post(
        _url_gravar(ocupado.pk), {"nome": "Cargo Base Renomeado Ocupado", "sigla": "CBRO"}
    )
    assert resposta_ocupado.status_code == 200
    ocupado.refresh_from_db()
    assert ocupado.nome == "Cargo Base Renomeado Ocupado"
    assert ocupado.sigla == "CBRO"

    resposta_extinto = client.post(
        _url_gravar(extinto.pk), {"nome": "Cargo Base Renomeado Extinto", "sigla": "CBRE"}
    )
    assert resposta_extinto.status_code == 200
    extinto.refresh_from_db()
    assert extinto.nome == "Cargo Base Renomeado Extinto"
    assert extinto.extinto_em is not None
