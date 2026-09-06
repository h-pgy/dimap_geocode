"""Testes de apps/competencias/views.py: a tela de atribuições da unidade (SPEC autorizacao/007) —
quem a abre, que organograma ela oferece como alvo, e os dois atos que ela pratica — e a tela de
conceder competência (SPEC autorizacao/008), que distribui essas atribuições entre os cargos.

A autorização não é reescrita aqui: quem exerce a ação é quem responde pela direção (estrutural,
SPEC 003) e sobre quais unidades ele pode incidir é o alcance declarado no contrato (SPEC 004). O
que estes testes fixam é que a rota cumpre as duas sem a view conferir nada — exceto a atribuição-
alvo da SPEC 008, que a proteção não tem como conhecer (Caveats da 008).

Todos levam o marker `banco`: direção, atribuição e concessão são lidas do banco.
"""

from datetime import timedelta

from bs4 import BeautifulSoup
from bs4.element import Tag
from django.test import Client
from django.urls import reverse
from django.utils import timezone

import pytest

from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao, Delegacao, ExecucaoAcao
from apps.user_admin.exercicio import designar_substituto, registrar_impedimento
from apps.unidades.models import TipoUnidade, Unidade
from apps.cargos.models import CargoBase, CargoComissao
from apps.user_admin.models import Perfil, TipoImpedimento
from apps.user_admin.schemas import NovaSubstituicao, NovoImpedimento
from apps.unidades.titularidade import definir_titular

banco = pytest.mark.banco

SLUG_ACAO = "competencias.definir_atribuicao"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Atribuição",
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
    dados: dict[str, object] = {"nome": "Cargo Atribuição", "sigla": "CGAT"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _cargo_chefia(nome: str) -> CargoComissao:
    return CargoComissao.objects.create(nome=nome, sigla="CDA", nivel=1, e_chefia=True)


def _cargo_comissao(**overrides: object) -> CargoComissao:
    dados: dict[str, object] = {
        "nome": "Cargo Comissão Concessão",
        "sigla": "CCC",
        "nivel": 1,
        "e_chefia": True,
    }
    dados.update(overrides)
    return CargoComissao.objects.create(**dados)  # type: ignore[arg-type]


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Atribuição",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _dirigente(unidade: Unidade, rf: str, nome: str = "Dirigente") -> Perfil:
    """Titular em exercício: é o que basta para exercer a estrutural, sem concessão gravada."""
    perfil = _perfil(unidade, rf, nome, cargo_comissao=_cargo_chefia(f"Diretor {rf}"))
    definir_titular(perfil)
    return perfil


def _acao(slug: str, **overrides: object) -> Acao:
    dados: dict[str, object] = {"nome": f"Ação {slug}", "tooltip": "tt", "ativa": True}
    dados.update(overrides)
    acao, _ = Acao.objects.get_or_create(slug=slug, defaults=dados)  # type: ignore[arg-type]
    return acao


def _atribuir(unidade: Unidade, acao: Acao) -> AtribuicaoUnidade:
    return AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)


def _conceder(atribuicao: AtribuicaoUnidade, cargo_base: CargoBase) -> Concessao:
    return Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo_base)


def _cobrir(substituto: Perfil, titular: Perfil) -> None:
    """Afasta o titular e põe o substituto no lugar. É por aqui que um perfil passa a dirigir mais
    de uma unidade (SPEC user_admin/015) — o caso que o alcance precisa saber tratar."""
    tipo, _ = TipoImpedimento.objects.get_or_create(nome="Licença Atribuição")
    hoje = timezone.localdate()
    impedimento = registrar_impedimento(
        titular,
        NovoImpedimento(
            tipo=tipo.pk,
            data_inicio=hoje - timedelta(days=1),
            data_fim=None,
        ),
    )
    designar_substituto(
        impedimento,
        NovaSubstituicao(substituto=substituto.pk, data_inicio=hoje, data_fim=None),
    )


# ---------------------------------------------------------------------------
# Helpers de leitura da resposta
# ---------------------------------------------------------------------------


def _url_tela() -> str:
    return reverse("competencias:definir_atribuicao")


def _sopa(client: Client, url: str) -> BeautifulSoup:
    return BeautifulSoup(client.get(url).content.decode(), "html.parser")


def _no_da_unidade(soup: BeautifulSoup, sigla: str) -> Tag | None:
    rotulo = soup.find(
        class_="card-unidade-sigla",
        string=lambda texto: bool(texto) and texto.strip() == sigla,
    )
    return rotulo.find_parent(class_="no-arvore") if rotulo else None


def _siglas_da_arvore(soup: BeautifulSoup) -> set[str]:
    return {rotulo.get_text(strip=True) for rotulo in soup.find_all(class_="card-unidade-sigla")}


def _raizes_da_arvore(soup: BeautifulSoup) -> list[Tag]:
    organograma = soup.find(class_="organograma")
    assert organograma is not None, "a tela não trouxe organograma nenhum"
    return organograma.find_all(class_="no-arvore", recursive=False)


def _url_tela_conceder() -> str:
    return reverse("competencias:conceder")


def _nomes_das_acoes_no_poco(soup: BeautifulSoup) -> set[str]:
    return {rotulo.get_text(strip=True) for rotulo in soup.find_all(class_="card-atribuicao-nome")}


