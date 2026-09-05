"""
Testes de apps/cargos/views.py — `gravar_edicao_cargo` (SPEC user_admin/029): a trava de natureza
vive no servidor, não na tela. Nível, chefia e alta administração de cargo ocupado só são
recusados pelo caminho do ato; nome e sigla seguem editáveis mesmo em cargo ocupado ou extinto.

`ACAO_EDITAR_CARGO` é exclusiva do superusuário — o contrato de segurança da ação (anônimo, sem
competência, concessão gravada) está em test_seguranca_cargos.py, comum às quatro ações. Todos
levam o marker `banco`.
"""

from datetime import date

from django.test import Client
from django.urls import reverse

import pytest

from apps.cargos.extincao import extinguir_cargo
from apps.cargos.models import CargoBase, CargoComissao
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


def _cargo_base(**overrides: object) -> CargoBase:
    dados: dict[str, object] = {"nome": "Cargo Base Edição", "sigla": "CGBED"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _perfil(unidade: Unidade, rf: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": "Servidor",
        "sobrenome": "Edição",
        "cargo_base": _cargo_base(),
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
        unidade=unidade or _unidade(f"CARGO-ED-SU-{rf}"),
        cargo_base=_cargo_base(),
    )


def _cargo(nome: str, **overrides: object) -> CargoComissao:
    dados: dict[str, object] = {"sigla": "CDA", "nivel": 4, "e_chefia": True, "nome": nome}
    dados.update(overrides)
    return CargoComissao.objects.create(**dados)  # type: ignore[arg-type]


def _payload(nome: str, sigla: str, nivel: str, e_chefia: bool = True) -> dict[str, str]:
    payload = {"nome": nome, "sigla": sigla, "nivel": nivel}
    if e_chefia:
        payload["e_chefia"] = "on"
    return payload


def _url_gravar(cargo_pk: int) -> str:
    return reverse("cargos:gravar_edicao_cargo", kwargs={"cargo": cargo_pk})


# ---------------------------------------------------------------------------
# Natureza travada quando há ocupante
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_edicao_recusa_natureza_de_cargo_ocupado(client: Client) -> None:
    unidade = _unidade("CARGO-EDNAT")
    superusuario = _superusuario("9600100")
    cargo = _cargo("Cargo Edição Natureza", nivel=4, e_chefia=True)
    _perfil(unidade, "9600101", cargo_comissao=cargo)

    client.force_login(superusuario)
    resposta = client.post(_url_gravar(cargo.pk), _payload(cargo.nome, cargo.sigla, "2"))

    assert resposta.status_code == 422
    cargo.refresh_from_db()
    assert cargo.nivel == 4
    assert cargo.e_chefia is True


@banco
@pytest.mark.django_db
def test_edicao_altera_nome_e_sigla_de_cargo_ocupado_e_extinto(client: Client) -> None:
    unidade = _unidade("CARGO-EDNOME")
    superusuario = _superusuario("9600200")
    ocupado = _cargo("Cargo Nome Ocupado", sigla="CNO")
    _perfil(unidade, "9600201", cargo_comissao=ocupado)
    extinto = _cargo("Cargo Nome Extinto", sigla="CNE")
    extinguir_cargo(extinto, date(2026, 9, 4))

    client.force_login(superusuario)

    resposta_ocupado = client.post(
        _url_gravar(ocupado.pk), _payload("Cargo Renomeado Ocupado", "CRO", str(ocupado.nivel))
    )
    assert resposta_ocupado.status_code == 200
    ocupado.refresh_from_db()
    assert ocupado.nome == "Cargo Renomeado Ocupado"
    assert ocupado.sigla == "CRO"

    resposta_extinto = client.post(
        _url_gravar(extinto.pk), _payload("Cargo Renomeado Extinto", "CRE", str(extinto.nivel))
    )
    assert resposta_extinto.status_code == 200
    extinto.refresh_from_db()
    assert extinto.nome == "Cargo Renomeado Extinto"
    assert extinto.extinto_em is not None


@banco
@pytest.mark.django_db
def test_edicao_livre_quando_ninguem_ocupa(client: Client) -> None:
    superusuario = _superusuario("9600300")
    cargo = _cargo("Cargo Edição Livre", nivel=4, e_chefia=True)

    client.force_login(superusuario)
    resposta = client.post(_url_gravar(cargo.pk), _payload(cargo.nome, cargo.sigla, "2"))

    assert resposta.status_code == 200
    cargo.refresh_from_db()
    assert cargo.nivel == 2
