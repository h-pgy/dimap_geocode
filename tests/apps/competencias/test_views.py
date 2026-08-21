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

from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao, ExecucaoAcao
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
def test_menu_administrador_mostra_a_acao_so_para_quem_pode(client: Client) -> None:
    # Importados aqui, e não no topo: ACAO_CONCEDER ainda não existe no regime `testes_tdd: true` —
    # isolar o import mantém o resto do módulo (SPEC 007, já implementada) coletável e verde.
    from apps.competencias.acoes_declaradas import ACAO_CONCEDER
    from apps.competencias.menus import MontagemMenu, RoteadorMenu
    from apps.competencias.menus_declarados import MENU_ADMINISTRADOR
    from apps.competencias.resolucao import slugs_liberados

    unidade = _unidade("CONC-MENU-UNIDADE")
    outra = _unidade("CONC-MENU-OUTRA")
    dirigente = _dirigente(unidade, "910320")
    sem_direcao = _perfil(outra, "910321", "Sem Direção Menu Concessão")

    roteador = RoteadorMenu()
    resolvido_dirigente = roteador(
        MontagemMenu(menu=MENU_ADMINISTRADOR, slugs_liberados=slugs_liberados(dirigente))
    )
    resolvido_sem_direcao = roteador(
        MontagemMenu(menu=MENU_ADMINISTRADOR, slugs_liberados=slugs_liberados(sem_direcao))
    )

    assert ACAO_CONCEDER.acao.slug in {item.slug for item in resolvido_dirigente.itens}
    assert ACAO_CONCEDER.acao.slug not in {item.slug for item in resolvido_sem_direcao.itens}