# ---------------------------------------------------------------------------
# Quem abre a tela
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_tela_abre_para_quem_dirige_e_nega_o_resto(client: Client) -> None:
    unidade = _unidade("DIR-ABRE")
    titular = _dirigente(unidade, "910100", "Titular")
    outra = _unidade("DIR-OUTRA")
    substituto = _perfil(outra, "910101", "Substituto")
    sem_direcao = _perfil(outra, "910102", "Sem Direção")

    # Titular em exercício: entra sem nenhuma concessão gravada — a estrutural decorre da direção.
    client.force_login(titular)
    assert client.get(_url_tela()).status_code == 200

    # Quem não dirige nada e não recebeu concessão nenhuma não passa da primeira barreira.
    client.force_login(sem_direcao)
    assert client.get(_url_tela()).status_code == 403

    # Afastado o titular, quem responde pela direção é o substituto — e a tela é dele enquanto durar.
    _cobrir(substituto, titular)
    client.force_login(substituto)
    assert client.get(_url_tela()).status_code == 200

    client.force_login(Perfil.objects.get(pk=titular.pk))
    assert client.get(_url_tela()).status_code == 403


@banco
@pytest.mark.django_db
def test_concessao_sem_direcao_abre_a_tela_sem_alvo(client: Client) -> None:
    """A concessão de uma estrutural com alcance libera o slug, não o alvo (SPEC 007, Caveats):
    a tela abre, e não há sobre o que agir."""
    unidade = _unidade("CONC-SEM-DIR")
    alheia = _unidade("CONC-ALHEIA")
    perfil = _perfil(unidade, "910110", "Concessão Sem Direção")
    _conceder(_atribuir(unidade, _acao(SLUG_ACAO, estrutural=True)), perfil.cargo_base)

    client.force_login(perfil)
    resposta = client.get(_url_tela())
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")

    assert resposta.status_code == 200
    assert soup.find(class_="no-arvore") is None

    negada = client.post(
        reverse("competencias:atribuir"),
        {"unidade": str(alheia.pk), "acao": SLUG_ACAO},
    )
    assert negada.status_code == 403


# ---------------------------------------------------------------------------
# O organograma como seletor do alvo
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_organograma_oferece_so_a_subarvore_dirigida(client: Client) -> None:
    raiz = _unidade("ARV-RAIZ")
    meio = _unidade("ARV-MEIO", pai=raiz)
    baixo = _unidade("ARV-BAIXO", pai=meio)
    _unidade("ARV-TIA", pai=raiz)

    dirigente = _dirigente(meio, "910120")
    client.force_login(dirigente)
    soup = _sopa(client, _url_tela())

    # A árvore nasce na dirigida e desce: a de cima e o ramo vizinho não são desenhados.
    assert _siglas_da_arvore(soup) == {"ARV-MEIO", "ARV-BAIXO"}
    # E não há como navegar para fora dela: nesta tela o card escolhe o alvo, não leva a lugar nenhum.
    assert soup.find(class_="card-unidade-pagina") is None
    assert soup.find(class_="no-arvore-irmas") is None

    # Sem escolha feita, o alvo é a dirigida.
    no_do_meio = _no_da_unidade(soup, "ARV-MEIO")
    assert no_do_meio is not None
    assert "no-arvore-ego" in no_do_meio["class"]

    # Dirigir uma unidade e outra abaixo dela é um ramo só: o de baixo já está dentro do de cima.
    titular_de_baixo = _dirigente(baixo, "910121", "Titular De Baixo")
    _cobrir(dirigente, titular_de_baixo)
    soup = _sopa(client, _url_tela())
    assert len(_raizes_da_arvore(soup)) == 1
    assert _siglas_da_arvore(soup) == {"ARV-MEIO", "ARV-BAIXO"}


@banco
@pytest.mark.django_db
def test_tela_abre_na_primeira_dirigida_por_sigla(client: Client) -> None:
    """Duas dirigidas sem parentesco são duas raízes, e `unidades_dirigidas` devolve conjunto: sem
    ordem explícita a tela abriria numa unidade diferente a cada requisição."""
    ultima = _unidade("ZZZ-DIRIGIDA")
    primeira = _unidade("AAA-DIRIGIDA")
    dirigente = _dirigente(ultima, "910130")
    _cobrir(dirigente, _dirigente(primeira, "910131", "Titular Da Primeira"))

    client.force_login(dirigente)
    soup = _sopa(client, _url_tela())

    assert len(_raizes_da_arvore(soup)) == 2
    no_da_primeira = _no_da_unidade(soup, "AAA-DIRIGIDA")
    assert no_da_primeira is not None
    assert "no-arvore-ego" in no_da_primeira["class"]


# ---------------------------------------------------------------------------
# Os dois atos
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_atribuir_recusa_unidade_fora_do_alcance(client: Client) -> None:
    dirigida = _unidade("ALC-DIRIGIDA")
    subordinada = _unidade("ALC-SUB", pai=dirigida)
    fora = _unidade("ALC-FORA")
    acao = _acao("competencias.acao_do_catalogo")
    dirigente = _dirigente(dirigida, "910140")

    client.force_login(dirigente)

    # Id válido, unidade existente — e ainda assim recusada: o ramo é outro.
    recusada = client.post(
        reverse("competencias:atribuir"),
        {"unidade": str(fora.pk), "acao": acao.slug},
    )
    assert recusada.status_code == 403
    assert not AtribuicaoUnidade.objects.filter(unidade=fora).exists()

    aceita = client.post(
        reverse("competencias:atribuir"),
        {"unidade": str(subordinada.pk), "acao": acao.slug},
    )
    assert aceita.status_code == 200
    assert AtribuicaoUnidade.objects.filter(unidade=subordinada, acao=acao).exists()


