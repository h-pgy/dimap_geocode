"""Testes de apps/competencias/backends.py (SPEC autorizacao/003): o backend de autorização que
serve `has_perm` a partir da concessão gravada e de quem responde pela direção da unidade hoje —
sem multiplicar consultas entre perguntas do mesmo perfil, e sem liberar nada a anônimo ou
exonerado.
"""

from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

import pytest

from apps.competencias.backends import CompetenciaPermissionBackend
from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao
from apps.competencias.schemas import AcaoImplementada, RegistroAcoes
from apps.user_admin.exercicio import designar_substituto, registrar_impedimento
from apps.user_admin.models import (
    CargoBase,
    CargoComissao,
    Perfil,
    TipoImpedimento,
    TipoUnidade,
    Unidade,
)
from apps.user_admin.schemas import NovaSubstituicao, NovoImpedimento
from apps.user_admin.titularidade import definir_titular
from services.domain.autorizacao import Acao as AcaoDominio

banco = pytest.mark.banco


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Backend",
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


def _cargo_base(**overrides: object) -> CargoBase:
    dados: dict[str, object] = {"nome": "Cargo Backend", "sigla": "CGBK"}
    dados.update(overrides)
    return CargoBase.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_chefia(nome: str, nivel: int) -> CargoComissao:
    return CargoComissao.objects.create(nome=nome, sigla="CDA", nivel=nivel, e_chefia=True)


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Backend",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _fresco(perfil: Perfil) -> Perfil:
    # Recarrega do banco: o cache de `has_perm` é do objeto Python, e o teste precisa ver o
    # efeito de cada mudança de estado como um request novo veria.
    return Perfil.objects.get(pk=perfil.pk)


def _registro_com_estrutural(slug: str) -> RegistroAcoes:
    return RegistroAcoes(
        acoes=(
            AcaoImplementada(
                acao=AcaoDominio(slug=slug, nome="Estrutural Backend", tooltip="tt", estrutural=True),
                url_name="competencias:teste",
                partial="_teste.html",
            ),
        )
    )


# ---------------------------------------------------------------------------
# Custo fixo: N perguntas do mesmo perfil não multiplicam consulta
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_backend_responde_has_perm_sem_multiplicar_consultas() -> None:
    unidade = _unidade("UQUERY")
    cargo = _cargo_base()
    perfil = _perfil(unidade, "800810", "ContaQuery", cargo_base=cargo)

    atribuicao = AtribuicaoUnidade.objects.create(
        unidade=unidade,
        acao=Acao.objects.create(slug="competencias.liberada_query", nome="Liberada", tooltip="tt"),
    )
    Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo)
    Acao.objects.create(slug="competencias.negada_query", nome="Negada", tooltip="tt")

    fresco = _fresco(perfil)
    backend = CompetenciaPermissionBackend()

    with CaptureQueriesContext(connection) as primeira_pergunta:
        assert backend.has_perm(fresco, "competencias.liberada_query") is True
    assert len(primeira_pergunta.captured_queries) > 0

    with CaptureQueriesContext(connection) as perguntas_seguintes:
        assert backend.has_perm(fresco, "competencias.negada_query") is False
        assert backend.has_perm(fresco, "competencias.liberada_query") is True
    assert len(perguntas_seguintes.captured_queries) == 0


# ---------------------------------------------------------------------------
# Canetas montadas do banco: direção, afastamento e substituição em outra unidade
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_backend_monta_as_canetas_do_banco(monkeypatch: pytest.MonkeyPatch) -> None:
    slug_estrutural = "competencias.estrutural_canetas"
    monkeypatch.setattr(
        "apps.competencias.consulta.REGISTRO", _registro_com_estrutural(slug_estrutural)
    )
    Acao.objects.create(
        slug=slug_estrutural, nome="Estrutural Canetas", tooltip="tt", estrutural=True
    )
    tipo_impedimento = TipoImpedimento.objects.create(nome="Férias Backend Canetas")
    hoje = timezone.localdate()
    backend = CompetenciaPermissionBackend()

    unidade_a = _unidade("UACAN")
    cargo_titular_a = _cargo_chefia("Diretor Backend Canetas", nivel=1)
    titular_a = _perfil(unidade_a, "800800", "Titular", cargo_comissao=cargo_titular_a)
    definir_titular(titular_a)

    # Titular em exercício: a estrutural da própria unidade libera sem concessão gravada.
    assert backend.has_perm(_fresco(titular_a), slug_estrutural) is True

    unidade_b = _unidade("UBCAN")
    substituto = _perfil(unidade_b, "800801", "Substituto")
    impedimento = registrar_impedimento(
        titular_a,
        NovoImpedimento(
            tipo=tipo_impedimento.pk, data_inicio=hoje - timedelta(days=1), data_fim=None
        ),
    )

    # Afastado e sem substituto: ninguém responde pela direção, ninguém recebe a estrutural.
    assert backend.has_perm(_fresco(titular_a), slug_estrutural) is False

    designar_substituto(
        impedimento, NovaSubstituicao(substituto=substituto.pk, data_inicio=hoje, data_fim=None)
    )

    # O substituto — de OUTRA unidade — passa a dirigir a unidade do titular coberto.
    assert backend.has_perm(_fresco(substituto), slug_estrutural) is True

    # E também exerce o que está concedido ao cargo do substituído, na unidade do substituído.
    atribuicao = AtribuicaoUnidade.objects.create(
        unidade=unidade_a,
        acao=Acao.objects.create(
            slug="competencias.concedida_ao_substituido", nome="Concedida", tooltip="tt"
        ),
    )
    Concessao.objects.create(atribuicao=atribuicao, cargo_comissao=cargo_titular_a)
    assert backend.has_perm(_fresco(substituto), "competencias.concedida_ao_substituido") is True


# ---------------------------------------------------------------------------
# Anônimo, exonerado e o retorno de `authenticate`
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_backend_nega_anonimo_e_exonerado_e_nao_autentica() -> None:
    unidade = _unidade("UANON")
    cargo = _cargo_base()
    perfil = _perfil(unidade, "800820", "Exonerado", cargo_base=cargo, is_active=False)

    atribuicao = AtribuicaoUnidade.objects.create(
        unidade=unidade,
        acao=Acao.objects.create(slug="competencias.anon_teste", nome="Anon", tooltip="tt"),
    )
    Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo)

    backend = CompetenciaPermissionBackend()

    assert backend.has_perm(AnonymousUser(), "competencias.anon_teste") is False
    assert backend.has_perm(_fresco(perfil), "competencias.anon_teste") is False
    assert backend.authenticate(None) is None
