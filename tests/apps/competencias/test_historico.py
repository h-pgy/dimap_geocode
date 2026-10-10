"""Testes de apps/competencias/historico.py (SPEC documentos_oficiais/009):
leitura do rastro para atos próprios do requerente (`atos_proprios`).
"""

from datetime import date, datetime, time
from itertools import count

from django.utils import timezone
import pytest

from apps.cargos.models import CargoBase, CargoComissao
from apps.competencias.models import Acao, ExecucaoAcao
from apps.unidades.models import TipoUnidade, Unidade
from apps.unidades.titularidade import definir_titular
from apps.user_admin.models import Perfil

banco = pytest.mark.banco
_SIGLAS = count(100)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(nome: str, **overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": nome,
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
        "tipo": _tipo_unidade(f"Tipo {sigla}"),
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base(nome: str = "Cargo Base Teste", **overrides: object) -> CargoBase:
    numero = next(_SIGLAS)
    dados: dict[str, object] = {"nome": f"{nome} {numero}", "sigla": f"CB{numero}"}
    dados.update(overrides)
    return CargoBase.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_chefia(nome: str) -> CargoComissao:
    return CargoComissao.objects.create(nome=nome, sigla="CDT", nivel=1, e_chefia=True)


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Certidão",
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


def _acao(slug: str) -> Acao:
    return Acao.objects.create(slug=slug, nome=f"Ação {slug}", tooltip="tt", ativa=True)


def _datetime(dia: date, hora: int = 12) -> datetime:
    return timezone.make_aware(datetime.combine(dia, time(hora, 0)))


def _execucao(
    acao: Acao,
    perfil: Perfil,
    unidade: Unidade,
    momento: datetime | None = None,
    **overrides: object,
) -> ExecucaoAcao:
    dados: dict[str, object] = {
        "acao": acao,
        "perfil": perfil,
        "unidade": unidade,
        "cargo_base": perfil.cargo_base,
        "cargo_comissao": perfil.cargo_comissao,
        "autorizado": True,
    }
    dados.update(overrides)
    execucao = ExecucaoAcao.objects.create(**dados)  # type: ignore[arg-type]
    if momento is not None:
        ExecucaoAcao.objects.filter(pk=execucao.pk).update(momento=momento)
        execucao.refresh_from_db()
    return execucao


# ---------------------------------------------------------------------------
# Testes de comportamento (SPEC 009 §8)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_certidao_lista_so_os_atos_autorizados_do_requerente() -> None:
    from apps.competencias.historico import atos_proprios
    from services.domain.certidao_atos_administrativos.models import BuscaAtosProprios

    raiz = _unidade("HIST-RAIZ")
    subordinada = _unidade("HIST-SUB", pai=raiz)

    # Requerente dirige a raiz, que alcança a subordinada
    requerente = _dirigente(raiz, "880001", "Requerente Dirigente")
    outro_servidor = _perfil(subordinada, "880002", "Outro Servidor")

    acao = _acao("competencias.acao_teste_proprios")
    hoje = timezone.localdate()

    # Ato autorizado do requerente: ENTRA
    ato_autorizado = _execucao(acao, requerente, raiz, momento=_datetime(hoje, 10))
    # Tentativa negada do requerente: FICA DE FORA
    _execucao(acao, requerente, raiz, momento=_datetime(hoje, 11), autorizado=False)
    # Ato autorizado de outro servidor (mesmo subordinado na unidade dirigida): FICA DE FORA
    _execucao(acao, outro_servidor, subordinada, momento=_datetime(hoje, 12), autorizado=True)

    busca = BuscaAtosProprios(
        perfil_id=requerente.pk,
        inicio=hoje,
        fim=hoje,
    )
    resultado = atos_proprios(busca)

    assert len(resultado) == 1
    assert resultado[0].pk == ato_autorizado.pk
    assert resultado[0].servidor_pk == requerente.pk


@banco
@pytest.mark.django_db
def test_certidao_descreve_o_ato_pelo_cargo_e_unidade_do_dia() -> None:
    from apps.competencias.historico import atos_proprios
    from services.domain.certidao_atos_administrativos.models import BuscaAtosProprios

    unidade_inicial = _unidade("HIST-INI")
    unidade_posterior = _unidade("HIST-POST")
    cargo_inicial = _cargo_base("Analista Inicial")
    cargo_posterior = _cargo_base("Auditor Posterior")

    servidor = _perfil(unidade_inicial, "880010", "Servidor Mudanca", cargo_base=cargo_inicial)
    acao = _acao("competencias.acao_historico_dia")
    hoje = timezone.localdate()

    ato = _execucao(acao, servidor, unidade_inicial, momento=_datetime(hoje))

    # O servidor é transferido e tem seu cargo alterado DEPOIS do ato
    servidor.unidade = unidade_posterior
    servidor.cargo_base = cargo_posterior
    servidor.save(update_fields=["unidade", "cargo_base"])

    busca = BuscaAtosProprios(
        perfil_id=servidor.pk,
        inicio=hoje,
        fim=hoje,
    )
    resultado = atos_proprios(busca)

    assert len(resultado) == 1
    linha = resultado[0]
    assert linha.pk == ato.pk
    # Continua trazendo a unidade e o cargo da LINHA (do momento da execução), e não de hoje
    assert linha.unidade == unidade_inicial.sigla
    assert linha.cargo == cargo_inicial.nome


@banco
@pytest.mark.django_db
def test_atos_praticados_em_unidade_anterior_entram_na_certidao() -> None:
    from apps.competencias.historico import atos_proprios
    from services.domain.certidao_atos_administrativos.models import BuscaAtosProprios

    unidade_antiga = _unidade("HIST-ANTIGA")
    unidade_atual = _unidade("HIST-ATUAL")

    servidor = _perfil(unidade_antiga, "880020", "Servidor Transferido")
    acao = _acao("competencias.acao_unidade_anterior")
    hoje = timezone.localdate()

    # Ato praticado na unidade antiga
    ato_antigo = _execucao(acao, servidor, unidade_antiga, momento=_datetime(hoje, 9))

    # Servidor é transferido para a nova unidade
    servidor.unidade = unidade_atual
    servidor.save(update_fields=["unidade"])

    # Ato praticado na unidade atual
    ato_atual = _execucao(acao, servidor, unidade_atual, momento=_datetime(hoje, 15))

    busca = BuscaAtosProprios(
        perfil_id=servidor.pk,
        inicio=hoje,
        fim=hoje,
    )
    resultado = atos_proprios(busca)

    pks = [linha.pk for linha in resultado]
    assert pks == [ato_antigo.pk, ato_atual.pk]
    assert resultado[0].unidade == unidade_antiga.sigla
    assert resultado[1].unidade == unidade_atual.sigla
