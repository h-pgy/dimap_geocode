"""Testes do registro de ações (SPEC painel/002): o alcance de leitura por unidade, o recorte no
banco combinado com os critérios do card, a materialização da linha e a view que amarra as quatro
camadas — alcance, banco, filtro do cabeçalho e paginação — na mesma query string.

Todos levam o marker `banco`: alcance, execução gravada e as views reais.
"""

from datetime import date, datetime, time, timedelta
from itertools import count

from bs4 import BeautifulSoup
from django.test import Client
from django.urls import reverse
from django.utils import timezone

import pytest

from apps.cargos.models import CargoBase, CargoComissao
from apps.competencias.consulta import unidades_lidas
from apps.competencias.historico import linhas_de_execucoes
from apps.competencias.models import Acao, ExecucaoAcao
from apps.unidades.models import TipoUnidade, Unidade
from apps.unidades.titularidade import definir_titular
from apps.user_admin.models import Perfil
from services.domain.listagem_gestao import TAMANHO_PAGINA, BuscaExecucoes, paginar

banco = pytest.mark.banco
_SIGLAS = count(1)


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


def _cargo_base(**overrides: object) -> CargoBase:
    numero = next(_SIGLAS)
    dados: dict[str, object] = {"nome": f"Cargo Registro {numero}", "sigla": f"CR{numero}"}
    dados.update(overrides)
    return CargoBase.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_chefia(nome: str) -> CargoComissao:
    return CargoComissao.objects.create(nome=nome, sigla="CDR", nivel=1, e_chefia=True)


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Registro",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _dirigente(unidade: Unidade, rf: str, nome: str = "Dirigente") -> Perfil:
    """Titular em exercício: é o que basta para dirigir, sem concessão gravada."""
    perfil = _perfil(unidade, rf, nome, cargo_comissao=_cargo_chefia(f"Diretor {rf}"))
    definir_titular(perfil)
    return perfil


def _extinguir(unidade: Unidade, quando: date) -> None:
    unidade.extinta_em = quando
    unidade.save(update_fields=["extinta_em"])


def _acao(slug: str) -> Acao:
    return Acao.objects.create(slug=slug, nome=f"Ação {slug}", tooltip="tt", ativa=True)


def _datetime(dia: date) -> datetime:
    return timezone.make_aware(datetime.combine(dia, time(12, 0)))


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


def _busca(unidades: frozenset[int], **overrides: object) -> BuscaExecucoes:
    hoje = timezone.localdate()
    dados: dict[str, object] = {
        "unidades_lidas": unidades,
        "inicio": hoje - timedelta(days=30),
        "fim": hoje,
    }
    dados.update(overrides)
    return BuscaExecucoes(**dados)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# O alcance de leitura nasce na própria unidade
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_leitura_parte_da_propria_unidade() -> None:
    raiz = _unidade("REG-1")
    filha = _unidade("REG-11", pai=raiz)
    neta_extinta = _unidade("REG-111", pai=filha)
    _extinguir(neta_extinta, date(2026, 1, 1))

    comum = _perfil(filha, "9700001", "Comum")
    dirigente = _dirigente(raiz, "9700002", "Dirigente")
    superusuario = _perfil(raiz, "9700003", "Super", is_superuser=True)

    assert unidades_lidas(comum, None) == frozenset({filha.pk})
    assert unidades_lidas(dirigente, None) == frozenset({raiz.pk, filha.pk, neta_extinta.pk})
    # Único ramo do organograma nesta massa: "todas" para o superusuário É este conjunto —
    # a unidade extinta continua alcançada mesmo para quem não a dirigia originalmente.
    assert unidades_lidas(superusuario, None) == frozenset({raiz.pk, filha.pk, neta_extinta.pk})


# ---------------------------------------------------------------------------
# Escolher uma unidade estreita para o sub-ramo; fora do alcance esvazia
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_unidade_escolhida_estreita_ou_esvazia() -> None:
    raiz = _unidade("REG-2")
    filha = _unidade("REG-21", pai=raiz)
    alheia = _unidade("REG-ALHEIA")

    dirigente = _dirigente(raiz, "9700010", "Dirigente")
    comum = _perfil(filha, "9700011", "Comum")

    assert unidades_lidas(dirigente, filha.pk) == frozenset({filha.pk})
    assert unidades_lidas(dirigente, alheia.pk) == frozenset()
    assert unidades_lidas(comum, alheia.pk) == frozenset()


