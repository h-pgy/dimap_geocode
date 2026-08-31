"""
Testes de apps/user_admin/views.py — `modal_exonerar_servidor`, `gravar_exoneracao` e
`gravar_reintegracao` (SPEC user_admin/027): exonerar e reintegrar servidor viram ato
administrativo, sob uma competência só, com duas operações — mesmo regime de
`registrar_impedimento`/`retornar_ao_exercicio` (SPEC user_admin/023).

A ação é estrutural e o alcance é `LotacaoDoServidor`: a unidade a conferir é a lotação do
servidor-alvo, lida no banco a partir do id que vem no caminho da rota — nunca do corpo. O
comportamento dos atos em si (o que `exonerar_servidor` e `reintegrar_servidor` gravam) é
`tests/apps/user_admin/test_exoneracao.py`; aqui ficam o contrato HTTP das rotas e a bateria de
segurança da skill `acao-administrativa`.

Todos levam o marker `banco`: direção, alcance, exoneração e execução são lidos e gravados no banco.
"""

from django.conf import settings as django_settings
from django.test import Client
from django.urls import reverse
from django.utils import timezone

import pytest

from apps.competencias.models import AtribuicaoUnidade, Concessao, ExecucaoAcao
from apps.unidades.models import TipoUnidade, Unidade
from apps.unidades.titularidade import definir_titular
from apps.user_admin.exercicio import registrar_impedimento
from apps.user_admin.models import CargoBase, CargoComissao, Perfil, TipoImpedimento
from apps.user_admin.schemas import NovoImpedimento

