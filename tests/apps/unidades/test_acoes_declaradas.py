"""
Testes de apps/unidades/acoes_declaradas.py (SPEC user_admin/020): os itens da bateria de
segurança que a SPEC pede sobre as DUAS ações estruturais de unidade ao mesmo tempo — anônimo nas
duas rotas de escrita, autenticado sem competência nas duas ações, e o alcance irrestrito do
superusuário sobre criar e editar unidade.

Os demais itens da bateria, específicos de cada ação, moram em test_criar_unidade.py,
test_editar_unidade.py (views/) e test_criar_unidade_raiz.py.

Todos levam o marker `banco`.
"""

from django.conf import settings as django_settings
from django.test import Client
from django.urls import reverse

import pytest

from apps.competencias.models import ExecucaoAcao
from apps.unidades.models import CorUnidade, TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, Perfil

banco = pytest.mark.banco


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Tipo Ações Declaradas",
        "nivel": 20,
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
    dados: dict[str, object] = {"nome": "Cargo Ações Declaradas", "sigla": "CGAD"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Ações Declaradas",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _superusuario(rf: str) -> Perfil:
    return Perfil.objects.create_superuser(
        rf=rf,
        nome="Super",
        sobrenome="Usuário",
        password="segredo123",
        unidade=_unidade(f"XA-SU-{rf}"),
        cargo_base=_cargo_base(),
    )


def _payload_criar(pai: Unidade, tipo: TipoUnidade, sigla: str) -> dict[str, str]:
    return {
        "pai": str(pai.pk),
        "nome": f"Unidade {sigla}",
        "sigla": sigla,
        "tipo": str(tipo.pk),
        "cor": str(CorUnidade.AGUA_700),
    }


def _payload_editar(
    pai: Unidade | None, tipo: TipoUnidade, nome: str, sigla: str
) -> dict[str, str]:
    return {
        "pai": str(pai.pk) if pai is not None else "",
        "nome": nome,
        "sigla": sigla,
        "tipo": str(tipo.pk),
        "cor": str(CorUnidade.AGUA_700),
    }


def _url_gravar_criar() -> str:
    return reverse("unidades:gravar_unidade")


def _url_abrir_editar(unidade_id: int) -> str:
    return reverse("unidades:editar_unidade", kwargs={"unidade": unidade_id})


def _url_gravar_editar(unidade_id: int) -> str:
    return reverse("unidades:gravar_edicao_unidade", kwargs={"unidade": unidade_id})


# ---------------------------------------------------------------------------
# Anônimo é mandado ao login, nas duas rotas de escrita, sem deixar linha
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_anonimo_vai_para_o_login_sem_deixar_linha(client: Client) -> None:
    pai = _unidade("XA-ANON-PAI")
    tipo_filho = _tipo_unidade(
        nome="Tipo Filho Anon Cruzado", nivel=10, pode_ser_raiz=False
    )
    alvo = _unidade("XA-ANON-ALVO")

    resposta_criar = client.post(
        _url_gravar_criar(), _payload_criar(pai, tipo_filho, "XA-ANON-FILHA")
    )
    assert resposta_criar.status_code == 302
    assert resposta_criar["Location"].startswith(str(django_settings.LOGIN_URL))

    resposta_editar = client.post(
        _url_gravar_editar(alvo.pk),
        _payload_editar(pai=None, tipo=alvo.tipo, nome=alvo.nome, sigla=alvo.sigla),
    )
    assert resposta_editar.status_code == 302
    assert resposta_editar["Location"].startswith(str(django_settings.LOGIN_URL))

    assert ExecucaoAcao.objects.count() == 0


# ---------------------------------------------------------------------------
# Autenticado sem competência recebe 403 registrado, nas duas ações
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_autenticado_sem_competencia_recebe_403_registrado(client: Client) -> None:
    unidade = _unidade("XA-403")
    perfil = _perfil(unidade, "9701000", "Sem Competência Cruzada")
    alvo = _unidade("XA-403-ALVO")

    client.force_login(perfil)
    assert client.get(reverse("unidades:criar_unidade")).status_code == 403
    assert client.get(_url_abrir_editar(alvo.pk)).status_code == 403

    assert ExecucaoAcao.objects.filter(autorizado=False).count() == 2


# ---------------------------------------------------------------------------
# O superusuário alcança o organograma inteiro, dirigindo unidade ou não
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_superusuario_alcanca_todo_o_organograma(client: Client) -> None:
    qualquer_ramo = _unidade("XA-SU-RAMO")
    tipo_filho = _tipo_unidade(
        nome="Tipo Filho Super Cruzado", nivel=10, pode_ser_raiz=False
    )
    alvo_edicao = _unidade("XA-SU-EDITADA")
    superusuario = _superusuario("9701100")

    client.force_login(superusuario)
    resposta_criar = client.post(
        _url_gravar_criar(), _payload_criar(qualquer_ramo, tipo_filho, "XA-SU-FILHA")
    )
    assert resposta_criar.status_code == 200
    assert Unidade.objects.filter(sigla="XA-SU-FILHA", pai=qualquer_ramo).exists()

    resposta_editar = client.post(
        _url_gravar_editar(alvo_edicao.pk),
        _payload_editar(
            pai=None,
            tipo=alvo_edicao.tipo,
            nome="Renomeada Pelo Super",
            sigla=alvo_edicao.sigla,
        ),
    )
    assert resposta_editar.status_code == 200
    alvo_edicao.refresh_from_db()
    assert alvo_edicao.nome == "Renomeada Pelo Super"

    assert (
        ExecucaoAcao.objects.filter(perfil=superusuario, autorizado=True).count() == 2
    )
