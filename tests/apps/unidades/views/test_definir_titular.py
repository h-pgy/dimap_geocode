"""
Testes de apps/unidades/views.py e apps/unidades/titularidade.py — os atos de definir, trocar e
destituir titular de unidade (SPEC user_admin/026).

Ação estrutural (`unidades.definir_titular`) com alcance `UnidadesEstritamenteSubordinadas` — o ramo
abaixo, SEM as unidades de onde ele parte: ninguém define nem destitui titular da própria unidade.

Todos levam o marker `banco`: hierarquia, titularidade, delegações, substituições, competência,
alcance e execução são lidos e gravados no banco.
"""

from datetime import timedelta

from bs4 import BeautifulSoup
from bs4.element import Tag
from django.conf import settings as django_settings
from django.test import Client
from django.urls import reverse
from django.utils import timezone

import pytest

from apps.competencias.models import Acao, Delegacao, ExecucaoAcao
from apps.competencias.resolucao import slugs_liberados
from apps.painel.abas_declaradas import ABA_ESTRUTURA, PAINEL, PARTIAL_CARTAO_MODAL
from apps.painel.resolucao import MontagemPainel, ResolvedorPainel
from apps.unidades.models import TipoUnidade, Unidade
from apps.unidades.titularidade import definir_titular
from apps.user_admin.exercicio import designar_substituto, registrar_impedimento
from apps.cargos.models import CargoBase, CargoComissao
from apps.user_admin.models import (
    Perfil,
    Substituicao,
    TipoImpedimento,
)
from apps.user_admin.schemas import NovaSubstituicao, NovoImpedimento

banco = pytest.mark.banco

SLUG_ACAO = "unidades.definir_titular"

NIVEL_RAIZ = 30
NIVEL_DIRIGIDA = 20
NIVEL_ALVO = 10


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
    dados: dict[str, object] = {"nome": "Cargo Titularidade", "sigla": "CGTT"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _cargo_chefia(nome: str, nivel: int = 1) -> CargoComissao:
    return CargoComissao.objects.create(
        nome=nome, sigla="CDA", nivel=nivel, e_chefia=True
    )


def _perfil(
    unidade: Unidade, rf: str, nome: str = "Servidor", **overrides: object
) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Titularidade",
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
        unidade=_unidade(f"DT-SU-{rf}", NIVEL_RAIZ),
        cargo_base=_cargo_base(),
    )


def _ramo(prefixo: str) -> tuple[Unidade, Unidade, Unidade]:
    raiz = _unidade(f"{prefixo}-RAIZ", NIVEL_RAIZ)
    dirigida = _unidade(f"{prefixo}-DIR", NIVEL_DIRIGIDA, pai=raiz)
    alvo = _unidade(f"{prefixo}-ALVO", NIVEL_ALVO, pai=dirigida)
    return raiz, dirigida, alvo


def _acao(slug: str, **overrides: object) -> Acao:
    dados: dict[str, object] = {"nome": f"Ação {slug}", "tooltip": "tt", "ativa": True}
    dados.update(overrides)
    acao, _ = Acao.objects.get_or_create(slug=slug, defaults=dados)  # type: ignore[arg-type]
    return acao


def _impedir(perfil: Perfil) -> None:
    tipo, _ = TipoImpedimento.objects.get_or_create(nome="Licença Titularidade")
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


def _url_modal() -> str:
    return reverse("unidades:modal_definir_titular")


def _url_face() -> str:
    return reverse("unidades:face_titularidade")


def _url_definir() -> str:
    return reverse("unidades:gravar_definir_titular")


def _url_destituir() -> str:
    return reverse("unidades:gravar_destituir_titular")


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