# ---------------------------------------------------------------------------
# O controle de unidade só existe para quem dirige
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_card_oferece_unidade_so_para_quem_dirige(client: Client) -> None:
    raiz = _unidade("REG-3")
    filha = _unidade("REG-31", pai=raiz)
    dirigente = _dirigente(raiz, "9700020", "Dirigente")
    comum = _perfil(filha, "9700021", "Comum")

    client.force_login(dirigente)
    sopa_dirigente = BeautifulSoup(
        client.get(reverse("competencias:listar_registro_acoes")).content.decode(), "html.parser"
    )
    client.force_login(comum)
    sopa_comum = BeautifulSoup(
        client.get(reverse("competencias:listar_registro_acoes")).content.decode(), "html.parser"
    )

    select_dirigente = sopa_dirigente.select_one("select[name='unidade_partida']")
    assert select_dirigente is not None
    valores = {opcao["value"] for opcao in select_dirigente.select("option")}
    assert valores == {str(raiz.pk), str(filha.pk)}
    selecionada = select_dirigente.select_one("option[selected]")
    assert selecionada is not None
    assert selecionada["value"] == str(raiz.pk)

    assert sopa_comum.select_one("select[name='unidade_partida']") is None


# ---------------------------------------------------------------------------
# Autor, cargos e período combinam cumulativamente
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_busca_combina_autor_cargos_e_periodo_cumulativamente() -> None:
    unidade = _unidade("REG-4")
    acao = _acao("competencias.teste_busca")
    hoje = timezone.localdate()

    marina = _perfil(unidade, "9700030", "Marina")
    paulo = _perfil(unidade, "9700031", "Paulo")
    outro_cargo_base = _cargo_base()

    dentro_do_criterio = _execucao(acao, marina, unidade, momento=_datetime(hoje))
    autor_errado = _execucao(acao, paulo, unidade, momento=_datetime(hoje))
    cargo_errado = _execucao(
        acao, marina, unidade, momento=_datetime(hoje), cargo_base=outro_cargo_base
    )
    fora_do_periodo = _execucao(acao, marina, unidade, momento=_datetime(hoje - timedelta(days=40)))

    linhas = linhas_de_execucoes(
        _busca(
            frozenset({unidade.pk}),
            perfil_id=marina.pk,
            cargo_base_id=marina.cargo_base_id,
        )
    )

    pks = {linha.pk for linha in linhas}
    assert pks == {dentro_do_criterio.pk}
    assert autor_errado.pk not in pks
    assert cargo_errado.pk not in pks
    assert fora_do_periodo.pk not in pks


# ---------------------------------------------------------------------------
# A linha diz a autorização, a cobertura e sobrevive ao autor apagado
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_linha_diz_a_autorizacao_a_cobertura_e_o_autor_apagado() -> None:
    unidade = _unidade("REG-5")
    acao = _acao("competencias.teste_linha")
    titular = _perfil(unidade, "9700040", "Titular", sobrenome="Toledo")
    substituto = _perfil(unidade, "9700041", "Substituto", sobrenome="Nakamura")
    apagavel = _perfil(unidade, "9700042", "Apagavel")

    negada = _execucao(acao, substituto, unidade, autorizado=False)
    em_substituicao = _execucao(acao, substituto, unidade, autorizado=True, substituindo=titular)
    competencia_propria = _execucao(acao, substituto, unidade, autorizado=True)
    de_autor_apagado = _execucao(acao, apagavel, unidade, autorizado=True)
    ExecucaoAcao.objects.filter(pk=de_autor_apagado.pk).update(perfil=None)

    linhas = {
        linha.pk: linha
        for linha in linhas_de_execucoes(_busca(frozenset({unidade.pk})))
    }

    assert linhas[negada.pk].autorizado is False
    assert linhas[em_substituicao.pk].substituindo == "Titular Toledo"
    assert linhas[competencia_propria.pk].substituindo == ""
    assert linhas[de_autor_apagado.pk].servidor_pk is None
    assert linhas[de_autor_apagado.pk].servidor == "—"


