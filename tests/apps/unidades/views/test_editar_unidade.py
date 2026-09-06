"""
Testes de apps/unidades/views.py — `editar_unidade` e `gravar_edicao_unidade` (SPEC user_admin/020):
editar unidade é ação estrutural cujo alvo é a própria unidade editada; o destino da transferência
NÃO é conferido contra o alcance (Caveats) — quem transfere pode deixar de administrar a unidade, e
o que protege isso é a confirmação em tela mais o ato registrado. Raiz é quem nasce raiz: nenhuma
tela torna raiz uma unidade que tem superior, nem para o superusuário.

Os itens da bateria de segurança comuns às duas ações estruturais de unidade moram em
test_acoes_declaradas.py.

Todos levam o marker `banco`: direção, alcance e execução são lidos e gravados no banco.
"""

from bs4 import BeautifulSoup, Tag
from django.test import Client
from django.urls import reverse

import pytest

from apps.competencias.models import ExecucaoAcao
from apps.unidades.models import CorUnidade, TipoUnidade, Unidade
from apps.cargos.models import CargoBase, CargoComissao
from apps.user_admin.models import Perfil
from apps.unidades.titularidade import definir_titular

banco = pytest.mark.banco

SLUG_ACAO = "unidades.editar_unidade"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Tipo Editar Unidade",
        "nivel": 20,
        "pode_ser_raiz": True,
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
    dados: dict[str, object] = {"nome": "Cargo Editar Unidade", "sigla": "CGEU"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _cargo_chefia(nome: str) -> CargoComissao:
    return CargoComissao.objects.create(nome=nome, sigla="CDA", nivel=1, e_chefia=True)


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Editar Unidade",
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
        unidade=_unidade(f"EU-SU-{rf}"),
        cargo_base=_cargo_base(),
    )


def _fresco(perfil: Perfil) -> Perfil:
    return Perfil.objects.get(pk=perfil.pk)


def _url_abrir(unidade_id: int) -> str:
    return reverse("unidades:editar_unidade", kwargs={"unidade": unidade_id})


def _url_gravar(unidade_id: int) -> str:
    return reverse("unidades:gravar_edicao_unidade", kwargs={"unidade": unidade_id})


def _payload(
    pai: Unidade | None,
    tipo: TipoUnidade,
    nome: str,
    sigla: str,
    cor: str = CorUnidade.AGUA_700,
    confirmar: bool = False,
) -> dict[str, str]:
    payload = {
        "pai": str(pai.pk) if pai is not None else "",
        "nome": nome,
        "sigla": sigla,
        "tipo": str(tipo.pk),
        "cor": str(cor),
    }
    if confirmar:
        payload["confirmar_transferencia"] = "1"
    return payload


def _controle(soup: BeautifulSoup, tag: str, nome: str) -> Tag:
    controle = soup.find(tag, attrs={"name": nome})
    assert isinstance(controle, Tag), f"a tela não trouxe o {tag} de {nome}"
    return controle


# ---------------------------------------------------------------------------
# Raiz é quem nasce raiz — nenhuma tela torna raiz, nem para o superusuário
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_tornar_raiz_e_recusado_para_todos(client: Client) -> None:
    raiz = _unidade("EU-RAIZ", nivel=30)
    tipo_filho = _tipo_unidade(
        nome="Tipo Filho Raiz Editar", nivel=10, pode_ser_raiz=False
    )
    filha = Unidade.objects.create(
        nome="Filha Raiz Editar", sigla="EU-RAIZ-FILHA", tipo=tipo_filho, pai=raiz
    )
    dirigente = _dirigente(raiz, "9601000")

    client.force_login(dirigente)
    resposta = client.post(
        _url_gravar(filha.pk),
        _payload(pai=None, tipo=tipo_filho, nome=filha.nome, sigla=filha.sigla),
    )
    html = resposta.content.decode()

    assert resposta.status_code == 422
    assert "Unidade com superior não vira raiz" in html
    filha.refresh_from_db()
    assert filha.pai_id == raiz.pk

    # Nem o superusuário torna raiz uma unidade que já tem superior.
    superusuario = _superusuario("9601010")
    client.force_login(superusuario)
    resposta_su = client.post(
        _url_gravar(filha.pk),
        _payload(pai=None, tipo=tipo_filho, nome=filha.nome, sigla=filha.sigla),
    )
    assert resposta_su.status_code == 422
    filha.refresh_from_db()
    assert filha.pai_id == raiz.pk


# ---------------------------------------------------------------------------
# Transferência: confirmação antes de gravar, e o registro que a distingue
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_troca_de_pai_pede_confirmacao_sem_gravar(client: Client) -> None:
    raiz = _unidade("EU-TROCA-RAIZ", nivel=30)
    origem = _unidade("EU-TROCA-ORIGEM", nivel=20, pai=raiz)
    destino = _unidade("EU-TROCA-DESTINO", nivel=20, pai=raiz)
    tipo_filho = _tipo_unidade(nome="Tipo Filho Troca", nivel=10, pode_ser_raiz=False)
    unidade = Unidade.objects.create(
        nome="Unidade Trocada", sigla="EU-TROCA-UNI", tipo=tipo_filho, pai=origem
    )
    dirigente = _dirigente(raiz, "9601100")

    client.force_login(dirigente)
    resposta = client.post(
        _url_gravar(unidade.pk),
        _payload(pai=destino, tipo=tipo_filho, nome=unidade.nome, sigla=unidade.sigla),
    )
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 200
    assert "campo-realce-alerta" in _controle(soup, "select", "pai")["class"]
    assert "Confirmar transferência" in html
    unidade.refresh_from_db()
    assert unidade.pai_id == origem.pk