# ---------------------------------------------------------------------------
# Atos de titularidade: definir, trocar e destituir em transação
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_definir_titular_em_unidade_sem_titular(client: Client) -> None:
    _, dirigida, alvo = _ramo("DT-DEF")
    dirigente = _dirigente(dirigida, "9300000")
    candidato = _perfil(
        alvo,
        "9300001",
        "Candidato",
        cargo_comissao=_cargo_chefia("Chefe Alvo", nivel=1),
    )

    client.force_login(dirigente)
    resposta = client.post(
        _url_definir(),
        {"unidade": str(alvo.pk), "titular": str(candidato.pk)},
    )

    assert resposta.status_code == 200
    candidato.refresh_from_db()
    alvo.refresh_from_db()
    assert candidato.e_titular is True
    assert alvo.titular == candidato
    assert Perfil.objects.filter(unidade=alvo, e_titular=True).count() == 1

    html = resposta.content.decode()
    assert candidato.nome in html


@banco
@pytest.mark.django_db
def test_trocar_titular_destitui_anterior_e_marca_novo_em_transacao(
    client: Client,
) -> None:
    _, dirigida, alvo = _ramo("DT-TROCA")
    dirigente = _dirigente(dirigida, "9300100")
    anterior = _perfil(
        alvo,
        "9300101",
        "Anterior",
        cargo_comissao=_cargo_chefia("Chefe Anterior", nivel=1),
    )
    definir_titular(anterior)
    _impedir(anterior)

    novo = _perfil(
        alvo,
        "9300102",
        "Novo",
        cargo_comissao=_cargo_chefia("Chefe Novo", nivel=1),
    )

    client.force_login(dirigente)
    resposta = client.post(
        _url_definir(),
        {"unidade": str(alvo.pk), "titular": str(novo.pk)},
    )

    assert resposta.status_code == 200
    anterior.refresh_from_db()
    novo.refresh_from_db()
    alvo.refresh_from_db()
    assert anterior.e_titular is False
    assert novo.e_titular is True
    assert alvo.titular == novo
    assert Perfil.objects.filter(unidade=alvo, e_titular=True).count() == 1


@banco
@pytest.mark.django_db
def test_destituir_titular_abre_vaga_e_encerra_delegacoes_vigentes(
    client: Client,
) -> None:
    _, dirigida, alvo = _ramo("DT-DEST-DEL")
    dirigente = _dirigente(dirigida, "9300200")
    titular = _perfil(
        alvo,
        "9300201",
        "Titular",
        cargo_comissao=_cargo_chefia("Chefe Titular", nivel=1),
    )
    definir_titular(titular)
    delegado = _perfil(alvo, "9300202", "Delegado")
    hoje = timezone.localdate()
    acao = _acao("unidades.editar_unidade")

    vigente = Delegacao.objects.create(
        acao=acao,
        unidade=alvo,
        delegante=titular,
        delegado=delegado,
        data_inicio=hoje - timedelta(days=5),
        data_fim=None,
    )
    futura = Delegacao.objects.create(
        acao=acao,
        unidade=alvo,
        delegante=titular,
        delegado=delegado,
        data_inicio=hoje + timedelta(days=5),
        data_fim=None,
    )

    client.force_login(dirigente)
    resposta = client.post(_url_destituir(), {"unidade": str(alvo.pk)})

    assert resposta.status_code == 200
    alvo.refresh_from_db()
    titular.refresh_from_db()
    assert alvo.titular is None
    assert titular.e_titular is False

    vigente.refresh_from_db()
    assert vigente.data_fim == hoje
    assert not Delegacao.objects.filter(pk=futura.pk).exists()


