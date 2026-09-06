"""
Testes de apps/unidades/views.py e apps/unidades/extincao.py — o ato de extinguir e reativar
unidade (SPEC user_admin/025).

Extinguir e reativar são UMA competência com DUAS operações (Caveats da SPEC): a barreira é a
mesma, o alcance é o mesmo, e o que as distingue no histórico é a `operacao` gravada. O alcance é
`UnidadesEstritamenteSubordinadas` — o ramo abaixo, SEM as unidades de onde ele parte: ninguém
extingue nem reativa a unidade que dirige.

Todos levam o marker `banco`: hierarquia, competência, alcance e execução são lidos e gravados no
banco.
"""

from datetime import timedelta

from bs4 import BeautifulSoup
from bs4.element import Tag
from django.test import Client
from django.urls import reverse
from django.utils import timezone

import pytest

from apps.competencias.models import (
    Acao,
    AtribuicaoUnidade,
    Concessao,
    Delegacao,
    ExecucaoAcao,
)
from apps.unidades.models import TipoUnidade, Unidade
from apps.unidades.titularidade import definir_titular
from apps.user_admin.exercicio import designar_substituto, registrar_impedimento
from apps.cargos.models import CargoBase, CargoComissao
from apps.user_admin.models import Perfil, TipoImpedimento
from apps.user_admin.schemas import NovaSubstituicao, NovoImpedimento

banco = pytest.mark.banco

SLUG_ACAO = "unidades.extinguir_unidade"