@banco
@pytest.mark.django_db
def test_remover_so_apaga_no_post_confirmado(client: Client) -> None:
    unidade = _unidade("REM-UNIDADE")
    acao = _acao("competencias.acao_a_remover")
    atribuicao = _atribuir(unidade, acao)
    _conceder(atribuicao, _cargo_base(nome="Auditor Removível", sigla="AUDR"))
    _conceder(atribuicao, _cargo_base(nome="Chefe Removível", sigla="CHER"))
    dirigente = _dirigente(unidade, "910150")

    client.force_login(dirigente)

    # A confirmação é leitura: diz quantos cargos caem e não apaga nada.
    confirmacao = client.get(
        reverse("competencias:confirmar_remocao"),
        {"unidade": str(unidade.pk), "acao": acao.slug},
    )
    assert confirmacao.status_code == 200
    corpo = confirmacao.content.decode()
    assert "Auditor Removível" in corpo
    assert "Chefe Removível" in corpo
    assert AtribuicaoUnidade.objects.filter(pk=atribuicao.pk).exists()
    assert Concessao.objects.filter(atribuicao=atribuicao).count() == 2

    # Confirmada, a atribuição sai levando as concessões dependentes.
    removida = client.post(
        reverse("competencias:remover"),
        {"unidade": str(unidade.pk), "acao": acao.slug},
    )
    assert removida.status_code == 200
    assert not AtribuicaoUnidade.objects.filter(pk=atribuicao.pk).exists()
    assert not Concessao.objects.filter(atribuicao=atribuicao).exists()


@banco
@pytest.mark.django_db
def test_atribuir_e_remover_ficam_registrados_com_alvo(client: Client) -> None:
    unidade = _unidade("REG-UNIDADE")
    acao = _acao("competencias.acao_registrada")
    dirigente = _dirigente(unidade, "910160")

    client.force_login(dirigente)
    dados = {"unidade": str(unidade.pk), "acao": acao.slug}
    client.post(reverse("competencias:atribuir"), dados)
    client.post(reverse("competencias:remover"), dados)

    registros = {
        execucao.operacao: execucao
        for execucao in ExecucaoAcao.objects.filter(autorizado=True)
    }
    assert set(registros) == {"atribuir", "remover"}
    for execucao in registros.values():
        assert execucao.perfil_id == dirigente.pk
        assert execucao.alvo_tipo == "unidade_acao"
        assert execucao.alvo_identificador == f"{unidade.sigla}:{acao.slug}"


# ---------------------------------------------------------------------------
# SPEC autorizacao/008 — Conceder competência
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_tela_abre_para_quem_dirige(client: Client) -> None:
    unidade = _unidade("CONC-ABRE")
    titular = _dirigente(unidade, "910260", "Titular Conceder")
    outra = _unidade("CONC-OUTRA")
    substituto = _perfil(outra, "910261", "Substituto Conceder")
    sem_direcao = _perfil(outra, "910262", "Sem Direção Conceder")

    # Titular em exercício: entra sem nenhuma concessão gravada da própria ação.
    client.force_login(titular)
    assert client.get(_url_tela_conceder()).status_code == 200

    client.force_login(sem_direcao)
    assert client.get(_url_tela_conceder()).status_code == 403

    # Afastado o titular, quem responde pela direção é o substituto.
    _cobrir(substituto, titular)
    client.force_login(substituto)
    assert client.get(_url_tela_conceder()).status_code == 200

    client.force_login(Perfil.objects.get(pk=titular.pk))
    assert client.get(_url_tela_conceder()).status_code == 403


@banco
@pytest.mark.django_db
def test_poco_traz_so_as_atribuicoes_da_unidade_escolhida(client: Client) -> None:
    raiz = _unidade("CONC-RAIZ")
    meio = _unidade("CONC-MEIO", pai=raiz)
    baixo = _unidade("CONC-BAIXO", pai=meio)
    acao_meio = _acao("competencias.acao_conc_meio")
    acao_baixo = _acao("competencias.acao_conc_baixo")
    _atribuir(meio, acao_meio)
    _atribuir(baixo, acao_baixo)
    dirigente = _dirigente(meio, "910270")

    client.force_login(dirigente)
    soup = _sopa(client, _url_tela_conceder())

    # O poço é só do alvo em foco — a dirigida, por padrão —, mesmo a subordinada estando alcançada.
    assert _nomes_das_acoes_no_poco(soup) == {acao_meio.nome}
    # O seletor, esse sim, oferece a subárvore inteira — e a unidade acima não aparece nele.
    assert _siglas_da_arvore(soup) == {"CONC-MEIO", "CONC-BAIXO"}

    soup_baixo = BeautifulSoup(
        client.get(
            reverse("competencias:painel_concessoes"), {"unidade": str(baixo.pk)}
        ).content.decode(),
        "html.parser",
    )
    assert _nomes_das_acoes_no_poco(soup_baixo) == {acao_baixo.nome}