@banco
@pytest.mark.django_db
def test_transferencia_confirmada_grava_e_registra_como_transferir(
    client: Client,
) -> None:
    raiz = _unidade("EU-CONF-RAIZ", nivel=30)
    origem = _unidade("EU-CONF-ORIGEM", nivel=20, pai=raiz)
    destino = _unidade("EU-CONF-DESTINO", nivel=20, pai=raiz)
    tipo_filho = _tipo_unidade(
        nome="Tipo Filho Confirmação", nivel=10, pode_ser_raiz=False
    )
    unidade = Unidade.objects.create(
        nome="Unidade Confirmada", sigla="EU-CONF-UNI", tipo=tipo_filho, pai=origem
    )
    dirigente = _dirigente(raiz, "9601200")

    client.force_login(dirigente)
    resposta = client.post(
        _url_gravar(unidade.pk),
        _payload(
            pai=destino,
            tipo=tipo_filho,
            nome=unidade.nome,
            sigla=unidade.sigla,
            confirmar=True,
        ),
    )

    assert resposta.status_code == 200
    unidade.refresh_from_db()
    assert unidade.pai_id == destino.pk
    execucao = ExecucaoAcao.objects.get(alvo_identificador=unidade.sigla)
    assert execucao.operacao == "transferir"


@banco
@pytest.mark.django_db
def test_edicao_sem_troca_de_pai_grava_sem_confirmacao(client: Client) -> None:
    raiz = _unidade("EU-SEMTROCA-RAIZ", nivel=30)
    tipo_filho = _tipo_unidade(
        nome="Tipo Filho Sem Troca", nivel=10, pode_ser_raiz=False
    )
    unidade = Unidade.objects.create(
        nome="Unidade Antiga",
        sigla="EU-SEMTROCA-UNI",
        tipo=tipo_filho,
        pai=raiz,
        cor=CorUnidade.AGUA_700,
    )
    dirigente = _dirigente(raiz, "9601300")

    client.force_login(dirigente)
    resposta = client.post(
        _url_gravar(unidade.pk),
        _payload(
            pai=raiz,
            tipo=tipo_filho,
            nome="Unidade Renomeada",
            sigla=unidade.sigla,
            cor=CorUnidade.SAKURA_600,
        ),
    )

    assert resposta.status_code == 200
    unidade.refresh_from_db()
    assert unidade.nome == "Unidade Renomeada"
    assert unidade.cor == CorUnidade.SAKURA_600
    execucao = ExecucaoAcao.objects.get(alvo_identificador=unidade.sigla)
    assert execucao.operacao == "editar"


@banco
@pytest.mark.django_db
def test_recusa_vence_a_confirmacao(client: Client) -> None:
    raiz = _unidade("EU-VENCE-RAIZ", nivel=30)
    origem = _unidade("EU-VENCE-ORIGEM", nivel=20, pai=raiz)
    # Nível baixo demais para subordinar a unidade que será movida (nível 10): a hierarquia recusa
    # antes de qualquer confirmação ser oferecida.
    destino_baixo = _unidade("EU-VENCE-DESTINO", nivel=5, pai=raiz)
    tipo_filho = _tipo_unidade(nome="Tipo Filho Vence", nivel=10, pode_ser_raiz=False)
    unidade = Unidade.objects.create(
        nome="Unidade Vence", sigla="EU-VENCE-UNI", tipo=tipo_filho, pai=origem
    )
    dirigente = _dirigente(raiz, "9601400")

    client.force_login(dirigente)
    resposta = client.post(
        _url_gravar(unidade.pk),
        _payload(
            pai=destino_baixo, tipo=tipo_filho, nome=unidade.nome, sigla=unidade.sigla
        ),
    )
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 422
    assert "campo-realce-erro" in _controle(soup, "select", "pai")["class"]
    assert "Confirmar transferência" not in html
    unidade.refresh_from_db()
    assert unidade.pai_id == origem.pk


# ---------------------------------------------------------------------------
# O alcance no alvo: unidade fora do ramo é recusada, abrir e gravar
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_editar_unidade_fora_do_alcance_e_403_registrado(client: Client) -> None:
    dirigida = _unidade("EU-ALC-DIRIGIDA")
    fora = _unidade("EU-ALC-FORA")
    dirigente = _dirigente(dirigida, "9601500")

    client.force_login(dirigente)
    resposta_abrir = client.get(_url_abrir(fora.pk))
    assert resposta_abrir.status_code == 403

    resposta_gravar = client.post(
        _url_gravar(fora.pk),
        _payload(pai=None, tipo=fora.tipo, nome=fora.nome, sigla=fora.sigla),
    )
    assert resposta_gravar.status_code == 403
    # Abrir e gravar são duas conferências de alvo, e cada uma deixa a própria linha (§2).
    negadas = ExecucaoAcao.objects.filter(autorizado=False)
    assert negadas.count() == 2
    assert all(execucao.perfil_id == dirigente.pk for execucao in negadas)
