"""
Testes de apps/user_admin/exoneracao.py (SPEC user_admin/027): o ato que tira um servidor do quadro
da DIMAP — e o que o reintegra. A exoneração larga, numa transação só, a titularidade, os
impedimentos em aberto, as coberturas das duas pontas, as delegações recebidas e a condição de
administrador; a reintegração devolve só o acesso.

Quem PODE praticar o ato é barreira da rota (SPEC autorizacao/004), fixada em
tests/apps/user_admin/views/test_exoneracao.py. Todos levam o marker `banco`: o ato lê e grava
Perfil, Impedimento, Substituicao e Delegacao.
"""

from datetime import timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone

import pytest

from apps.cargos.models import CargoBase, CargoComissao
from apps.competencias.models import Acao, Delegacao
from apps.unidades.models import TipoUnidade, Unidade
from apps.unidades.titularidade import definir_titular
from apps.user_admin.exercicio import designar_substituto, registrar_impedimento
from apps.user_admin.exoneracao import exonerar_servidor, reintegrar_servidor
from apps.user_admin.models import (
    Impedimento,
    Perfil,
    Substituicao,
    TipoImpedimento,
)
from apps.user_admin.schemas import ComandoExoneracao
from apps.user_admin.schemas import NovaSubstituicao, NovoImpedimento
from services.domain.exoneracao import MOTIVO_AUTO_EXONERACAO

banco = pytest.mark.banco