@banco
@pytest.mark.django_db
def test_destituir_titular_encerra_substituicoes_vigentes_do_afastado(
    client: Client,
) -> None:
    _, dirigida, alvo = _ramo("DT-DEST-SUB")
    dirigente = _dirigente(dirigida, "9300300")
    titular = _perfil(
        alvo,
        "9300301",
        "Titular Afastado",
        cargo_comissao=_cargo_chefia("Chefe Titular", nivel=1),
    )
    definir_titular(titular)
    substituto = _perfil(alvo, "9300302", "Substituto")
    tipo_imp, _ = TipoImpedimento.objects.get_or_create(nome="Licença Destituição")
    hoje = timezone.localdate()

    impedimento = registrar_impedimento(
        titular,
        NovoImpedimento(
            tipo=tipo_imp.pk,
            data_inicio=hoje - timedelta(days=5),
            data_fim=None,
        ),
    )
    designar_substituto(
        impedimento,
        NovaSubstituicao(
            substituto=substituto.pk,
            data_inicio=hoje - timedelta(days=5),
            data_fim=None,
        ),
    )
    futura_sub = Substituicao.objects.create(
        impedimento=impedimento,
        substituto=substituto,
        data_inicio=hoje + timedelta(days=5),
        data_fim=None,
    )

    client.force_login(dirigente)
    resposta = client.post(_url_destituir(), {"unidade": str(alvo.pk)})

    assert resposta.status_code == 200
    alvo.refresh_from_db()
    titular.refresh_from_db()
    assert alvo.titular is None
    assert titular.e_titular is False

    sub_vigente = Substituicao.objects.get(
        impedimento=impedimento, data_inicio=hoje - timedelta(days=5)
    )
    assert sub_vigente.data_fim == hoje
    assert not Substituicao.objects.filter(pk=futura_sub.pk).exists()


# ---------------------------------------------------------------------------
# Validações do candidato (lotação, cargo e exercício)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_definir_titular_com_servidor_de_outra_unidade_ou_sem_cargo_recusa_422(
    client: Client,
) -> None:
    _, dirigida, alvo = _ramo("DT-REC-CARGO")
    dirigente = _dirigente(dirigida, "9300400")
    outro_servidor = _perfil(
        dirigida,
        "9300401",
        "Outro Servidor",
        cargo_comissao=_cargo_chefia("Chefe Outro", nivel=1),
    )
    servidor_sem_cargo = _perfil(alvo, "9300402", "Sem Cargo")

    client.force_login(dirigente)

    resp_outra = client.post(
        _url_definir(),
        {"unidade": str(alvo.pk), "titular": str(outro_servidor.pk)},
    )
    assert resp_outra.status_code == 422
    alvo.refresh_from_db()
    assert alvo.titular is None

    resp_sem_cargo = client.post(
        _url_definir(),
        {"unidade": str(alvo.pk), "titular": str(servidor_sem_cargo.pk)},
    )
    assert resp_sem_cargo.status_code == 422
    alvo.refresh_from_db()
    assert alvo.titular is None


@banco
@pytest.mark.django_db
def test_definir_titular_com_servidor_impedido_recusa_422(client: Client) -> None:
    _, dirigida, alvo = _ramo("DT-REC-IMP")
    dirigente = _dirigente(dirigida, "9300500")
    candidato = _perfil(
        alvo,
        "9300501",
        "Candidato",
        cargo_comissao=_cargo_chefia("Chefe Candidato", nivel=1),
    )
    _impedir(candidato)

    client.force_login(dirigente)
    resposta = client.post(
        _url_definir(),
        {"unidade": str(alvo.pk), "titular": str(candidato.pk)},
    )

    assert resposta.status_code == 422
    candidato.refresh_from_db()
    alvo.refresh_from_db()
    assert candidato.e_titular is False
    assert alvo.titular is None


# ---------------------------------------------------------------------------
# Modal e face de titularidade
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_modal_direto_lista_apenas_unidades_do_alcance_estrito(
    client: Client,
) -> None:
    raiz, dirigida, alvo1 = _ramo("DT-MODAL")
    alvo2 = _unidade("DT-MODAL-ALVO2", NIVEL_ALVO, pai=dirigida)
    _, _, alheio = _ramo("DT-MODAL-ALHEIO")
    dirigente = _dirigente(dirigida, "9300600")

    client.force_login(dirigente)
    resposta = client.get(_url_modal())
    assert resposta.status_code == 200

    siglas = _siglas_no_select(_sopa(resposta.content.decode()))
    assert alvo1.sigla in siglas
    assert alvo2.sigla in siglas
    assert dirigida.sigla not in siglas
    assert raiz.sigla not in siglas
    assert alheio.sigla not in siglas

    resposta_face = client.get(_url_face(), {"unidade": str(alvo1.pk)})
    assert resposta_face.status_code == 200