# Quatro degraus porque o alcance estrito exige três — raiz, a unidade DIRIGIDA de onde ele parte,
# e o alvo abaixo dela — e o alvo ainda precisa poder ter subordinada própria a transferir.
NIVEL_RAIZ = 40
NIVEL_DIRIGIDA = 30
NIVEL_ALVO = 20
NIVEL_FILHA = 10


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(nome: str, nivel: int, **overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": nome,
        "nivel": nivel,
        "pode_ser_raiz": nivel == NIVEL_RAIZ,
        "nivel_minimo_titular": 1,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(sigla: str, nivel: int = NIVEL_ALVO, **overrides: object) -> Unidade:
    dados: dict[str, object] = {
        "nome": f"Unidade {sigla}",
        "sigla": sigla,
        "tipo": _tipo_unidade(f"Tipo {sigla}", nivel),
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base(**overrides: object) -> CargoBase:
    dados: dict[str, object] = {"nome": "Cargo Extinção", "sigla": "CGEX"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _cargo_chefia(nome: str) -> CargoComissao:
    return CargoComissao.objects.create(nome=nome, sigla="CDA", nivel=1, e_chefia=True)


def _perfil(
    unidade: Unidade, rf: str, nome: str = "Servidor", **overrides: object
) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Extinção",
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


def _superusuario(rf: str) -> Perfil:
    return Perfil.objects.create_superuser(
        rf=rf,
        nome="Super",
        sobrenome="Usuário",
        password="segredo123",
        unidade=_unidade(f"EX-SU-{rf}", NIVEL_RAIZ),
        cargo_base=_cargo_base(),
    )


def _acao(slug: str, **overrides: object) -> Acao:
    dados: dict[str, object] = {"nome": f"Ação {slug}", "tooltip": "tt", "ativa": True}
    dados.update(overrides)
    acao, _ = Acao.objects.get_or_create(slug=slug, defaults=dados)  # type: ignore[arg-type]
    return acao


def _atribuir(unidade: Unidade, acao: Acao) -> AtribuicaoUnidade:
    return AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)


def _conceder(atribuicao: AtribuicaoUnidade, cargo: CargoBase) -> Concessao:
    return Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo)


def _cobrir(substituto: Perfil, titular: Perfil) -> None:
    """Afasta o titular e põe o substituto no lugar (SPEC user_admin/015)."""
    tipo, _ = TipoImpedimento.objects.get_or_create(nome="Licença Extinção")
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


def _impedir(perfil: Perfil) -> None:
    tipo, _ = TipoImpedimento.objects.get_or_create(nome="Licença Extinção")
    registrar_impedimento(
        perfil,
        NovoImpedimento(
            tipo=tipo.pk,
            data_inicio=timezone.localdate() - timedelta(days=1),
            data_fim=None,
        ),
    )


# ---------------------------------------------------------------------------
# Helpers de rota e de leitura da resposta
# ---------------------------------------------------------------------------


def _url_painel() -> str:
    return reverse("unidades:painel_unidades")


def _url_modal() -> str:
    return reverse("unidades:extinguir_unidade")


def _url_previa() -> str:
    return reverse("unidades:previa_do_ato")


def _url_extinguir() -> str:
    return reverse("unidades:gravar_extincao_unidade")


def _url_reativar() -> str:
    return reverse("unidades:gravar_reativacao_unidade")


def _url_pagina(unidade: Unidade) -> str:
    return reverse("unidades:pagina_unidade", kwargs={"pk": unidade.pk})


def _sopa(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _siglas_no_select(soup: BeautifulSoup, nome: str = "unidade") -> set[str]:
    select = soup.find("select", attrs={"name": nome})
    if not isinstance(select, Tag):
        return set()
    return {
        opcao.get_text(strip=True).split("·")[0].strip()
        for opcao in select.find_all("option")
        if opcao.get("value")
    }


def _negativas(slug: str = SLUG_ACAO) -> int:
    return ExecucaoAcao.objects.filter(acao__slug=slug, autorizado=False).count()


def _extinguir_pelo_ato(client: Client, autor: Perfil, alvo: Unidade) -> None:
    """Arranjo que passa pelo ATO, e não pelo campo: as competências precisam cair com a data do
    dia para que a reativação tenha o que restaurar."""
    client.force_login(autor)
    resposta = client.post(_url_extinguir(), {"unidade": str(alvo.pk)})
    assert resposta.status_code == 200, "o arranjo da extinção não passou"


# ---------------------------------------------------------------------------
# Cenário-base: raiz → ramo dirigido → alvo, que é o que o alcance estrito pede
# ---------------------------------------------------------------------------


def _ramo(prefixo: str) -> tuple[Unidade, Unidade, Unidade]:
    """Raiz, a unidade DIRIGIDA de onde o alcance parte, e o alvo abaixo dela. O alvo é sempre o
    NETO: filho da dirigida seria alcançável, mas a dirigida em si nunca é — é dela que o alcance
    parte, e o alcance estrito a exclui."""
    raiz = _unidade(f"{prefixo}-RAIZ", NIVEL_RAIZ)
    dirigida = _unidade(f"{prefixo}-DIR", NIVEL_DIRIGIDA, pai=raiz)
    alvo = _unidade(f"{prefixo}-ALVO", NIVEL_ALVO, pai=dirigida)
    return raiz, dirigida, alvo


# ---------------------------------------------------------------------------
# Comportamento do ato — o que a extinção move e o que ela derruba
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_extincao_transfere_servidores_e_filhas_para_o_pai(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-TRANSF")
    filha = _unidade("EX-TRANSF-FILHA", NIVEL_FILHA, pai=alvo)
    dirigente = _dirigente(dirigida, "9700000")
    titular_do_alvo = _dirigente(alvo, "9700001", nome="Titular do Alvo")
    comum = _perfil(alvo, "9700002", nome="Comum")

    client.force_login(dirigente)
    resposta = client.post(_url_extinguir(), {"unidade": str(alvo.pk)})

    assert resposta.status_code == 200
    alvo.refresh_from_db()
    assert alvo.extinta_em == timezone.localdate()

    filha.refresh_from_db()
    assert filha.pai_id == dirigida.pk

    titular_do_alvo.refresh_from_db()
    comum.refresh_from_db()
    assert titular_do_alvo.unidade_id == dirigida.pk
    assert comum.unidade_id == dirigida.pk
    # O titular chega ao destino como servidor comum: a unicidade de um titular por unidade
    # barraria o segundo marcado lá.
    assert titular_do_alvo.e_titular is False

    # A resposta é o painel inteiro, já sem a unidade.
    html = resposta.content.decode()
    assert "painel-unidades" in html
    assert alvo.sigla not in html


@banco
@pytest.mark.django_db
def test_extincao_extingue_atribuicoes_e_concessoes(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-COMP")
    dirigente = _dirigente(dirigida, "9700100")
    cargo = _cargo_base(nome="Cargo Competência Extinta", sigla="CGCE")
    beneficiado = _perfil(alvo, "9700101", nome="Beneficiado", cargo_base=cargo)
    atribuicao = _atribuir(alvo, _acao("competencias.definir_atribuicao"))
    concessao = _conceder(atribuicao, cargo)

    assert beneficiado.has_perm("competencias.definir_atribuicao")

    client.force_login(dirigente)
    client.post(_url_extinguir(), {"unidade": str(alvo.pk)})

    hoje = timezone.localdate()
    atribuicao.refresh_from_db()
    concessao.refresh_from_db()
    assert atribuicao.extinta_em == hoje
    assert concessao.extinta_em == hoje

    # Competência de unidade extinta não é competência de ninguém — e `has_perm` cacheia no
    # objeto, então quem responde precisa vir fresco do banco.
    assert not Perfil.objects.get(pk=beneficiado.pk).has_perm(
        "competencias.definir_atribuicao"
    )


@banco
@pytest.mark.django_db
def test_delegacoes_da_extinta_sao_encerradas(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-DELEG")
    dirigente = _dirigente(dirigida, "9700200")
    delegado = _perfil(alvo, "9700201", nome="Delegado")
    hoje = timezone.localdate()
    acao = _acao("unidades.editar_unidade")

    vigente = Delegacao.objects.create(
        acao=acao,
        unidade=alvo,
        delegante=dirigente,
        delegado=delegado,
        data_inicio=hoje - timedelta(days=5),
        data_fim=None,
    )
    futura = Delegacao.objects.create(
        acao=acao,
        unidade=alvo,
        delegante=dirigente,
        delegado=delegado,
        data_inicio=hoje + timedelta(days=5),
        data_fim=None,
    )

    client.force_login(dirigente)
    client.post(_url_extinguir(), {"unidade": str(alvo.pk)})

    vigente.refresh_from_db()
    assert vigente.data_fim == hoje
    # A que nunca vigorou é apagada: encerrar antes do início é recusado pelo CheckConstraint.
    assert not Delegacao.objects.filter(pk=futura.pk).exists()


@banco
@pytest.mark.django_db
def test_extincao_recusa_por_inteiro(client: Client) -> None:
    raiz, dirigida, alvo = _ramo("EX-RECUSA")
    dirigente = _dirigente(dirigida, "9700300")

    # A raiz não se extingue — nem para o superusuário, e a barreira é do banco.
    superusuario = _superusuario("9700301")
    client.force_login(superusuario)
    resposta_raiz = client.post(_url_extinguir(), {"unidade": str(raiz.pk)})
    assert resposta_raiz.status_code == 422
    assert "não se extingue" in resposta_raiz.content.decode()
    raiz.refresh_from_db()
    assert raiz.extinta_em is None

    # Subordinada que o destino não admite por tipo vedado: o ato inteiro é recusado, sem mover
    # nem servidor, nem filha, nem competência.
    tipo_filha = _tipo_unidade("Tipo Filha Vedada", NIVEL_FILHA, pode_ser_raiz=False)
    dirigida.tipo.tipos_filhos_vedados.add(tipo_filha)
    filha = Unidade.objects.create(
        nome="Unidade Filha Vedada",
        sigla="EX-RECUSA-FILHA",
        tipo=tipo_filha,
        pai=alvo,
    )
    lotado = _perfil(alvo, "9700302", nome="Lotado")
    atribuicao = _atribuir(alvo, _acao("competencias.conceder"))

    client.force_login(dirigente)
    resposta = client.post(_url_extinguir(), {"unidade": str(alvo.pk)})

    assert resposta.status_code == 422
    assert "não admite filhas deste tipo" in resposta.content.decode()
    alvo.refresh_from_db()
    filha.refresh_from_db()
    lotado.refresh_from_db()
    atribuicao.refresh_from_db()
    assert alvo.extinta_em is None
    assert filha.pai_id == alvo.pk
    assert lotado.unidade_id == alvo.pk
    assert atribuicao.extinta_em is None


@banco
@pytest.mark.django_db
def test_extinta_some_da_listagem_ate_o_toggle_revela(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-TOGGLE")
    dirigente = _dirigente(dirigida, "9700400")
    _extinguir_pelo_ato(client, dirigente, alvo)

    desligado = _sopa(client.get(_url_painel()).content.decode())
    assert alvo.sigla not in desligado.get_text()

    ligado = client.get(_url_painel(), {"extintas": "1"})
    html = ligado.content.decode()
    assert alvo.sigla in html
    assert "Extinta" in html
    # Sem a lixeira: gesto de unidade viva não se oferece a unidade extinta.
    linha = _sopa(ligado.content.decode()).find("tr", class_="linha-extinta")
    assert isinstance(linha, Tag)
    assert linha.select_one("[data-abrir-modal]") is None

    # Nunca nos selects, com o toggle ligado ou desligado.
    cadastro = _sopa(client.get(reverse("unidades:criar_unidade")).content.decode())
    assert alvo.sigla not in _siglas_no_select(cadastro, "pai")

    # E o estado do toggle sobrevive à filtragem seguinte.
    filtrado = client.get(_url_painel(), {"extintas": "1", "sigla": alvo.sigla})
    assert alvo.sigla in filtrado.content.decode()


@banco
@pytest.mark.django_db
def test_extinta_nao_recebe_lotacao_nem_como_superusuario(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-LOTA")
    dirigente = _dirigente(dirigida, "9700500")
    servidor = _perfil(dirigida, "9700501", nome="Servidor Lotado")
    _extinguir_pelo_ato(client, dirigente, alvo)

    superusuario = _superusuario("9700502")
    client.force_login(superusuario)

    # Criar: o POST nomeia a extinta e é recusado, sem criar perfil.
    antes = Perfil.objects.count()
    resposta_criar = client.post(
        reverse("user_admin:gravar_servidor"),
        {
            "rf": "9700503",
            "nome": "Novo",
            "sobrenome": "Servidor",
            "email": "novo.servidor@prefeitura.sp.gov.br",
            "unidade": str(alvo.pk),
            "cargo_base": str(_cargo_base().pk),
        },
    )
    assert resposta_criar.status_code == 422
    assert "extinta" in resposta_criar.content.decode().lower()
    assert Perfil.objects.count() == antes

    # Editar: a lotação não muda.
    resposta_editar = client.post(
        reverse("user_admin:gravar_edicao", kwargs={"servidor": servidor.pk}),
        {
            "rf": servidor.rf,
            "nome": servidor.nome,
            "sobrenome": servidor.sobrenome,
            "email": servidor.email,
            "unidade": str(alvo.pk),
            "cargo_base": str(servidor.cargo_base_id),
        },
    )
    assert resposta_editar.status_code == 422
    servidor.refresh_from_db()
    assert servidor.unidade_id == dirigida.pk


@banco
@pytest.mark.django_db
def test_extinta_nao_recebe_competencia_nova(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-COMPNOVA")
    dirigente = _dirigente(dirigida, "9700600")
    cargo = _cargo_base(nome="Cargo Competência Nova", sigla="CGCN")
    beneficiado = _perfil(dirigida, "9700601", nome="Beneficiado", cargo_base=cargo)
    acao = _acao("competencias.conceder")
    atribuicao = _atribuir(alvo, acao)
    _extinguir_pelo_ato(client, dirigente, alvo)

    superusuario = _superusuario("9700602")
    client.force_login(superusuario)

    resposta_atribuir = client.post(
        reverse("competencias:atribuir"),
        {"unidade": str(alvo.pk), "acao": acao.slug},
    )
    assert resposta_atribuir.status_code == 404
    assert (
        AtribuicaoUnidade.objects.filter(unidade=alvo, extinta_em__isnull=True).count()
        == 0
    )

    atribuicao.refresh_from_db()
    resposta_conceder = client.post(
        reverse("competencias:conceder_cargo"),
        {
            "unidade": str(alvo.pk),
            "atribuicao": str(atribuicao.pk),
            "cargo_base": str(cargo.pk),
        },
    )
    assert resposta_conceder.status_code == 404
    assert Concessao.objects.filter(atribuicao=atribuicao).count() == 0
    assert not Perfil.objects.get(pk=beneficiado.pk).has_perm(acao.slug)


# ---------------------------------------------------------------------------
# As duas faces do modal, e a reativação
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_modal_abre_com_previa_e_select_recortado(client: Client) -> None:
    raiz, dirigida, alvo = _ramo("EX-MODAL")
    _unidade("EX-MODAL-IRMA", NIVEL_ALVO, pai=dirigida)
    _unidade("EX-MODAL-FILHA", NIVEL_FILHA, pai=alvo)
    dirigente = _dirigente(dirigida, "9700700")
    _perfil(alvo, "9700701", nome="Um")
    _perfil(alvo, "9700702", nome="Dois")

    client.force_login(dirigente)
    resposta = client.get(_url_modal(), {"unidade": str(alvo.pk)})
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "2" in html and "Servidores" in html
    assert "Subordinadas" in html
    # Para qual sigla vai o que ela carrega.
    assert dirigida.sigla in html

    siglas = _siglas_no_select(_sopa(resposta.content.decode()))
    # O ramo abaixo da dirigida, sem ela e sem a raiz: ninguém extingue a unidade que dirige.
    assert alvo.sigla in siglas
    assert "EX-MODAL-IRMA" in siglas
    assert dirigida.sigla not in siglas
    assert raiz.sigla not in siglas


@banco
@pytest.mark.django_db
def test_face_do_modal_segue_o_estado_da_unidade(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-FACE")
    dirigente = _dirigente(dirigida, "9700800")
    _atribuir(alvo, _acao("competencias.conceder"))

    client.force_login(dirigente)
    vigente = client.get(_url_modal(), {"unidade": str(alvo.pk)}).content.decode()
    assert "Extinguir unidade" in vigente
    assert "Reativar" not in vigente

    _extinguir_pelo_ato(client, dirigente, alvo)

    extinta = client.get(_url_modal(), {"unidade": str(alvo.pk)}).content.decode()
    assert "Reativar unidade" in extinta
    # A contagem do que volta é a da face de reativação.
    assert "Atribuições" in extinta
    assert "Concessões" in extinta


@banco
@pytest.mark.django_db
def test_reativacao_devolve_unidade_e_as_competencias_que_cairam(
    client: Client,
) -> None:
    _, dirigida, alvo = _ramo("EX-REATIVA")
    filha = _unidade("EX-REATIVA-FILHA", NIVEL_FILHA, pai=alvo)
    dirigente = _dirigente(dirigida, "9700900")
    cargo = _cargo_base(nome="Cargo Reativação", sigla="CGRE")
    beneficiado = _perfil(dirigida, "9700901", nome="Beneficiado", cargo_base=cargo)
    lotado = _perfil(alvo, "9700902", nome="Lotado")

    acao = _acao("competencias.conceder")
    atribuicao = _atribuir(alvo, acao)
    _conceder(atribuicao, cargo)
    # Retirada por ato PRÓPRIO antes da extinção: apagar é o que retirar faz, e o que não existe
    # mais não é recriado pela volta.
    retirada = _atribuir(alvo, _acao("unidades.editar_unidade"))
    retirada.delete()

    _extinguir_pelo_ato(client, dirigente, alvo)

    resposta = client.post(_url_reativar(), {"unidade": str(alvo.pk)})
    assert resposta.status_code == 200

    alvo.refresh_from_db()
    assert alvo.extinta_em is None
    assert alvo.sigla in client.get(_url_painel()).content.decode()
    assert alvo.sigla in _siglas_no_select(
        _sopa(client.get(reverse("unidades:criar_unidade")).content.decode()), "pai"
    )

    atribuicao.refresh_from_db()
    assert atribuicao.extinta_em is None
    assert (
        Concessao.objects.filter(atribuicao=atribuicao, extinta_em__isnull=True).count()
        == 1
    )
    # A concessão é da UNIDADE (SPEC autorizacao/002): quem exerce precisa estar lotado nela. Como
    # servidor não volta sozinho (Caveats da SPEC), o arranjo relota à mão — só então a concessão
    # restaurada tem quem a exerça.
    beneficiado.unidade = alvo
    beneficiado.save(update_fields=["unidade"])
    assert Perfil.objects.get(pk=beneficiado.pk).has_perm(acao.slug)
    assert AtribuicaoUnidade.objects.filter(unidade=alvo).count() == 1

    # Servidores e subordinadas NÃO voltam: refazem-se à mão.
    filha.refresh_from_db()
    lotado.refresh_from_db()
    assert filha.pai_id == dirigida.pk
    assert lotado.unidade_id == dirigida.pk


@banco
@pytest.mark.django_db
def test_reativacao_recusa_por_inteiro(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-REC-REATIVA")
    dirigente = _dirigente(dirigida, "9701000")

    # Reativar unidade que não está extinta.
    client.force_login(dirigente)
    vigente = client.post(_url_reativar(), {"unidade": str(alvo.pk)})
    assert vigente.status_code == 422
    assert "não está extinta" in vigente.content.decode()

    # Reativar unidade cuja superior está extinta: a recusa NOMEIA a sigla a reativar primeiro.
    neto = _unidade("EX-REC-NETO", NIVEL_FILHA, pai=alvo)
    _extinguir_pelo_ato(client, dirigente, neto)
    _extinguir_pelo_ato(client, dirigente, alvo)

    resposta = client.post(_url_reativar(), {"unidade": str(neto.pk)})
    assert resposta.status_code == 422
    assert alvo.sigla in resposta.content.decode()
    neto.refresh_from_db()
    assert neto.extinta_em is not None


@banco
@pytest.mark.django_db
def test_extincao_nao_reponta_filha_ja_extinta(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-CADEIA")
    filha = _unidade("EX-CADEIA-FILHA", NIVEL_FILHA, pai=alvo)
    dirigente = _dirigente(dirigida, "9701100")

    _extinguir_pelo_ato(client, dirigente, filha)
    _extinguir_pelo_ato(client, dirigente, alvo)

    # A subordinada JÁ extinta não sobe: o `pai` dela é a memória de onde ela volta.
    filha.refresh_from_db()
    assert filha.pai_id == alvo.pk

    recusa = client.post(_url_reativar(), {"unidade": str(filha.pk)})
    assert recusa.status_code == 422
    assert alvo.sigla in recusa.content.decode()

    # Na ordem certa, as duas voltam.
    assert client.post(_url_reativar(), {"unidade": str(alvo.pk)}).status_code == 200
    assert client.post(_url_reativar(), {"unidade": str(filha.pk)}).status_code == 200
    alvo.refresh_from_db()
    filha.refresh_from_db()
    assert alvo.extinta_em is None
    assert filha.extinta_em is None
    assert filha.pai_id == alvo.pk


@banco
@pytest.mark.django_db
def test_pagina_da_extinta_oferece_so_reativar(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-PAGINA")
    dirigente = _dirigente(dirigida, "9701200")
    _extinguir_pelo_ato(client, dirigente, alvo)

    resposta = client.get(_url_pagina(alvo))
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "Extinta" in html
    assert timezone.localdate().strftime("%d/%m/%Y") in html
    assert "Reativar unidade" in html
    assert "Editar unidade" not in html
    assert "Designar substituto" not in html

    client.post(_url_reativar(), {"unidade": str(alvo.pk)})
    depois = client.get(_url_pagina(alvo)).content.decode()
    assert "Reativar unidade" not in depois
    assert "Editar unidade" in depois


# ---------------------------------------------------------------------------
# Segurança da ação (skill `acao-administrativa`) — a barreira e o rastro
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_anonimo_vai_ao_login_sem_registrar(client: Client) -> None:
    _, _, alvo = _ramo("EX-ANON")

    for url in (_url_extinguir(), _url_reativar()):
        resposta = client.post(url, {"unidade": str(alvo.pk)})
        assert resposta.status_code == 302
        assert "/login" in resposta["Location"]

    # Anônimo não deixa linha: sem perfil não há autor, cargo nem unidade a gravar.
    assert ExecucaoAcao.objects.filter(acao__slug=SLUG_ACAO).count() == 0
    alvo.refresh_from_db()
    assert alvo.extinta_em is None


@banco
@pytest.mark.django_db
def test_sem_competencia_recebe_403_registrado(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-SEMCOMP")
    comum = _perfil(dirigida, "9701300", nome="Comum")

    client.force_login(comum)
    resposta = client.post(_url_extinguir(), {"unidade": str(alvo.pk)})

    assert resposta.status_code == 403
    assert _negativas() == 1
    alvo.refresh_from_db()
    assert alvo.extinta_em is None


@banco
@pytest.mark.django_db
def test_quem_dirige_pratica_sem_concessao_gravada(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-DIRIGE")
    dirigente = _dirigente(dirigida, "9701400")
    assert not AtribuicaoUnidade.objects.filter(acao__slug=SLUG_ACAO).exists()

    client.force_login(dirigente)
    assert client.post(_url_extinguir(), {"unidade": str(alvo.pk)}).status_code == 200
    assert client.post(_url_reativar(), {"unidade": str(alvo.pk)}).status_code == 200

    # Quem não dirige e não tem concessão, não pratica.
    de_fora = _perfil(dirigida, "9701401", nome="De Fora")
    client.force_login(de_fora)
    assert client.post(_url_extinguir(), {"unidade": str(alvo.pk)}).status_code == 403


@banco
@pytest.mark.django_db
def test_propria_unidade_dirigida_e_recusada(client: Client) -> None:
    _, dirigida, _alvo = _ramo("EX-PROPRIA")
    dirigente = _dirigente(dirigida, "9701500")

    client.force_login(dirigente)
    resposta = client.post(_url_extinguir(), {"unidade": str(dirigida.pk)})
    assert resposta.status_code == 403

    dirigida.extinta_em = timezone.localdate()
    dirigida.save(update_fields=["extinta_em"])
    assert (
        client.post(_url_reativar(), {"unidade": str(dirigida.pk)}).status_code == 403
    )
    assert _negativas() == 2

    # E o botão dela não é renderizado na tabela.
    dirigida.extinta_em = None
    dirigida.save(update_fields=["extinta_em"])
    linhas = _sopa(client.get(_url_painel()).content.decode()).find_all("tr")
    da_dirigida = [linha for linha in linhas if dirigida.sigla in linha.get_text()]
    assert da_dirigida
    assert all(linha.select_one("[data-abrir-modal]") is None for linha in da_dirigida)


@banco
@pytest.mark.django_db
def test_alvo_de_outro_ramo_e_recusado(client: Client) -> None:
    _, dirigida, _alvo = _ramo("EX-RAMO-A")
    _, _, alheio = _ramo("EX-RAMO-B")
    dirigente = _dirigente(dirigida, "9701600")

    client.force_login(dirigente)
    resposta = client.post(_url_extinguir(), {"unidade": str(alheio.pk)})

    assert resposta.status_code == 403
    assert _negativas() == 1
    alheio.refresh_from_db()
    assert alheio.extinta_em is None


@banco
@pytest.mark.django_db
def test_post_sem_o_parametro_do_alvo_e_400(client: Client) -> None:
    _, dirigida, _alvo = _ramo("EX-SEM-ALVO")
    dirigente = _dirigente(dirigida, "9701700")

    client.force_login(dirigente)
    resposta = client.post(_url_extinguir(), {})

    assert resposta.status_code == 400
    # Falta de parâmetro não é negativa de competência: nada a registrar.
    assert _negativas() == 0


@banco
@pytest.mark.django_db
def test_impedido_recebe_403_e_exonerado_302(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-IMPED")
    dirigente = _dirigente(dirigida, "9701800")
    _impedir(dirigente)

    client.force_login(dirigente)
    assert client.post(_url_extinguir(), {"unidade": str(alvo.pk)}).status_code == 403
    assert _negativas() == 1

    _, outra_dirigida, outro_alvo = _ramo("EX-EXON")
    exonerado = _dirigente(outra_dirigida, "9701801")
    client.force_login(exonerado)
    exonerado.is_active = False
    exonerado.exonerado_em = timezone.localdate()
    exonerado.save(update_fields=["is_active", "exonerado_em"])

    resposta = client.post(_url_extinguir(), {"unidade": str(outro_alvo.pk)})
    assert resposta.status_code == 302
    # Exonerado chega como anônimo: não há negativa a gravar.
    assert _negativas() == 1


@banco
@pytest.mark.django_db
def test_substituto_pratica_durante_a_cobertura(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-SUBST")
    titular = _dirigente(dirigida, "9701900", nome="Titular")
    _, outra, _ = _ramo("EX-SUBST-OUTRA")
    substituto = _perfil(outra, "9701901", nome="Substituto")
    _cobrir(substituto, titular)

    client.force_login(substituto)
    resposta = client.post(_url_extinguir(), {"unidade": str(alvo.pk)})

    assert resposta.status_code == 200
    execucao = ExecucaoAcao.objects.get(acao__slug=SLUG_ACAO, autorizado=True)
    assert execucao.perfil_id == substituto.pk
    assert execucao.substituindo_id == titular.pk


@banco
@pytest.mark.django_db
def test_ato_grava_quem_cargo_unidade_operacao_e_alvo(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-REGISTRO")
    dirigente = _dirigente(dirigida, "9702000")

    client.force_login(dirigente)
    client.post(_url_extinguir(), {"unidade": str(alvo.pk)})

    execucao = ExecucaoAcao.objects.get(acao__slug=SLUG_ACAO, autorizado=True)
    assert execucao.perfil_id == dirigente.pk
    assert execucao.unidade_id == dirigida.pk
    assert execucao.cargo_base_id == dirigente.cargo_base_id
    assert execucao.cargo_comissao_id == dirigente.cargo_comissao_id
    assert execucao.operacao == "extinguir"
    assert execucao.alvo_tipo == "unidade"
    assert execucao.alvo_identificador == alvo.sigla

    # Mudar a lotação depois não reescreve a linha.
    _, nova_unidade, _ = _ramo("EX-REG-NOVA")
    dirigente.unidade = nova_unidade
    dirigente.e_titular = False
    dirigente.save(update_fields=["unidade", "e_titular"])
    execucao.refresh_from_db()
    assert execucao.unidade_id == dirigida.pk


@banco
@pytest.mark.django_db
def test_extinguir_e_reativar_sao_distinguiveis_no_historico(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-HIST")
    dirigente = _dirigente(dirigida, "9702100")

    client.force_login(dirigente)
    client.post(_url_extinguir(), {"unidade": str(alvo.pk)})
    client.post(_url_reativar(), {"unidade": str(alvo.pk)})

    operacoes = list(
        ExecucaoAcao.objects.filter(acao__slug=SLUG_ACAO, autorizado=True)
        .order_by("momento")
        .values_list("operacao", flat=True)
    )
    # Uma ação só, duas operações: é a `operacao` que as separa no rastro.
    assert operacoes == ["extinguir", "reativar"]
    assert (
        ExecucaoAcao.objects.filter(acao__slug=SLUG_ACAO)
        .values("acao")
        .distinct()
        .count()
        == 1
    )


@banco
@pytest.mark.django_db
def test_historico_da_extinta_continua_integro(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-HIST-INT")
    dirigente = _dirigente(dirigida, "9702200")
    lotado = _dirigente(alvo, "9702201", nome="Lotado no Alvo")

    # Um ato praticado NA unidade, antes de ela ser extinta.
    anterior = ExecucaoAcao.objects.create(
        acao=_acao("unidades.editar_unidade"),
        perfil=lotado,
        unidade=alvo,
        cargo_base=lotado.cargo_base,
        cargo_comissao=lotado.cargo_comissao,
        autorizado=True,
        operacao="editar",
        alvo_tipo="unidade",
        alvo_identificador=alvo.sigla,
    )

    _extinguir_pelo_ato(client, dirigente, alvo)

    anterior.refresh_from_db()
    assert anterior.unidade_id == alvo.pk
    # A travessia de FK continua devolvendo a extinta: é o `base_manager_name = "todas"`.
    assert anterior.unidade.sigla == alvo.sigla


@banco
@pytest.mark.django_db
def test_leitura_autorizada_nao_vira_linha(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-LEITURA")
    dirigente = _dirigente(dirigida, "9702300")

    client.force_login(dirigente)
    client.get(_url_painel())
    client.get(_url_modal(), {"unidade": str(alvo.pk)})
    client.get(_url_previa(), {"unidade": str(alvo.pk)})
    assert ExecucaoAcao.objects.filter(acao__slug=SLUG_ACAO).count() == 0

    # O mesmo GET negado, sim: a negativa é o que o registro existe para guardar.
    comum = _perfil(dirigida, "9702301", nome="Comum")
    client.force_login(comum)
    assert client.get(_url_modal(), {"unidade": str(alvo.pk)}).status_code == 403
    assert _negativas() == 1


@banco
@pytest.mark.django_db
def test_escrita_so_por_post(client: Client) -> None:
    _, dirigida, alvo = _ramo("EX-METODO")
    dirigente = _dirigente(dirigida, "9702400")

    client.force_login(dirigente)
    for url in (_url_extinguir(), _url_reativar()):
        assert client.get(url, {"unidade": str(alvo.pk)}).status_code == 405

    alvo.refresh_from_db()
    assert alvo.extinta_em is None