banco = pytest.mark.banco


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Rota Exoneração",
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
    dados: dict[str, object] = {"nome": "Cargo Rota Exoneração", "sigla": "CGRE"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _cargo_chefia(nome: str) -> CargoComissao:
    return CargoComissao.objects.create(nome=nome, sigla="CDA", nivel=1, e_chefia=True)


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Rota Exoneração",
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


def _impedir(perfil: Perfil) -> None:
    tipo, _ = TipoImpedimento.objects.get_or_create(nome="Licença Rota Exoneração")
    registrar_impedimento(
        perfil,
        NovoImpedimento(tipo=tipo.pk, data_inicio=timezone.localdate(), data_fim=None),
    )


def _fresco(perfil: Perfil) -> Perfil:
    # O cache de `has_perm` é do objeto Python: cada requisição simulada precisa ver o efeito de
    # uma mudança de estado como uma requisição nova veria.
    return Perfil.objects.get(pk=perfil.pk)


def _url_modal() -> str:
    return reverse("user_admin:modal_exonerar_servidor")


def _url_gravar_exonerar(servidor_id: int) -> str:
    return reverse("user_admin:gravar_exoneracao", kwargs={"servidor": servidor_id})


def _url_gravar_reintegrar(servidor_id: int) -> str:
    return reverse("user_admin:gravar_reintegracao", kwargs={"servidor": servidor_id})


# ---------------------------------------------------------------------------
# Barreira de autenticação e de competência
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_anonimo_vai_ao_login_sem_registrar(client: Client) -> None:
    alvo = _perfil(_unidade("EXO-ANON"), "9900000", "Alvo Anônimo")

    resposta = client.post(_url_gravar_exonerar(alvo.pk))

    assert resposta.status_code == 302
    assert resposta["Location"].startswith(str(django_settings.LOGIN_URL))
    assert ExecucaoAcao.objects.count() == 0
    assert _fresco(alvo).is_active is True


@banco
@pytest.mark.django_db
def test_autenticado_sem_competencia_recebe_403_e_fica_registrado(
    client: Client,
) -> None:
    unidade = _unidade("EXO-403")
    comum = _perfil(unidade, "9900100", "Sem Competência")
    alvo = _perfil(unidade, "9900110", "Alvo 403")

    client.force_login(comum)
    resposta = client.post(_url_gravar_exonerar(alvo.pk))

    assert resposta.status_code == 403
    execucao = ExecucaoAcao.objects.get()
    assert execucao.autorizado is False
    assert _fresco(alvo).is_active is True


@banco
@pytest.mark.django_db
def test_dirigente_de_outro_ramo_recebe_403(client: Client) -> None:
    dirigida = _unidade("EXO-RAMO-DIRIGIDA")
    fora = _unidade("EXO-RAMO-FORA")
    dirigente = _dirigente(dirigida, "9900200")
    de_fora = _perfil(fora, "9900210", "Alvo De Fora")

    client.force_login(_fresco(dirigente))
    resposta = client.post(_url_gravar_exonerar(de_fora.pk))

    assert resposta.status_code == 403
    assert ExecucaoAcao.objects.filter(autorizado=False).count() == 1
    assert _fresco(de_fora).is_active is True


@banco
@pytest.mark.django_db
def test_estrutural_dispensa_concessao_gravada(client: Client) -> None:
    unidade = _unidade("EXO-ESTR")
    dirigente = _dirigente(unidade, "9900300")
    alvo = _perfil(unidade, "9900310", "Alvo Estrutural")
    de_fora = _perfil(unidade, "9900320", "De Fora Estrutural")
    outro_alvo = _perfil(unidade, "9900330", "Outro Alvo Estrutural")

    client.force_login(_fresco(dirigente))
    resposta = client.post(_url_gravar_exonerar(alvo.pk))

    assert resposta.status_code == 200
    # Dirigir basta: nada foi atribuído à unidade nem concedido a cargo algum.
    assert AtribuicaoUnidade.objects.count() == 0
    assert Concessao.objects.count() == 0

    # Quem não dirige e não tem concessão, não pratica.
    client.force_login(_fresco(de_fora))
    resposta_negada = client.post(_url_gravar_exonerar(outro_alvo.pk))
    assert resposta_negada.status_code == 403


@banco
@pytest.mark.django_db
def test_impedido_recebe_403_e_exonerado_302(client: Client) -> None:
    """Os dois desfechos são diferentes de propósito: o impedido segue autenticado e o `has_perm`
    o nega; o exonerado (`is_active=False`) o Django nem autentica, e ele chega como anônimo."""
    unidade = _unidade("EXO-IMPED")
    impedido = _dirigente(unidade, "9900400", "Titular Impedido")
    alvo = _perfil(unidade, "9900410", "Alvo Fora")
    _impedir(impedido)

    client.force_login(_fresco(impedido))
    resposta = client.post(_url_gravar_exonerar(alvo.pk))
    assert resposta.status_code == 403
    negativas = ExecucaoAcao.objects.filter(autorizado=False).count()

    exonerado = _dirigente(_unidade("EXO-EXON"), "9900420", "Titular Exonerado")
    exonerado.is_active = False
    exonerado.exonerado_em = timezone.localdate()
    exonerado.save(update_fields=["is_active", "exonerado_em"])

    client.force_login(exonerado)
    resposta_exonerado = client.post(_url_gravar_exonerar(alvo.pk))

    assert resposta_exonerado.status_code == 302
    assert resposta_exonerado["Location"].startswith(str(django_settings.LOGIN_URL))
    assert ExecucaoAcao.objects.filter(autorizado=False).count() == negativas
    assert _fresco(alvo).is_active is True


# ---------------------------------------------------------------------------
# O que fica registrado
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_registro_distingue_exonerar_de_reintegrar(client: Client) -> None:
    unidade = _unidade("EXO-HIST")
    dirigente = _dirigente(unidade, "9900500")
    alvo = _perfil(unidade, "9900510", "Alvo Histórico")

    client.force_login(_fresco(dirigente))
    client.post(_url_gravar_exonerar(alvo.pk))
    client.post(_url_gravar_reintegrar(alvo.pk))

    execucoes = ExecucaoAcao.objects.filter(autorizado=True)
    assert set(execucoes.values_list("operacao", flat=True)) == {
        "exonerar",
        "reintegrar",
    }
    assert all(execucao.alvo_identificador == alvo.rf for execucao in execucoes)
    assert all(execucao.alvo_tipo == "servidor" for execucao in execucoes)


# ---------------------------------------------------------------------------
# Abrir o modal não vira linha; a mesma leitura negada, sim
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_abrir_o_modal_nao_vira_linha(client: Client) -> None:
    unidade = _unidade("EXO-LEITURA")
    dirigente = _dirigente(unidade, "9900600")
    alvo = _perfil(unidade, "9900610", "Alvo Leitura")
    de_fora = _perfil(_unidade("EXO-LEITURA-FORA"), "9900620", "De Fora Leitura")

    client.force_login(_fresco(dirigente))
    assert client.get(_url_modal(), {"servidor": str(alvo.pk)}).status_code == 200
    assert ExecucaoAcao.objects.count() == 0

    assert client.get(_url_modal(), {"servidor": str(de_fora.pk)}).status_code == 403
    assert ExecucaoAcao.objects.filter(autorizado=False).count() == 1