DIA = timedelta(days=1)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Exoneração",
        "nivel": 10,
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
    dados: dict[str, object] = {"nome": "Cargo Exoneração", "sigla": "CGEO"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _cargo_chefia(nome: str) -> CargoComissao:
    return CargoComissao.objects.create(nome=nome, sigla="CDA", nivel=1, e_chefia=True)


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Exoneração",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _dirigente(unidade: Unidade, rf: str, nome: str = "Dirigente") -> Perfil:
    perfil = _perfil(unidade, rf, nome, cargo_comissao=_cargo_chefia(f"Diretor {rf}"))
    definir_titular(perfil)
    return perfil


def _tipo_impedimento(nome: str) -> TipoImpedimento:
    tipo, _ = TipoImpedimento.objects.get_or_create(nome=nome)
    return tipo


def _fresco(perfil: Perfil) -> Perfil:
    return Perfil.objects.get(pk=perfil.pk)


def _comando(servidor: Perfil, autor: Perfil) -> ComandoExoneracao:
    return ComandoExoneracao(servidor_id=servidor.pk, autor_id=autor.pk)


# ---------------------------------------------------------------------------
# A exoneração larga tudo o que prende a pessoa ao quadro, numa transação só
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_exoneracao_larga_tudo_num_ato_so() -> None:
    unidade = _unidade("EXO-TUDO")
    outra_unidade = _unidade("EXO-TUDO-OUTRA")
    alvo = _dirigente(unidade, "9800000", "Alvo Tudo")
    alvo.is_superuser = True
    alvo.save(update_fields=["is_superuser"])
    outro_titular = _dirigente(outra_unidade, "9800001", "Outro Titular")
    hoje = timezone.localdate()
    tipo = _tipo_impedimento("Licença Exoneração Tudo")

    # A ponta que ele DÁ: cobrindo o impedimento de outro titular — ANTES do próprio impedimento
    # dele, porque um substituto precisa estar livre no período designado (SPEC 015): o histórico
    # real é alvo cobrir outro_titular primeiro e só depois entrar de licença ele mesmo.
    impedimento_alheio = registrar_impedimento(
        outro_titular,
        NovoImpedimento(tipo=tipo.pk, data_inicio=hoje - DIA, data_fim=None),
    )
    designar_substituto(
        impedimento_alheio,
        NovaSubstituicao(substituto=alvo.pk, data_inicio=hoje - DIA, data_fim=None),
    )

    # A ponta que ele RECEBE: impedimento em aberto, coberto por um substituto.
    substituto_recebido = _perfil(unidade, "9800002", "Substituto Recebido")
    impedimento_proprio = registrar_impedimento(
        alvo, NovoImpedimento(tipo=tipo.pk, data_inicio=hoje - DIA, data_fim=None)
    )
    designar_substituto(
        impedimento_proprio,
        NovaSubstituicao(
            substituto=substituto_recebido.pk, data_inicio=hoje - DIA, data_fim=None
        ),
    )

    # Uma delegação recebida.
    acao = Acao.objects.get_or_create(
        slug="unidades.editar_unidade",
        defaults={"nome": "Editar unidade", "tooltip": "tt"},
    )[0]
    delegacao = Delegacao.objects.create(
        acao=acao,
        unidade=unidade,
        delegante=outro_titular,
        delegado=alvo,
        data_inicio=hoje - DIA,
        data_fim=None,
    )

    desfecho = exonerar_servidor(_comando(alvo, outro_titular), hoje)

    assert desfecho.perfil is not None
    alvo.refresh_from_db()
    assert alvo.e_titular is False
    assert alvo.is_superuser is False
    assert alvo.is_staff is False
    assert alvo.is_active is False
    assert alvo.exonerado_em == hoje

    impedimento_proprio.refresh_from_db()
    assert impedimento_proprio.data_fim == hoje
    assert Substituicao.objects.get(impedimento=impedimento_proprio).data_fim == hoje

    cobertura_dada = Substituicao.objects.get(
        impedimento=impedimento_alheio, substituto=alvo
    )
    assert cobertura_dada.data_fim == hoje

    delegacao.refresh_from_db()
    assert delegacao.data_fim == hoje


# ---------------------------------------------------------------------------
# A vaga aberta aceita a designação do próximo no mesmo instante
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_titularidade_largada_libera_a_designacao_do_proximo() -> None:
    unidade = _unidade("EXO-VAGA")
    autor = _perfil(unidade, "9800100", "Autor Vaga")
    titular = _dirigente(unidade, "9800101", "Titular Vaga")
    proximo = _perfil(
        unidade, "9800102", "Próximo Vaga", cargo_comissao=_cargo_chefia("Diretor Vaga")
    )

    exonerar_servidor(_comando(titular, autor), timezone.localdate())
    definir_titular(proximo)

    proximo.refresh_from_db()
    assert proximo.e_titular is True
    assert Perfil.objects.filter(unidade=unidade, e_titular=True).count() == 1


# ---------------------------------------------------------------------------
# O que não vigorou é apagado; o vigente termina no dia da exoneração
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_impedimento_futuro_e_apagado_e_o_vigente_e_encerrado_hoje() -> None:
    unidade = _unidade("EXO-IMPED")
    autor = _perfil(unidade, "9800200", "Autor Imped")
    # Cargo em comissão: é quem tem chefia que a substituição cobre (SPEC 015) — sem ele o
    # avaliador recusaria a designação abaixo, e a substituição nunca chegaria a existir.
    alvo = _perfil(
        unidade, "9800201", "Alvo Imped", cargo_comissao=_cargo_chefia("Diretor Imped")
    )
    tipo = _tipo_impedimento("Licença Exo Imped")
    hoje = timezone.localdate()

    vigente = registrar_impedimento(
        alvo, NovoImpedimento(tipo=tipo.pk, data_inicio=hoje - 5 * DIA, data_fim=None)
    )
    substituto = _perfil(unidade, "9800202", "Substituto Imped")
    designar_substituto(
        vigente,
        NovaSubstituicao(
            substituto=substituto.pk, data_inicio=hoje - 5 * DIA, data_fim=None
        ),
    )
    futuro = registrar_impedimento(
        alvo, NovoImpedimento(tipo=tipo.pk, data_inicio=hoje + 10 * DIA, data_fim=None)
    )

    exonerar_servidor(_comando(alvo, autor), hoje)

    vigente.refresh_from_db()
    assert vigente.data_fim == hoje
    assert Substituicao.objects.get(impedimento=vigente).data_fim == hoje
    assert not Impedimento.objects.filter(pk=futuro.pk).exists()


# ---------------------------------------------------------------------------
# Quem saiu do quadro deixa de entrar: a sessão aberta não resolve no request seguinte
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_exonerado_nao_autentica(client: Client) -> None:
    unidade = _unidade("EXO-SESSAO")
    autor = _perfil(unidade, "9800300", "Autor Sessão")
    alvo = _perfil(unidade, "9800301", "Alvo Sessão")

    client.force_login(alvo)
    assert client.get(reverse("painel:painel")).status_code == 200

    exonerar_servidor(_comando(alvo, autor), timezone.localdate())

    resposta = client.get(reverse("painel:painel"))
    assert resposta.status_code == 302
    assert resposta.url.startswith(reverse("autenticacao:login"))


# ---------------------------------------------------------------------------
# O ato é recusado por inteiro, sem gravar nada
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_recusa_nao_grava_nada() -> None:
    unidade = _unidade("EXO-RECUSA")
    titular = _dirigente(unidade, "9800500", "Titular Recusa")
    titular.is_superuser = True
    titular.save(update_fields=["is_superuser"])
    hoje = timezone.localdate()
    impedimento = registrar_impedimento(
        titular,
        NovoImpedimento(
            tipo=_tipo_impedimento("Licença Recusa").pk,
            data_inicio=hoje - DIA,
            data_fim=None,
        ),
    )

    desfecho = exonerar_servidor(_comando(titular, titular), hoje)

    assert desfecho.perfil is None
    assert desfecho.recusa.mensagens == (MOTIVO_AUTO_EXONERACAO,)
    titular.refresh_from_db()
    assert titular.e_titular is True
    assert titular.is_superuser is True
    assert titular.is_active is True
    impedimento.refresh_from_db()
    assert impedimento.data_fim is None


# ---------------------------------------------------------------------------
# A reintegração devolve o acesso e nada mais
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_reintegracao_devolve_so_o_acesso() -> None:
    unidade = _unidade("EXO-REINTEGRA")
    autor = _perfil(unidade, "9800600", "Autor Reintegra")
    titular = _dirigente(unidade, "9800601", "Titular Reintegra")
    titular.is_superuser = True
    titular.save(update_fields=["is_superuser"])

    exonerar_servidor(_comando(titular, autor), timezone.localdate())
    desfecho = reintegrar_servidor(_comando(titular, autor))

    assert desfecho.perfil is not None
    titular.refresh_from_db()
    assert titular.is_active is True
    assert titular.exonerado_em is None
    assert titular.e_titular is False
    assert titular.is_superuser is False