# ---------------------------------------------------------------------------
# Card no Painel de Ações
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_card_titularidade_presente_no_painel_para_quem_tem_competencia() -> None:
    _, dirigida, _ = _ramo("DT-CARD")
    dirigente = _dirigente(dirigida, "9300700")
    comum = _perfil(dirigida, "9300701", "Comum")

    slugs_dir = slugs_liberados(dirigente)
    painel_dir = ResolvedorPainel()(
        MontagemPainel(painel=PAINEL, slugs_liberados=slugs_dir, perfil_id=dirigente.pk)
    )
    aba_dir = next((a for a in painel_dir.abas if a.slug == ABA_ESTRUTURA.slug), None)
    assert aba_dir is not None
    grupo_dir = next((g for g in aba_dir.grupos if g.rotulo == "Organograma"), None)
    assert grupo_dir is not None
    item_tit = next((i for i in grupo_dir.itens if i.slug == SLUG_ACAO), None)
    assert item_tit is not None
    assert item_tit.partial == PARTIAL_CARTAO_MODAL

    slugs_com = slugs_liberados(comum)
    painel_com = ResolvedorPainel()(
        MontagemPainel(painel=PAINEL, slugs_liberados=slugs_com, perfil_id=comum.pk)
    )
    aba_com = next((a for a in painel_com.abas if a.slug == ABA_ESTRUTURA.slug), None)
    if aba_com is not None:
        grupo_com = next((g for g in aba_com.grupos if g.rotulo == "Organograma"), None)
        if grupo_com is not None:
            assert not any(i.slug == SLUG_ACAO for i in grupo_com.itens)


# ---------------------------------------------------------------------------
# Segurança da ação (skill acao-administrativa)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_definir_titular_anonimo_redireciona_login(client: Client) -> None:
    _, _, alvo = _ramo("DT-ANON")

    for url in (_url_modal(), _url_face()):
        resposta_get = client.get(url, {"unidade": str(alvo.pk)})
        assert resposta_get.status_code == 302
        assert resposta_get["Location"].startswith(str(django_settings.LOGIN_URL))

    for url in (_url_definir(), _url_destituir()):
        resposta_post = client.post(url, {"unidade": str(alvo.pk)})
        assert resposta_post.status_code == 302
        assert resposta_post["Location"].startswith(str(django_settings.LOGIN_URL))

    assert ExecucaoAcao.objects.filter(acao__slug=SLUG_ACAO).count() == 0


@banco
@pytest.mark.django_db
def test_definir_titular_sem_competencia_retorna_403_e_registra_negativa(
    client: Client,
) -> None:
    _, dirigida, alvo = _ramo("DT-SEMCOMP")
    comum = _perfil(dirigida, "9300800", "Comum")
    candidato = _perfil(
        alvo, "9300801", "Candidato", cargo_comissao=_cargo_chefia("Chefe", nivel=1)
    )

    client.force_login(comum)
    resposta = client.post(
        _url_definir(),
        {"unidade": str(alvo.pk), "titular": str(candidato.pk)},
    )

    assert resposta.status_code == 403
    assert _negativas() == 1
    alvo.refresh_from_db()
    assert alvo.titular is None


@banco
@pytest.mark.django_db
def test_definir_titular_fora_do_alcance_estrito_retorna_403_registrado(
    client: Client,
) -> None:
    _, dirigida, _alvo = _ramo("DT-FORA-A")
    _, _, alheio = _ramo("DT-FORA-B")
    dirigente = _dirigente(dirigida, "9300900")
    candidato = _perfil(
        alheio, "9300901", "Candidato", cargo_comissao=_cargo_chefia("Chefe B", nivel=1)
    )

    client.force_login(dirigente)
    resposta = client.post(
        _url_definir(),
        {"unidade": str(alheio.pk), "titular": str(candidato.pk)},
    )

    assert resposta.status_code == 403
    assert _negativas() == 1
    alheio.refresh_from_db()
    assert alheio.titular is None