# ---------------------------------------------------------------------------
# A paginação percorre o resultado inteiro do período
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_paginacao_percorre_o_resultado_inteiro() -> None:
    unidade = _unidade("REG-6")
    acao = _acao("competencias.teste_volume")
    autor = _perfil(unidade, "9700050", "Volume")
    agora = timezone.now()

    ExecucaoAcao.objects.bulk_create(
        [
            ExecucaoAcao(
                acao=acao,
                perfil=autor,
                unidade=unidade,
                cargo_base=autor.cargo_base,
                autorizado=True,
            )
            for _ in range(600)
        ]
    )
    todas = list(ExecucaoAcao.objects.filter(unidade=unidade).order_by("pk"))
    for indice, execucao in enumerate(todas):
        execucao.momento = agora - timedelta(minutes=indice)
    ExecucaoAcao.objects.bulk_update(todas, ["momento"])
    # A ordem cronológica reversa (a mais recente primeiro) é o que a página 1 e a última
    # precisam respeitar — a linha de índice 0 tem o momento mais recente.
    mais_recente, mais_antiga = todas[0], todas[-1]

    linhas = linhas_de_execucoes(
        _busca(
            frozenset({unidade.pk}),
            inicio=agora.date() - timedelta(days=1),
            fim=agora.date() + timedelta(days=1),
        )
    )
    pagina_1 = paginar(linhas, numero=1, tamanho=TAMANHO_PAGINA)
    pagina_12 = paginar(linhas, numero=12, tamanho=TAMANHO_PAGINA)

    assert pagina_1.total_paginas == 12
    assert pagina_1.total_linhas == 600
    assert len(pagina_1.linhas) == 50
    assert len(pagina_12.linhas) == 50
    assert pagina_1.linhas[0].pk == mais_recente.pk
    assert pagina_12.linhas[-1].pk == mais_antiga.pk


# ---------------------------------------------------------------------------
# O corpo aplica alcance, busca, filtros do cabeçalho e página da mesma query string
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_corpo_aplica_alcance_busca_filtros_e_pagina_da_mesma_query_string(client: Client) -> None:
    unidade = _unidade("REG-7")
    fora_do_alcance = _unidade("REG-FORA-7")
    leitor = _dirigente(unidade, "9700060", "Leitor")
    marina = _perfil(unidade, "9700061", "Marina", sobrenome="Toledo")
    paulo = _perfil(unidade, "9700062", "Paulo", sobrenome="Rezende")
    acao = _acao("competencias.teste_corpo")
    hoje = timezone.localdate()

    alvo = _execucao(acao, marina, unidade, momento=_datetime(hoje), operacao="cadastrar")
    _execucao(
        acao, marina, unidade, momento=_datetime(hoje - timedelta(days=40)), operacao="cadastrar"
    )  # fora do período do card
    _execucao(acao, marina, unidade, momento=_datetime(hoje), operacao="editar")  # fora do filtro do cabeçalho
    _execucao(acao, paulo, unidade, momento=_datetime(hoje), operacao="cadastrar")  # fora do critério de autor
    _execucao(
        acao, marina, fora_do_alcance, momento=_datetime(hoje), operacao="cadastrar"
    )  # fora do alcance

    client.force_login(leitor)
    resposta = client.get(
        reverse("competencias:corpo_execucoes"),
        {
            "unidade_partida": str(unidade.pk),
            "perfil": str(marina.pk),
            "inicio": (hoje - timedelta(days=30)).isoformat(),
            "fim": hoje.isoformat(),
            "operacao": "cadastrar",
            "pagina": "1",
        },
    )
    sopa = BeautifulSoup(resposta.content.decode(), "html.parser")
    linhas = sopa.select("#corpo-execucoes tr")

    assert resposta.status_code == 200
    assert len(linhas) == 1
    assert "Marina" in linhas[0].get_text()
    assert alvo.operacao in linhas[0].get_text()