@banco
@pytest.mark.django_db
def test_concessao_recusa_unidade_fora_do_alcance(client: Client) -> None:
    dirigida = _unidade("CONC-ALC-DIRIGIDA")
    fora = _unidade("CONC-ALC-FORA")
    acao = _acao("competencias.acao_conc_fora")
    atribuicao_fora = _atribuir(fora, acao)
    cargo = _cargo_base(nome="Cargo Fora Do Alcance", sigla="CFDA")
    dirigente = _dirigente(dirigida, "910280")

    client.force_login(dirigente)
    # Id válido, unidade existente — e ainda assim recusada: o ramo é outro.
    resposta = client.post(
        reverse("competencias:conceder_cargo"),
        {
            "unidade": str(fora.pk),
            "atribuicao": str(atribuicao_fora.pk),
            "cargo_base": str(cargo.pk),
        },
    )

    assert resposta.status_code == 403
    assert not Concessao.objects.filter(atribuicao=atribuicao_fora).exists()


@banco
@pytest.mark.django_db
def test_concessao_recusa_atribuicao_de_outra_unidade(client: Client) -> None:
    dirigida = _unidade("CONC-ATR-DIRIGIDA")
    fora = _unidade("CONC-ATR-FORA")
    acao = _acao("competencias.acao_conc_atr_fora")
    atribuicao_da_fora = _atribuir(fora, acao)
    cargo = _cargo_base(nome="Cargo Atribuição Alheia", sigla="CAAL")
    dirigente = _dirigente(dirigida, "910290")

    client.force_login(dirigente)
    # Unidade válida e alcançada — só a atribuição pertence a um ramo que o perfil não dirige.
    resposta = client.post(
        reverse("competencias:conceder_cargo"),
        {
            "unidade": str(dirigida.pk),
            "atribuicao": str(atribuicao_da_fora.pk),
            "cargo_base": str(cargo.pk),
        },
    )

    assert resposta.status_code == 403
    assert not Concessao.objects.filter(atribuicao=atribuicao_da_fora).exists()


@banco
@pytest.mark.django_db
def test_concessao_mira_exatamente_um_cargo(client: Client) -> None:
    unidade = _unidade("CONC-XOR-UNIDADE")
    acao = _acao("competencias.acao_conc_xor")
    atribuicao = _atribuir(unidade, acao)
    cargo_base = _cargo_base(nome="Cargo XOR Base", sigla="CXB")
    cargo_comissao = _cargo_comissao(nome="Cargo XOR Comissão", sigla="CXC")
    dirigente = _dirigente(unidade, "910300")

    client.force_login(dirigente)
    dados = {"unidade": str(unidade.pk), "atribuicao": str(atribuicao.pk)}

    os_dois = dados | {"cargo_base": str(cargo_base.pk), "cargo_comissao": str(cargo_comissao.pk)}
    assert client.post(reverse("competencias:conceder_cargo"), os_dois).status_code == 422

    assert client.post(reverse("competencias:conceder_cargo"), dados).status_code == 422
    assert not Concessao.objects.filter(atribuicao=atribuicao).exists()


@banco
@pytest.mark.django_db
def test_conceder_e_revogar_ficam_registrados_com_alvo(client: Client) -> None:
    unidade = _unidade("CONC-REG-UNIDADE")
    acao = _acao("competencias.acao_conc_registrada")
    atribuicao = _atribuir(unidade, acao)
    cargo = _cargo_base(nome="Cargo Registrado Concessão", sigla="CRGC")
    dirigente = _dirigente(unidade, "910310")

    client.force_login(dirigente)
    concedida = client.post(
        reverse("competencias:conceder_cargo"),
        {"unidade": str(unidade.pk), "atribuicao": str(atribuicao.pk), "cargo_base": str(cargo.pk)},
    )
    assert concedida.status_code == 200
    concessao = Concessao.objects.get(atribuicao=atribuicao, cargo_base=cargo)

    revogada = client.post(
        reverse("competencias:revogar_cargo"),
        {"unidade": str(unidade.pk), "concessao": str(concessao.pk)},
    )
    assert revogada.status_code == 200
    assert not Concessao.objects.filter(pk=concessao.pk).exists()

    registros = {
        execucao.operacao: execucao
        for execucao in ExecucaoAcao.objects.filter(autorizado=True)
    }
    assert set(registros) == {"conceder", "revogar"}
    for execucao in registros.values():
        assert execucao.perfil_id == dirigente.pk
        assert execucao.alvo_tipo == "acao_cargo"
        assert acao.slug in execucao.alvo_identificador
        assert cargo.sigla in execucao.alvo_identificador


@banco
@pytest.mark.django_db
def test_slugs_liberados_da_acao_concedida_so_para_quem_dirige(client: Client) -> None:
    # Importado aqui, e não no topo: ACAO_CONCEDER ainda não existe no regime `testes_tdd: true` —
    # isolar o import mantém o resto do módulo (SPEC 007, já implementada) coletável e verde.
    from apps.competencias.acoes_declaradas import ACAO_CONCEDER
    from apps.competencias.resolucao import slugs_liberados

    unidade = _unidade("CONC-MENU-UNIDADE")
    outra = _unidade("CONC-MENU-OUTRA")
    dirigente = _dirigente(unidade, "910320")
    sem_direcao = _perfil(outra, "910321", "Sem Direção Menu Concessão")

    assert ACAO_CONCEDER.acao.slug in slugs_liberados(dirigente)
    assert ACAO_CONCEDER.acao.slug not in slugs_liberados(sem_direcao)


