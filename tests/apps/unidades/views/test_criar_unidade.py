"""
Testes de apps/unidades/views.py — `criar_unidade` e `gravar_unidade` (SPEC user_admin/020): criar
unidade é ação estrutural cujo alvo é a unidade SUPERIOR escolhida (`pai`), e quem responde pela
direção dela cria abaixo sem concessão gravada. A recusa do model volta no próprio formulário
realçada, e o painel embutido nas telas de servidor grava e devolve a unidade já selecionada.

Os itens da bateria de segurança comuns às duas ações estruturais de unidade (anônimo, autenticado
sem competência e o alcance irrestrito do superusuário) moram em test_acoes_declaradas.py; a ação
de criar unidade RAIZ, exclusiva do superusuário, mora em test_criar_unidade_raiz.py.

Todos levam o marker `banco`: direção, concessão e execução são lidas e gravadas no banco.
"""

from bs4 import BeautifulSoup, Tag
from django.test import Client
from django.urls import reverse

import pytest

from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao, ExecucaoAcao
from apps.user_admin.exercicio import designar_substituto, registrar_impedimento
from apps.unidades.models import CorUnidade, TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, CargoComissao, Perfil, TipoImpedimento
from apps.user_admin.schemas import NovaSubstituicao, NovoImpedimento
from apps.unidades.titularidade import definir_titular
from datetime import timedelta

from django.conf import settings as django_settings
from django.utils import timezone

banco = pytest.mark.banco

