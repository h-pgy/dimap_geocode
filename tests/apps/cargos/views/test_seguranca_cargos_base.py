"""
Bateria de segurança das quatro ações de apps/cargos/views.py sobre o catálogo de cargo base (SPEC
user_admin/030, skill `acao-administrativa`): criar, editar, extinguir e reativar são exclusivas do
administrador do sistema, sem alcance — mesmo regime das quatro sobre cargo em comissão
(test_seguranca_cargos.py, SPEC user_admin/029).

Fora do teto de testes da SPEC (skill `acao-administrativa`, §6): fixam quem pode praticar o ato,
não o comportamento de cada operação — que está em test_edicao_cargo_base.py e em
test_extincao_base.py. Todos levam o marker `banco`.
"""

from itertools import count

from django.conf import settings as django_settings
from django.test import Client
from django.urls import reverse

import pytest

from apps.cargos.models import CargoBase, CargoComissao
from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao, ExecucaoAcao
from apps.unidades.models import TipoUnidade, Unidade
from apps.unidades.titularidade import definir_titular
from apps.user_admin.models import Perfil

banco = pytest.mark.banco

SLUG_EXTINGUIR = "cargos.extinguir_cargo_base"
# CargoBase.sigla é única: um contador garante sigla nova a cada cargo, mesmo entre nomes que
# comecem iguais ("Cargo Base ...").
_SIGLAS = count(1)


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


def _cargo_base(nome: str = "Cargo Base Segurança", **overrides: object) -> CargoBase:
    defaults: dict[str, object] = {"sigla": f"CB{next(_SIGLAS)}"}
    defaults.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(nome=nome, defaults=defaults)  # type: ignore[arg-type]
    return cargo


def _perfil(unidade: Unidade, rf: str, nome: str = "Servidor", **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Segurança Base",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _cargo_chefia(nome: str) -> CargoComissao:
    return CargoComissao.objects.create(nome=nome, sigla="CDA", nivel=1, e_chefia=True)


def _dirigente(unidade: Unidade, rf: str, nome: str = "Dirigente") -> Perfil:
    perfil = _perfil(unidade, rf, nome, cargo_comissao=_cargo_chefia(f"Diretor Base {rf}"))
    definir_titular(perfil)
    return perfil


def _superusuario(rf: str, unidade: Unidade | None = None) -> Perfil:
    return Perfil.objects.create_superuser(
        rf=rf,
        nome="Super",
        sobrenome="Usuário",
        password="segredo123",
        unidade=unidade or _unidade(f"CARGOBASE-SU-{rf}"),
        cargo_base=_cargo_base(f"Cargo Base Super {rf}"),
    )


def _fresco(perfil: Perfil) -> Perfil:
    return Perfil.objects.get(pk=perfil.pk)


def _url_modal_criar() -> str:
    return reverse("cargos:modal_criar_cargo_base")


def _url_modal_editar() -> str:
    return reverse("cargos:modal_editar_cargo_base")


def _url_modal_extinguir() -> str:
    return reverse("cargos:modal_extinguir_cargo_base")


def _url_modal_reativar() -> str:
    return reverse("cargos:modal_reativar_cargo_base")


def _url_gravar_extincao(cargo_pk: int) -> str:
    return reverse("cargos:gravar_extincao_cargo_base", kwargs={"cargo": cargo_pk})


def _url_gravar_reativacao(cargo_pk: int) -> str:
    return reverse("cargos:gravar_reativacao_cargo_base", kwargs={"cargo": cargo_pk})


# ---------------------------------------------------------------------------
# Anônimo vai ao login, sem registrar
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_anonimo_vai_ao_login_sem_registrar(client: Client) -> None:
    cargo = _cargo_base("Cargo Base Anônimo")

    urls = (
        _url_modal_criar(),
        f"{_url_modal_editar()}?cargo={cargo.pk}",
        f"{_url_modal_extinguir()}?cargo={cargo.pk}",
        f"{_url_modal_reativar()}?cargo={cargo.pk}",
    )
    for url in urls:
        resposta = client.get(url)
        assert resposta.status_code == 302
        assert resposta["Location"].startswith(str(django_settings.LOGIN_URL))

    assert ExecucaoAcao.objects.count() == 0


# ---------------------------------------------------------------------------
# Autenticado sem competência: 403, e a negativa fica registrada
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_autenticado_sem_competencia_recebe_403_e_fica_registrado(client: Client) -> None:
    perfil = _perfil(_unidade("CARGOBASE-403"), "9610600", nome="Sem Caneta")
    cargo = _cargo_base("Cargo Base 403")

    client.force_login(perfil)
    resposta = client.get(_url_modal_extinguir(), {"cargo": cargo.pk})

    assert resposta.status_code == 403
    execucao = ExecucaoAcao.objects.get()
    assert execucao.autorizado is False


# ---------------------------------------------------------------------------
# Nem concessão gravada nem direção de unidade liberam ação exclusiva do superusuário
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_concessao_gravada_nao_abre_acao_exclusiva_de_superusuario(client: Client) -> None:
    unidade = _unidade("CARGOBASE-CONC")
    cargo_base_concedido = _cargo_base(nome="Cargo Base Concessão Cargos", sigla="CBCC")
    concedido = _perfil(unidade, "9610700", nome="Concessão", cargo_base=cargo_base_concedido)
    acao, _ = Acao.objects.get_or_create(
        slug=SLUG_EXTINGUIR,
        defaults={"nome": "Extinguir cargo base", "tooltip": "tt", "estrutural": False},
    )
    atribuicao = AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)
    Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo_base_concedido)
    cargo = _cargo_base("Cargo Base Concessão Alvo")

    client.force_login(_fresco(concedido))
    assert _fresco(concedido).has_perm(SLUG_EXTINGUIR) is False
    resposta_concessao = client.get(_url_modal_extinguir(), {"cargo": cargo.pk})
    assert resposta_concessao.status_code == 403

    dirigente = _dirigente(unidade, "9610701", nome="Dirigente Cargos Base")
    client.force_login(_fresco(dirigente))
    resposta_dirigente = client.get(_url_modal_extinguir(), {"cargo": cargo.pk})
    assert resposta_dirigente.status_code == 403