def _delegar(
    atribuicao: AtribuicaoUnidade,
    delegante: Perfil,
    delegado: Perfil,
    **overrides: object,
) -> Delegacao:
    from apps.competencias.models.delegacao import Delegacao

    dados: dict[str, object] = {
        "acao": atribuicao.acao,
        "unidade": atribuicao.unidade,
        "delegante": delegante,
        "delegado": delegado,
        "data_inicio": timezone.localdate(),
        "data_fim": None,
    }
    dados.update(overrides)
    return Delegacao.objects.create(**dados)


# ---------------------------------------------------------------------------
# SPEC autorizacao/009 — Delegação nominal de competência estrutural: Comportamento
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_delegacao_nominal_libera_acao_ao_servidor() -> None:
    unidade = _unidade("DEL-NOM-UNIDADE")
    titular = _dirigente(unidade, "910400", "Titular Delegante")
    delegado = _perfil(unidade, "910401", "Servidor Delegado")
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao = _atribuir(unidade, acao)

    assert not delegado.has_perm(acao.slug)

    _delegar(atribuicao, delegante=titular, delegado=delegado)

    fresco = Perfil.objects.get(pk=delegado.pk)
    assert fresco.has_perm(acao.slug)


@banco
@pytest.mark.django_db
def test_delegacao_carrega_alcance_da_unidade_delegante() -> None:
    from apps.competencias.consulta import alcance_do_perfil

    raiz = _unidade("DEL-ALC-RAIZ")
    meio = _unidade("DEL-ALC-MEIO", pai=raiz)
    baixo = _unidade("DEL-ALC-BAIXO", pai=meio)
    irmao = _unidade("DEL-ALC-IRMAO", pai=raiz)

    titular_meio = _dirigente(meio, "910410", "Dirigente Meio")
    delegado = _perfil(baixo, "910411", "Delegado Baixo")
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao = _atribuir(meio, acao)

    assert alcance_do_perfil(delegado) == frozenset()

    _delegar(atribuicao, delegante=titular_meio, delegado=delegado)

    alcance = alcance_do_perfil(delegado)
    assert meio.pk in alcance
    assert baixo.pk in alcance
    assert raiz.pk not in alcance
    assert irmao.pk not in alcance


@banco
@pytest.mark.django_db
def test_delegado_pratica_ato_estrutural_no_ramo(client: Client) -> None:
    raiz = _unidade("DEL-PRAT-RAIZ")
    meio = _unidade("DEL-PRAT-MEIO", pai=raiz)
    baixo = _unidade("DEL-PRAT-BAIXO", pai=meio)

    titular = _dirigente(meio, "910420", "Dirigente Meio Pratica")
    delegado = _perfil(baixo, "910421", "Delegado Pratica")
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao = _atribuir(meio, acao)
    acao_a_atribuir = _acao("competencias.acao_praticada", estrutural=False)

    _delegar(atribuicao, delegante=titular, delegado=delegado)

    client.force_login(delegado)
    resposta = client.post(
        reverse("competencias:atribuir"),
        {"unidade": str(baixo.pk), "acao": acao_a_atribuir.slug},
    )

    assert resposta.status_code == 200
    assert AtribuicaoUnidade.objects.filter(unidade=baixo, acao=acao_a_atribuir).exists()


@banco
@pytest.mark.django_db
def test_delegado_nao_herda_outras_competencias_nem_direcao() -> None:
    from apps.competencias.consulta import dirige, unidades_dirigidas

    unidade = _unidade("DEL-ISOL-UNIDADE")
    titular = _dirigente(unidade, "910430", "Dirigente Titular Isol")
    delegado = _perfil(unidade, "910431", "Delegado Isol")
    acao_delegada = _acao("competencias.definir_atribuicao", estrutural=True)
    acao_nao_delegada = _acao("competencias.conceder", estrutural=True)
    atribuicao = _atribuir(unidade, acao_delegada)
    _atribuir(unidade, acao_nao_delegada)

    _delegar(atribuicao, delegante=titular, delegado=delegado)

    fresco = Perfil.objects.get(pk=delegado.pk)
    assert fresco.has_perm(acao_delegada.slug)
    assert not fresco.has_perm(acao_nao_delegada.slug)
    assert not dirige(fresco, unidade)
    assert unidade.pk not in unidades_dirigidas(fresco)


@banco
@pytest.mark.django_db
def test_delegado_pode_ser_de_unidade_subordinada(client: Client) -> None:
    from apps.competencias.models.delegacao import Delegacao

    raiz = _unidade("DEL-SUB-RAIZ")
    sub = _unidade("DEL-SUB-SUBORDINADA", pai=raiz)

    titular_raiz = _dirigente(raiz, "910440", "Dirigente Raiz")
    delegado_sub = _perfil(sub, "910441", "Servidor Subordinada")
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao = _atribuir(raiz, acao)

    client.force_login(titular_raiz)
    hoje = timezone.localdate()
    resposta = client.post(
        reverse("competencias:delegar_servidor"),
        {
            "unidade": str(raiz.pk),
            "atribuicao": str(atribuicao.pk),
            "delegado": str(delegado_sub.pk),
            "data_inicio": hoje.isoformat(),
        },
    )

    assert resposta.status_code == 200
    assert Delegacao.objects.filter(
        unidade=raiz,
        acao=acao,
        delegante=titular_raiz,
        delegado=delegado_sub,
    ).exists()