SLUG_ACAO = "unidades.criar_unidade"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Tipo Criar Unidade",
        "nivel": 20,
        "pode_ser_raiz": True,
        "nivel_minimo_titular": 1,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _tipo_filho(**overrides: object) -> TipoUnidade:
    # Nível baixo e sem exigência de ser raiz: o tipo que a nova unidade recebe ao ser criada
    # abaixo do pai escolhido nos testes.
    dados: dict[str, object] = {
        "nome": "Tipo Filho Criar Unidade",
        "nivel": 10,
        "pode_ser_raiz": False,
        "nivel_minimo_titular": 1,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(sigla: str, nivel: int = 20, **overrides: object) -> Unidade:
    dados: dict[str, object] = {
        "nome": f"Unidade {sigla}",
        "sigla": sigla,
        "tipo": _tipo_unidade(nome=f"Tipo {sigla}", nivel=nivel),
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base(**overrides: object) -> CargoBase:
    dados: dict[str, object] = {"nome": "Cargo Criar Unidade", "sigla": "CGCU"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _cargo_chefia(nome: str) -> CargoComissao:
    return CargoComissao.objects.create(nome=nome, sigla="CDA", nivel=1, e_chefia=True)


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Criar Unidade",
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


def _cobrir(substituto: Perfil, titular: Perfil) -> None:
    tipo, _ = TipoImpedimento.objects.get_or_create(nome="Licença Criar Unidade")
    hoje = timezone.localdate()
    impedimento = registrar_impedimento(
        titular,
        NovoImpedimento(
            tipo=tipo.pk, data_inicio=hoje - timedelta(days=1), data_fim=None
        ),
    )
    designar_substituto(
        impedimento,
        NovaSubstituicao(substituto=substituto.pk, data_inicio=hoje, data_fim=None),
    )


def _conceder(unidade: Unidade, cargo_base: CargoBase) -> Acao:
    acao, _ = Acao.objects.get_or_create(
        slug=SLUG_ACAO,
        defaults={"nome": "Cadastrar unidade", "tooltip": "tt", "estrutural": True},
    )
    atribuicao = AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)
    Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo_base)
    return acao


def _superusuario(rf: str) -> Perfil:
    return Perfil.objects.create_superuser(
        rf=rf,
        nome="Super",
        sobrenome="Usuário",
        password="segredo123",
        unidade=_unidade(f"CU-SU-{rf}"),
        cargo_base=_cargo_base(),
    )


def _fresco(perfil: Perfil) -> Perfil:
    return Perfil.objects.get(pk=perfil.pk)


def _url_form() -> str:
    return reverse("unidades:criar_unidade")


def _url_gravar() -> str:
    return reverse("unidades:gravar_unidade")


def _payload(
    pai: Unidade | None, tipo: TipoUnidade, sigla: str, nome: str | None = None
) -> dict[str, str]:
    return {
        "pai": str(pai.pk) if pai is not None else "",
        "nome": nome or f"Unidade {sigla}",
        "sigla": sigla,
        "tipo": str(tipo.pk),
        "cor": str(CorUnidade.AGUA_700),
    }


def _controle(soup: BeautifulSoup, tag: str, nome: str) -> Tag:
    controle = soup.find(tag, attrs={"name": nome})
    assert isinstance(controle, Tag), f"a tela não trouxe o {tag} de {nome}"
    return controle


# ---------------------------------------------------------------------------
# A gravação cria a unidade abaixo da escolhida
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_gravar_cria_a_unidade_abaixo_da_escolhida(client: Client) -> None:
    pai = _unidade("CU-PAI")
    tipo_filho = _tipo_filho()
    dirigente = _dirigente(pai, "9501000")

    client.force_login(dirigente)
    resposta = client.post(_url_gravar(), _payload(pai, tipo_filho, "CU-FILHA"))
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "CU-FILHA" in html
    nova = Unidade.objects.get(sigla="CU-FILHA")
    assert nova.pai_id == pai.pk
    assert nova.tipo_id == tipo_filho.pk


# ---------------------------------------------------------------------------
# Recusa do model: volta no formulário, realçada, sem gravar
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_recusa_do_model_volta_no_formulario_realcada(client: Client) -> None:
    pai = _unidade("CU-NIVEL")
    # Mesmo nível do pai: a hierarquia recusa, porque o tipo escolhido não subordina.
    tipo_mesmo_nivel = _tipo_filho(nome="Tipo Mesmo Nível", nivel=20)
    dirigente = _dirigente(pai, "9501100")

    client.force_login(dirigente)
    resposta = client.post(
        _url_gravar(), _payload(pai, tipo_mesmo_nivel, "CU-NIVEL-FILHA")
    )
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 422
    assert "A unidade pai precisa ser de um tipo de nível superior." in html
    assert "campo-realce-erro" in _controle(soup, "select", "pai")["class"]
    assert not Unidade.objects.filter(sigla="CU-NIVEL-FILHA").exists()


# ---------------------------------------------------------------------------
# O tom fora da paleta é recusado no controle de cor
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_tom_fora_da_paleta_e_recusado_no_controle_cor(client: Client) -> None:
    pai = _unidade("CU-COR")
    tipo_filho = _tipo_filho(nome="Tipo Cor Criar Unidade")
    dirigente = _dirigente(pai, "9501300")

    client.force_login(dirigente)
    payload = _payload(pai, tipo_filho, "CU-COR-FILHA")
    payload["cor"] = "cor-inventada-000"
    resposta = client.post(_url_gravar(), payload)
    html = resposta.content.decode()

    assert resposta.status_code == 422
    assert "Cor: escolha uma opção da lista." in html
    assert not Unidade.objects.filter(sigla="CU-COR-FILHA").exists()


# ---------------------------------------------------------------------------
# O painel embutido grava e devolve a unidade já selecionada na lotação
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_criacao_no_painel_devolve_o_campo_de_lotacao_com_a_unidade_nova(
    client: Client,
) -> None:
    pai = _unidade("CU-PAINEL")
    tipo_filho = _tipo_filho(nome="Tipo Painel Criar Unidade")
    dirigente = _dirigente(pai, "9501200")

    client.force_login(dirigente)
    resposta = client.post(
        reverse("unidades:gravar_unidade_e_selecionar"),
        _payload(pai, tipo_filho, "CU-PAINEL-NOVA"),
    )
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 200
    assert 'id="campo-unidade-lotacao"' in html
    nova = Unidade.objects.get(sigla="CU-PAINEL-NOVA")
    selecionada = soup.find("option", attrs={"value": str(nova.pk)})
    assert isinstance(selecionada, Tag)
    assert selecionada.has_attr("selected")


# ---------------------------------------------------------------------------
# Estrutural × concessão em outra unidade
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_estrutural_libera_quem_dirige_sem_concessao(client: Client) -> None:
    unidade = _unidade("CU-ESTR")
    titular = _dirigente(unidade, "9501600", "Titular Estrutural")
    outra = _unidade("CU-ESTR-OUTRA")
    substituto = _perfil(outra, "9501610", "Substituto Estrutural")

    client.force_login(titular)
    assert client.get(_url_form()).status_code == 200

    _cobrir(substituto, titular)
    client.force_login(_fresco(substituto))
    assert client.get(_url_form()).status_code == 200

    client.force_login(_fresco(titular))
    assert client.get(_url_form()).status_code == 403


@banco
@pytest.mark.django_db
def test_concessao_em_outra_unidade_nao_libera(client: Client) -> None:
    superior = _unidade("CU-CONC-SUP")
    subordinada = _unidade("CU-CONC-SUB", nivel=10, pai=superior)
    cargo = _cargo_base(nome="Cargo Concessão Alheia Unidade", sigla="CCAU")
    perfil = _perfil(subordinada, "9501500", "Concessão Alheia", cargo_base=cargo)
    # A mesma ação, concedida ao mesmo cargo — mas na unidade superior, não na do perfil.
    _conceder(superior, cargo)

    client.force_login(perfil)
    assert client.get(_url_form()).status_code == 403


# ---------------------------------------------------------------------------
# Fora de exercício não exerce, ainda que dirija no papel
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_perfil_fora_de_exercicio_nao_exerce(client: Client) -> None:
    impedido = _dirigente(_unidade("CU-IMPEDIDO"), "9501900", "Titular Impedido")
    tipo, _ = TipoImpedimento.objects.get_or_create(
        nome="Licença Sem Cobertura Criar Unidade"
    )
    registrar_impedimento(
        impedido,
        NovoImpedimento(
            tipo=tipo.pk,
            data_inicio=timezone.localdate() - timedelta(days=1),
            data_fim=None,
        ),
    )
    client.force_login(_fresco(impedido))
    assert client.get(_url_form()).status_code == 403

    exonerado = _dirigente(_unidade("CU-EXONERADO"), "9501910", "Titular Exonerado")
    exonerado.is_active = False
    exonerado.exonerado_em = timezone.localdate()
    exonerado.save(update_fields=["is_active", "exonerado_em"])
    client.force_login(exonerado)
    resposta = client.get(_url_form())
    assert resposta.status_code == 302
    assert resposta["Location"].startswith(str(django_settings.LOGIN_URL))


# ---------------------------------------------------------------------------
# O alcance no POST: alvo (pai) fora do ramo, e o parâmetro obrigatório
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_criar_com_pai_fora_do_alcance_e_403_registrado(client: Client) -> None:
    dirigida = _unidade("CU-ALC-DIRIGIDA")
    fora = _unidade("CU-ALC-FORA")
    tipo_filho = _tipo_filho(nome="Tipo Alcance Fora Criar Unidade")
    dirigente = _dirigente(dirigida, "9502000")

    client.force_login(dirigente)
    resposta = client.post(
        _url_gravar(), _payload(fora, tipo_filho, "CU-ALC-FORA-FILHA")
    )

    assert resposta.status_code == 403
    assert not Unidade.objects.filter(sigla="CU-ALC-FORA-FILHA").exists()


@banco
@pytest.mark.django_db
def test_criar_sem_o_parametro_pai_e_400(client: Client) -> None:
    dirigida = _unidade("CU-400")
    tipo_filho = _tipo_filho(nome="Tipo 400 Criar Unidade")
    dirigente = _dirigente(dirigida, "9502100")
    payload = _payload(dirigida, tipo_filho, "CU-400-FILHA")
    del payload["pai"]

    client.force_login(dirigente)
    antes = ExecucaoAcao.objects.count()
    resposta = client.post(_url_gravar(), payload)

    assert resposta.status_code == 400
    assert ExecucaoAcao.objects.count() == antes
    assert not Unidade.objects.filter(sigla="CU-400-FILHA").exists()


# ---------------------------------------------------------------------------
# Ação inativa não libera ninguém, mesmo com concessão gravada
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_acao_inativa_nao_libera_ninguem(client: Client) -> None:
    unidade = _unidade("CU-INATIVA")
    cargo = _cargo_base(nome="Cargo Concessão Inativa Unidade", sigla="CCIU")
    perfil = _perfil(unidade, "9502200", "Concessão Sem Direção", cargo_base=cargo)
    acao = _conceder(unidade, cargo)

    client.force_login(perfil)
    assert client.get(_url_form()).status_code == 200

    acao.ativa = False
    acao.save(update_fields=["ativa"])
    client.force_login(_fresco(perfil))
    assert client.get(_url_form()).status_code == 403


# ---------------------------------------------------------------------------
# O que fica registrado: lotação do momento e distinção leitura × escrita
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_execucao_registrada_com_o_cargo_e_a_unidade_do_momento(client: Client) -> None:
    origem = _unidade("CU-REG-ORIGEM")
    destino = _unidade("CU-REG-DESTINO")
    tipo_filho = _tipo_filho(nome="Tipo Registro Criar Unidade")
    dirigente = _dirigente(origem, "9502300")

    client.force_login(dirigente)
    resposta = client.post(_url_gravar(), _payload(origem, tipo_filho, "CU-REG-FILHA"))
    assert resposta.status_code == 200

    execucao = ExecucaoAcao.objects.get(
        operacao="criar", alvo_identificador="CU-REG-FILHA"
    )
    assert execucao.perfil_id == dirigente.pk
    assert execucao.unidade_id == origem.pk
    assert execucao.alvo_tipo == "unidade"

    dirigente.unidade = destino
    dirigente.save(update_fields=["unidade"])
    execucao.refresh_from_db()
    assert execucao.unidade_id == origem.pk


@banco
@pytest.mark.django_db
def test_leitura_autorizada_nao_vira_registro(client: Client) -> None:
    unidade = _unidade("CU-LEITURA")
    outra = _unidade("CU-LEITURA-OUTRA")
    dirigente = _dirigente(unidade, "9502400")
    sem_competencia = _perfil(outra, "9502410", "Sem Competência Leitura")

    client.force_login(dirigente)
    assert client.get(_url_form()).status_code == 200
    assert ExecucaoAcao.objects.count() == 0

    client.force_login(sem_competencia)
    assert client.get(_url_form()).status_code == 403
    assert ExecucaoAcao.objects.count() == 1


# ---------------------------------------------------------------------------
# Gravação só por POST
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_gravacao_so_por_post(client: Client) -> None:
    pai = _unidade("CU-SOPOST")
    dirigente = _dirigente(pai, "9502500")

    client.force_login(dirigente)
    resposta = client.get(_url_gravar(), {"pai": str(pai.pk)})

    assert resposta.status_code == 405
    assert ExecucaoAcao.objects.count() == 0