# ---------------------------------------------------------------------------
# O que fica registrado
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_ato_grava_quem_cargo_unidade_operacao_e_alvo(client: Client) -> None:
    unidade_autor = _unidade("CARGOBASE-REG-AUTOR")
    outra = _unidade("CARGOBASE-REG-OUTRA")
    superusuario = _superusuario("9610800", unidade_autor)
    cargo = _cargo_base("Cargo Base Registro")

    client.force_login(superusuario)
    resposta = client.post(_url_gravar_extincao(cargo.pk))
    assert resposta.status_code == 200

    execucao = ExecucaoAcao.objects.get(autorizado=True)
    assert execucao.perfil_id == superusuario.pk
    assert execucao.unidade_id == unidade_autor.pk
    assert execucao.cargo_base_id == superusuario.cargo_base_id
    assert execucao.operacao == "extinguir"
    assert execucao.alvo_tipo == "cargo_base"
    assert execucao.alvo_identificador == cargo.nome

    # Mudar a lotação depois não reescreve a linha.
    superusuario.unidade = outra
    superusuario.save(update_fields=["unidade"])
    execucao.refresh_from_db()
    assert execucao.unidade_id == unidade_autor.pk


@banco
@pytest.mark.django_db
def test_extinguir_e_reativar_ficam_distinguiveis_no_registro(client: Client) -> None:
    superusuario = _superusuario("9610900")
    cargo = _cargo_base("Cargo Base Distinguível")

    client.force_login(superusuario)
    client.post(_url_gravar_extincao(cargo.pk))
    client.post(_url_gravar_reativacao(cargo.pk))

    operacoes = set(ExecucaoAcao.objects.values_list("operacao", flat=True))
    assert operacoes == {"extinguir", "reativar"}


# ---------------------------------------------------------------------------
# Gravação só por POST
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_gravacao_so_por_post(client: Client) -> None:
    superusuario = _superusuario("9611000")
    cargo = _cargo_base("Cargo Base Só Post")

    client.force_login(superusuario)
    resposta = client.get(_url_gravar_extincao(cargo.pk))

    assert resposta.status_code == 405
    assert ExecucaoAcao.objects.count() == 0
    cargo.refresh_from_db()
    assert cargo.extinto_em is None

    # Abrir o modal (GET) não pratica o ato: leitura autorizada não vira linha.
    resposta_modal = client.get(_url_modal_extinguir(), {"cargo": cargo.pk})
    assert resposta_modal.status_code == 200
    assert ExecucaoAcao.objects.count() == 0