@banco
@pytest.mark.django_db
def test_candidato_fora_do_alcance_e_recusado(client: Client) -> None:
    from apps.competencias.models.delegacao import Delegacao

    ramo_a = _unidade("DEL-FORA-A")
    ramo_b = _unidade("DEL-FORA-B")

    titular_a = _dirigente(ramo_a, "910450", "Dirigente Ramo A")
    servidor_b = _perfil(ramo_b, "910451", "Servidor Ramo B")
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao = _atribuir(ramo_a, acao)

    client.force_login(titular_a)
    hoje = timezone.localdate()
    resposta = client.post(
        reverse("competencias:delegar_servidor"),
        {
            "unidade": str(ramo_a.pk),
            "atribuicao": str(atribuicao.pk),
            "delegado": str(servidor_b.pk),
            "data_inicio": hoje.isoformat(),
        },
    )

    assert resposta.status_code in (200, 422)
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")
    assert soup.find(class_="erro-formulario") is not None or "delegado" in resposta.content.decode()
    assert not Delegacao.objects.filter(delegado=servidor_b).exists()


@banco
@pytest.mark.django_db
def test_delegacao_com_periodo_futuro_nao_libera_hoje() -> None:
    from apps.competencias.consulta import alcance_do_perfil

    unidade = _unidade("DEL-FUT-UNIDADE")
    titular = _dirigente(unidade, "910460", "Dirigente Futuro")
    delegado = _perfil(unidade, "910461", "Delegado Futuro")
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao = _atribuir(unidade, acao)

    hoje = timezone.localdate()
    _delegar(
        atribuicao,
        delegante=titular,
        delegado=delegado,
        data_inicio=hoje + timedelta(days=5),
    )

    fresco = Perfil.objects.get(pk=delegado.pk)
    assert not fresco.has_perm(acao.slug)
    assert unidade.pk not in alcance_do_perfil(fresco)


@banco
@pytest.mark.django_db
def test_revogar_delegacao_encerra_vigencia_ou_apaga(client: Client) -> None:
    from apps.competencias.models.delegacao import Delegacao

    unidade = _unidade("DEL-REV-UNIDADE")
    titular = _dirigente(unidade, "910470", "Dirigente Revogar")
    delegado1 = _perfil(unidade, "910471", "Delegado 1")
    delegado2 = _perfil(unidade, "910472", "Delegado 2")
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao = _atribuir(unidade, acao)

    hoje = timezone.localdate()
    del1 = _delegar(
        atribuicao,
        delegante=titular,
        delegado=delegado1,
        data_inicio=hoje - timedelta(days=2),
    )
    del2 = _delegar(
        atribuicao,
        delegante=titular,
        delegado=delegado2,
        data_inicio=hoje + timedelta(days=2),
    )

    client.force_login(titular)

    resp1 = client.post(
        reverse("competencias:revogar_delegacao"),
        {"unidade": str(unidade.pk), "delegacao": str(del1.pk)},
    )
    assert resp1.status_code == 200
    del1.refresh_from_db()
    assert del1.data_fim == hoje

    resp2 = client.post(
        reverse("competencias:revogar_delegacao"),
        {"unidade": str(unidade.pk), "delegacao": str(del2.pk)},
    )
    assert resp2.status_code == 200
    assert not Delegacao.objects.filter(pk=del2.pk).exists()


@banco
@pytest.mark.django_db
def test_substituto_do_titular_delega_durante_impedimento(client: Client) -> None:
    from apps.competencias.models.delegacao import Delegacao

    unidade = _unidade("DEL-SUBST-UNIDADE")
    titular = _dirigente(unidade, "910480", "Titular Impedido")
    substituto = _perfil(unidade, "910481", "Substituto do Titular")
    servidor = _perfil(unidade, "910482", "Servidor Designado")
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao = _atribuir(unidade, acao)

    _cobrir(substituto, titular)

    client.force_login(substituto)
    hoje = timezone.localdate()
    resposta = client.post(
        reverse("competencias:delegar_servidor"),
        {
            "unidade": str(unidade.pk),
            "atribuicao": str(atribuicao.pk),
            "delegado": str(servidor.pk),
            "data_inicio": hoje.isoformat(),
        },
    )

    assert resposta.status_code == 200
    assert Delegacao.objects.filter(
        unidade=unidade,
        acao=acao,
        delegante=substituto,
        delegado=servidor,
    ).exists()


@banco
@pytest.mark.django_db
def test_delegacao_registra_operacoes_distintas(client: Client) -> None:
    from apps.competencias.models.delegacao import Delegacao

    unidade = _unidade("DEL-REG-UNIDADE")
    titular = _dirigente(unidade, "910490", "Dirigente Registro")
    delegado = _perfil(unidade, "910491", "Delegado Registro")
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao = _atribuir(unidade, acao)

    client.force_login(titular)
    hoje = timezone.localdate()

    resp_delegar = client.post(
        reverse("competencias:delegar_servidor"),
        {
            "unidade": str(unidade.pk),
            "atribuicao": str(atribuicao.pk),
            "delegado": str(delegado.pk),
            "data_inicio": hoje.isoformat(),
        },
    )
    assert resp_delegar.status_code == 200

    del_criada = Delegacao.objects.get(
        unidade=unidade, acao=acao, delegado=delegado
    )

    resp_revogar = client.post(
        reverse("competencias:revogar_delegacao"),
        {"unidade": str(unidade.pk), "delegacao": str(del_criada.pk)},
    )
    assert resp_revogar.status_code == 200

    registros = {
        execucao.operacao: execucao
        for execucao in ExecucaoAcao.objects.filter(
            autorizado=True, perfil_id=titular.pk, alvo_tipo="acao_servidor"
        )
    }
    assert "delegar" in registros
    assert "revogar" in registros

    assert registros["delegar"].alvo_identificador == f"{acao.slug}:{delegado.rf}"
    assert registros["revogar"].alvo_identificador == f"{acao.slug}:{delegado.rf}"


