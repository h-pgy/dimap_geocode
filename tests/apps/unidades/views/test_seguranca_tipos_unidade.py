"""
Bateria de segurança das quatro ações de tipo de unidade em apps/unidades/views.py (SPEC
user_admin/031, skill `acao-administrativa`): criar, editar, extinguir e reativar tipo de unidade
são exclusivas do administrador do sistema, sem alcance — o catálogo é global e não incide sobre
unidade.

Fora do teto de testes da SPEC (skill `acao-administrativa`, §6): fixam quem pode praticar o ato,
não o comportamento de cada operação — que está em test_edicao_tipo_unidade.py e em
tests/apps/unidades/test_extincao_tipo.py. Todos levam o marker `banco`.
"""

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

SLUGS = (
    "unidades.criar_tipo_unidade",
    "unidades.editar_tipo_unidade",
    "unidades.extinguir_tipo_unidade",
    "unidades.reativar_tipo_unidade",
)


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
    dados: dict[str, object] = {"nome": "Cargo Base Segurança Tipo", "sigla": "CGBST"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _perfil(unidade: Unidade, rf: str, nome: str = "Servidor", **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Segurança Tipo",
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
    perfil = _perfil(unidade, rf, nome, cargo_comissao=_cargo_chefia(f"Diretor {rf}"))
    definir_titular(perfil)
    return perfil


def _superusuario(rf: str, unidade: Unidade | None = None) -> Perfil:
    return Perfil.objects.create_superuser(
        rf=rf,
        nome="Super",
        sobrenome="Usuário",
        password="segredo123",
        unidade=unidade or _unidade(f"TIPO-SU-{rf}"),
        cargo_base=_cargo_base(),
    )


def _fresco(perfil: Perfil) -> Perfil:
    return Perfil.objects.get(pk=perfil.pk)


def _urls_dos_modais(tipo_pk: int) -> tuple[str, ...]:
    return (
        reverse("unidades:modal_criar_tipo_unidade"),
        f"{reverse('unidades:modal_editar_tipo_unidade')}?tipo={tipo_pk}",
        f"{reverse('unidades:modal_extinguir_tipo_unidade')}?tipo={tipo_pk}",
        f"{reverse('unidades:modal_reativar_tipo_unidade')}?tipo={tipo_pk}",
    )


def _urls_de_gravacao(tipo_pk: int) -> tuple[str, ...]:
    return (
        reverse("unidades:gravar_criacao_tipo_unidade"),
        reverse("unidades:gravar_edicao_tipo_unidade", kwargs={"tipo": tipo_pk}),
        _url_gravar_extincao(tipo_pk),
        _url_gravar_reativacao(tipo_pk),
    )


def _url_modal_extinguir() -> str:
    return reverse("unidades:modal_extinguir_tipo_unidade")


def _url_gravar_extincao(tipo_pk: int) -> str:
    return reverse("unidades:gravar_extincao_tipo_unidade", kwargs={"tipo": tipo_pk})


def _url_gravar_reativacao(tipo_pk: int) -> str:
    return reverse("unidades:gravar_reativacao_tipo_unidade", kwargs={"tipo": tipo_pk})


# ---------------------------------------------------------------------------
# Anônimo vai ao login, sem registrar
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_anonimo_vai_ao_login_sem_registrar(client: Client) -> None:
    tipo = _tipo_unidade("Tipo Anônimo")

    for url in _urls_dos_modais(tipo.pk):
        resposta = client.get(url)
        assert resposta.status_code == 302, url
        assert resposta["Location"].startswith(str(django_settings.LOGIN_URL))
    for url in _urls_de_gravacao(tipo.pk):
        resposta = client.post(url)
        assert resposta.status_code == 302, url
        assert resposta["Location"].startswith(str(django_settings.LOGIN_URL))

    assert ExecucaoAcao.objects.count() == 0
    tipo.refresh_from_db()
    assert tipo.extinto_em is None


# ---------------------------------------------------------------------------
# Autenticado sem competência: 403, e a negativa fica registrada
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_autenticado_sem_competencia_recebe_403_e_fica_registrado(client: Client) -> None:
    perfil = _perfil(_unidade("TIPO-403"), "9610600", nome="Sem Caneta")
    tipo = _tipo_unidade("Tipo 403")

    client.force_login(perfil)
    for url in _urls_dos_modais(tipo.pk):
        assert client.get(url).status_code == 403, url
    resposta = client.post(_url_gravar_extincao(tipo.pk))

    assert resposta.status_code == 403
    assert ExecucaoAcao.objects.filter(autorizado=False).count() == 5
    assert not ExecucaoAcao.objects.filter(autorizado=True).exists()
    tipo.refresh_from_db()
    assert tipo.extinto_em is None


# ---------------------------------------------------------------------------
# Nem concessão gravada nem direção de unidade liberam ação exclusiva do superusuário
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_concessao_gravada_nao_abre_acao_exclusiva_de_superusuario(client: Client) -> None:
    unidade = _unidade("TIPO-CONC")
    cargo_base = _cargo_base(nome="Cargo Concessão Tipos", sigla="CGCTP")
    concedido = _perfil(unidade, "9610700", nome="Concessão", cargo_base=cargo_base)
    for slug in SLUGS:
        acao, _ = Acao.objects.get_or_create(
            slug=slug,
            defaults={"nome": slug, "tooltip": "tt", "estrutural": False},
        )
        atribuicao = AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)
        Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo_base)
    tipo = _tipo_unidade("Tipo Concessão Alvo")

    client.force_login(_fresco(concedido))
    for slug in SLUGS:
        assert _fresco(concedido).has_perm(slug) is False, slug
    for url in _urls_dos_modais(tipo.pk):
        assert client.get(url).status_code == 403, url

    dirigente = _dirigente(unidade, "9610701", nome="Dirigente Tipos")
    client.force_login(_fresco(dirigente))
    for url in _urls_dos_modais(tipo.pk):
        assert client.get(url).status_code == 403, url