@banco
@pytest.mark.django_db
def test_titular_nao_pode_definir_ou_destituir_a_propria_titularidade(
    client: Client,
) -> None:
    _, dirigida, _ = _ramo("DT-PROPRIA")
    dirigente = _dirigente(dirigida, "9301000")
    outro = _perfil(
        dirigida, "9301001", "Outro", cargo_comissao=_cargo_chefia("Outro Dir", nivel=1)
    )

    client.force_login(dirigente)

    resp_def = client.post(
        _url_definir(),
        {"unidade": str(dirigida.pk), "titular": str(outro.pk)},
    )
    assert resp_def.status_code == 403

    resp_dest = client.post(
        _url_destituir(),
        {"unidade": str(dirigida.pk)},
    )
    assert resp_dest.status_code == 403

    assert _negativas() == 2
    dirigida.refresh_from_db()
    assert dirigida.titular == dirigente


@banco
@pytest.mark.django_db
def test_superusuario_alcanca_qualquer_unidade_inclusive_raiz(
    client: Client,
) -> None:
    raiz, _, alvo = _ramo("DT-SUPER")
    superusuario = _superusuario("9301100")
    candidato_raiz = _perfil(
        raiz,
        "9301101",
        "Candidato Raiz",
        cargo_comissao=_cargo_chefia("Diretor Raiz", nivel=1),
    )
    candidato_alvo = _perfil(
        alvo,
        "9301102",
        "Candidato Alvo",
        cargo_comissao=_cargo_chefia("Chefe Alvo", nivel=1),
    )

    client.force_login(superusuario)

    resp_raiz = client.post(
        _url_definir(),
        {"unidade": str(raiz.pk), "titular": str(candidato_raiz.pk)},
    )
    assert resp_raiz.status_code == 200
    raiz.refresh_from_db()
    assert raiz.titular == candidato_raiz

    resp_dest_raiz = client.post(
        _url_destituir(),
        {"unidade": str(raiz.pk)},
    )
    assert resp_dest_raiz.status_code == 200
    raiz.refresh_from_db()
    assert raiz.titular is None

    resp_alvo = client.post(
        _url_definir(),
        {"unidade": str(alvo.pk), "titular": str(candidato_alvo.pk)},
    )
    assert resp_alvo.status_code == 200
    alvo.refresh_from_db()
    assert alvo.titular == candidato_alvo

    assert (
        ExecucaoAcao.objects.filter(perfil=superusuario, autorizado=True).count() == 3
    )


@banco
@pytest.mark.django_db
def test_ato_autorizado_registra_operacao_e_alvo(client: Client) -> None:
    _, dirigida, alvo = _ramo("DT-RASTRO")
    dirigente = _dirigente(dirigida, "9301200")
    cand1 = _perfil(
        alvo, "9301201", "Primeiro", cargo_comissao=_cargo_chefia("Chefe 1", nivel=1)
    )
    cand2 = _perfil(
        alvo, "9301202", "Segundo", cargo_comissao=_cargo_chefia("Chefe 2", nivel=1)
    )

    client.force_login(dirigente)

    # 1. Definir em unidade sem titular -> operacao="definir"
    client.post(_url_definir(), {"unidade": str(alvo.pk), "titular": str(cand1.pk)})

    # 2. Trocar titular -> operacao="trocar"
    client.post(_url_definir(), {"unidade": str(alvo.pk), "titular": str(cand2.pk)})

    # 3. Destituir titular -> operacao="destituir"
    client.post(_url_destituir(), {"unidade": str(alvo.pk)})

    execucoes = ExecucaoAcao.objects.filter(
        acao__slug=SLUG_ACAO, autorizado=True
    ).order_by("momento")
    assert [e.operacao for e in execucoes] == ["definir", "trocar", "destituir"]
    assert all(e.alvo_tipo == "unidade" for e in execucoes)
    assert all(e.alvo_identificador == alvo.sigla for e in execucoes)
    assert all(e.perfil_id == dirigente.pk for e in execucoes)
    assert all(e.unidade_id == dirigida.pk for e in execucoes)