# ---------------------------------------------------------------------------
# SPEC autorizacao/009 — Delegação nominal de competência estrutural: Segurança da ação
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_anonimo_vai_ao_login_sem_registrar(client: Client) -> None:
    unidade = _unidade("DEL-ANON-UNIDADE")
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao = _atribuir(unidade, acao)

    resp_delegar = client.post(
        reverse("competencias:delegar_servidor"),
        {"unidade": str(unidade.pk), "atribuicao": str(atribuicao.pk)},
    )
    assert resp_delegar.status_code == 302
    assert "/login" in resp_delegar["Location"]

    resp_revogar = client.post(
        reverse("competencias:revogar_delegacao"),
        {"unidade": str(unidade.pk), "delegacao": "1"},
    )
    assert resp_revogar.status_code == 302
    assert "/login" in resp_revogar["Location"]

    assert ExecucaoAcao.objects.count() == 0


@banco
@pytest.mark.django_db
def test_sem_competencia_recebe_403_registrado(client: Client) -> None:
    unidade = _unidade("DEL-SEM-COMP-UNIDADE")
    sem_direcao = _perfil(unidade, "910500", "Sem Direcao")
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao = _atribuir(unidade, acao)

    client.force_login(sem_direcao)
    resposta = client.post(
        reverse("competencias:delegar_servidor"),
        {
            "unidade": str(unidade.pk),
            "atribuicao": str(atribuicao.pk),
            "delegado": str(sem_direcao.pk),
            "data_inicio": timezone.localdate().isoformat(),
        },
    )

    assert resposta.status_code == 403
    assert ExecucaoAcao.objects.filter(
        autorizado=False, perfil_id=sem_direcao.pk
    ).exists()


@banco
@pytest.mark.django_db
def test_delegado_nao_re_delega_estrutural(client: Client) -> None:
    unidade = _unidade("DEL-RE-DEL-UNIDADE")
    titular = _dirigente(unidade, "910510", "Titular ReDel")
    delegado = _perfil(unidade, "910511", "Delegado ReDel")
    terceiro = _perfil(unidade, "910512", "Terceiro ReDel")
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao = _atribuir(unidade, acao)

    _delegar(atribuicao, delegante=titular, delegado=delegado)

    client.force_login(delegado)
    resposta = client.post(
        reverse("competencias:delegar_servidor"),
        {
            "unidade": str(unidade.pk),
            "atribuicao": str(atribuicao.pk),
            "delegado": str(terceiro.pk),
            "data_inicio": timezone.localdate().isoformat(),
        },
    )

    assert resposta.status_code == 403
    assert ExecucaoAcao.objects.filter(
        autorizado=False, perfil_id=delegado.pk
    ).exists()


@banco
@pytest.mark.django_db
def test_delegado_nao_revoga_delegacao_de_outrem(client: Client) -> None:
    unidade = _unidade("DEL-REV-OUTREM-UNID")
    titular = _dirigente(unidade, "910520", "Titular RevOutrem")
    delegado1 = _perfil(unidade, "910521", "Delegado 1 RevOutrem")
    delegado2 = _perfil(unidade, "910522", "Delegado 2 RevOutrem")
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao = _atribuir(unidade, acao)

    _delegar(atribuicao, delegante=titular, delegado=delegado1)
    del2 = _delegar(atribuicao, delegante=titular, delegado=delegado2)

    client.force_login(delegado1)
    resposta = client.post(
        reverse("competencias:revogar_delegacao"),
        {"unidade": str(unidade.pk), "delegacao": str(del2.pk)},
    )

    assert resposta.status_code == 403
    assert ExecucaoAcao.objects.filter(
        autorizado=False, perfil_id=delegado1.pk
    ).exists()


@banco
@pytest.mark.django_db
def test_delegado_fora_do_exercicio_nao_exerce(client: Client) -> None:
    unidade = _unidade("DEL-EXERC-UNIDADE")
    titular = _dirigente(unidade, "910530", "Titular Exerc")
    delegado_impedido = _perfil(unidade, "910531", "Delegado Imp")
    delegado_exonerado = _perfil(
        unidade, "910532", "Delegado Exon", is_active=False, exonerado_em=timezone.localdate()
    )
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao = _atribuir(unidade, acao)
    acao_teste = _acao("competencias.acao_teste_exerc", estrutural=False)

    _delegar(atribuicao, delegante=titular, delegado=delegado_impedido)
    _delegar(atribuicao, delegante=titular, delegado=delegado_exonerado)

    tipo_imp, _ = TipoImpedimento.objects.get_or_create(nome="Licenca Delegado")
    registrar_impedimento(
        delegado_impedido,
        NovoImpedimento(
            tipo=tipo_imp.pk,
            data_inicio=timezone.localdate() - timedelta(days=1),
            data_fim=None,
        ),
    )

    client.force_login(delegado_impedido)
    resp_imp = client.post(
        reverse("competencias:atribuir"),
        {"unidade": str(unidade.pk), "acao": acao_teste.slug},
    )
    assert resp_imp.status_code == 403
    assert ExecucaoAcao.objects.filter(
        autorizado=False, perfil_id=delegado_impedido.pk
    ).exists()

    client.force_login(delegado_exonerado)
    resp_exon = client.post(
        reverse("competencias:atribuir"),
        {"unidade": str(unidade.pk), "acao": acao_teste.slug},
    )
    assert resp_exon.status_code == 302
    assert "/login" in resp_exon["Location"]