# ---------------------------------------------------------------------------
# O que fica registrado
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_ato_grava_quem_cargo_unidade_operacao_e_alvo(client: Client) -> None:
    unidade_autor = _unidade("TIPO-REG-AUTOR")
    outra = _unidade("TIPO-REG-OUTRA")
    superusuario = _superusuario("9610800", unidade_autor)
    tipo = _tipo_unidade("Tipo Registro")

    client.force_login(superusuario)
    resposta = client.post(_url_gravar_extincao(tipo.pk))
    assert resposta.status_code == 200

    execucao = ExecucaoAcao.objects.get(autorizado=True)
    assert execucao.perfil_id == superusuario.pk
    assert execucao.unidade_id == unidade_autor.pk
    assert execucao.cargo_base_id == superusuario.cargo_base_id
    assert execucao.operacao == "extinguir"
    assert execucao.alvo_tipo == "tipo_unidade"
    assert execucao.alvo_identificador == tipo.nome

    # Mudar a lotação depois não reescreve a linha.
    superusuario.unidade = outra
    superusuario.save(update_fields=["unidade"])
    execucao.refresh_from_db()
    assert execucao.unidade_id == unidade_autor.pk


@banco
@pytest.mark.django_db
def test_extinguir_e_reativar_ficam_distinguiveis_no_registro(client: Client) -> None:
    superusuario = _superusuario("9610900")
    tipo = _tipo_unidade("Tipo Distinguível")

    client.force_login(superusuario)
    client.post(_url_gravar_extincao(tipo.pk))
    client.post(_url_gravar_reativacao(tipo.pk))

    operacoes = set(ExecucaoAcao.objects.values_list("operacao", flat=True))
    assert operacoes == {"extinguir", "reativar"}


# ---------------------------------------------------------------------------
# Gravação só por POST
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_gravacao_so_por_post(client: Client) -> None:
    superusuario = _superusuario("9611000")
    tipo = _tipo_unidade("Tipo Só Post")

    client.force_login(superusuario)
    for url in _urls_de_gravacao(tipo.pk):
        assert client.get(url).status_code == 405, url

    assert ExecucaoAcao.objects.count() == 0
    tipo.refresh_from_db()
    assert tipo.extinto_em is None

    # Abrir o modal (GET) não pratica o ato: leitura autorizada não vira linha.
    resposta_modal = client.get(_url_modal_extinguir(), {"tipo": tipo.pk})
    assert resposta_modal.status_code == 200
    assert ExecucaoAcao.objects.count() == 0