@banco
@pytest.mark.django_db
def test_delegado_nao_alcanca_unidade_superior(client: Client) -> None:
    raiz = _unidade("DEL-SUP-RAIZ")
    filha = _unidade("DEL-SUP-FILHA", pai=raiz)

    titular_filha = _dirigente(filha, "910540", "Titular Filha")
    delegado = _perfil(filha, "910541", "Delegado Filha")
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao_filha = _atribuir(filha, acao)
    acao_teste = _acao("competencias.acao_teste_sup", estrutural=False)

    _delegar(atribuicao_filha, delegante=titular_filha, delegado=delegado)

    client.force_login(delegado)
    resposta = client.post(
        reverse("competencias:atribuir"),
        {"unidade": str(raiz.pk), "acao": acao_teste.slug},
    )

    assert resposta.status_code == 403
    assert ExecucaoAcao.objects.filter(
        autorizado=False, perfil_id=delegado.pk
    ).exists()


@banco
@pytest.mark.django_db
def test_delegado_nao_alcanca_ramo_irmao(client: Client) -> None:
    raiz = _unidade("DEL-IRM-RAIZ")
    filha1 = _unidade("DEL-IRM-FILHA1", pai=raiz)
    filha2 = _unidade("DEL-IRM-FILHA2", pai=raiz)

    titular_filha1 = _dirigente(filha1, "910550", "Titular Filha 1")
    delegado = _perfil(filha1, "910551", "Delegado Filha 1")
    acao = _acao("competencias.definir_atribuicao", estrutural=True)
    atribuicao1 = _atribuir(filha1, acao)
    acao_teste = _acao("competencias.acao_teste_irm", estrutural=False)

    _delegar(atribuicao1, delegante=titular_filha1, delegado=delegado)

    client.force_login(delegado)
    resposta = client.post(
        reverse("competencias:atribuir"),
        {"unidade": str(filha2.pk), "acao": acao_teste.slug},
    )

    assert resposta.status_code == 403
    assert ExecucaoAcao.objects.filter(
        autorizado=False, perfil_id=delegado.pk
    ).exists()


@banco
@pytest.mark.django_db
def test_acao_inativa_nao_libera_delegado(client: Client) -> None:
    unidade = _unidade("DEL-INAT-UNIDADE")
    titular = _dirigente(unidade, "910560", "Titular Inativa")
    delegado = _perfil(unidade, "910561", "Delegado Inativa")
    acao = _acao("competencias.definir_atribuicao", estrutural=True, ativa=False)
    atribuicao = _atribuir(unidade, acao)
    acao_teste = _acao("competencias.acao_teste_inat", estrutural=False)

    _delegar(atribuicao, delegante=titular, delegado=delegado)

    fresco = Perfil.objects.get(pk=delegado.pk)
    assert not fresco.has_perm(acao.slug)

    client.force_login(delegado)
    resposta = client.post(
        reverse("competencias:atribuir"),
        {"unidade": str(unidade.pk), "acao": acao_teste.slug},
    )
    assert resposta.status_code == 403


@banco
@pytest.mark.django_db
def test_cartao_estrutural_bloqueado_para_quem_nao_dirige(client: Client) -> None:
    unidade = _unidade("DEL-CARD-UNIDADE")
    titular = _dirigente(unidade, "910570", "Titular Card")
    servidor_comum = _perfil(unidade, "910571", "Servidor Comum Card")
    acao_estrutural = _acao("competencias.definir_atribuicao", estrutural=True)
    acao_conceder = _acao("competencias.conceder", estrutural=True)
    atribuicao = _atribuir(unidade, acao_estrutural)
    atr_conceder = _atribuir(unidade, acao_conceder)

    _delegar(atribuicao, delegante=titular, delegado=servidor_comum)
    _delegar(atr_conceder, delegante=titular, delegado=servidor_comum)

    client.force_login(servidor_comum)
    resposta = client.get(
        reverse("competencias:painel_concessoes"),
        {"unidade": str(unidade.pk)},
    )
    assert resposta.status_code == 200
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")

    assert soup.find(string=lambda t: bool(t) and "Estrutural" in t) is not None

    assert soup.find(class_="lata-concessao") is None
    assert soup.find(class_="btn-delegar") is None or "modal-delegar" not in str(soup)


@banco
@pytest.mark.django_db
def test_escrita_so_por_post(client: Client) -> None:
    unidade = _unidade("DEL-POST-UNIDADE")
    titular = _dirigente(unidade, "910580", "Titular Post")

    client.force_login(titular)

    resp_delegar = client.get(reverse("competencias:delegar_servidor"))
    assert resp_delegar.status_code == 405

    resp_revogar = client.get(reverse("competencias:revogar_delegacao"))
    assert resp_revogar.status_code == 405

