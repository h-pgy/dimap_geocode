"""
Testes de apps/user_admin/views.py — `modal_designar`, `gravar_designacao`, `modal_trocar`,
`gravar_troca`, `modal_encerrar`, `gravar_encerramento` e o modal da rota direta com as duas leituras
que ele encadeia (SPEC user_admin/024): designar substituto, trocar e encerrar cobertura viram ato
administrativo sob uma competência só, com três operações.

A ação é estrutural e o alcance é `LotacaoDoServidor`: a unidade a conferir é a lotação do
servidor substituído, lida no banco a partir do id que vem no caminho da rota.
O substituto viaja no corpo e é conferido contra o alcance de quem assina.

Todos levam o marker `banco`: direção, alcance, substituição e execução são lidos e gravados no banco.
"""

from datetime import date, timedelta

from bs4 import BeautifulSoup, Tag
from django.conf import settings as django_settings
from django.test import Client
from django.urls import reverse
from django.utils import timezone

import pytest

from apps.competencias.models import AtribuicaoUnidade, Concessao, ExecucaoAcao
from apps.unidades.models import TipoUnidade, Unidade
from apps.unidades.titularidade import definir_titular
from apps.user_admin.exercicio import registrar_impedimento
from apps.user_admin.models import (
    CargoBase,
    CargoComissao,
    Impedimento,
    Perfil,
    Substituicao,
    TipoImpedimento,
)
from apps.user_admin.schemas import (
    ERRO_FIM_ANTES_DO_INICIO_SUBSTITUICAO,
    NovaSubstituicao,
    NovoImpedimento,
)
from apps.user_admin.substituicao import ERRO_SUBSTITUTO_FORA_DO_ALCANCE, designar_substituto

banco = pytest.mark.banco

DIA = timedelta(days=1)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Substituicao",
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
    dados: dict[str, object] = {"nome": "Cargo Substituicao", "sigla": "CGSUB"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _cargo_chefia(nome: str) -> CargoComissao:
    return CargoComissao.objects.create(nome=nome, sigla="CDA", nivel=1, e_chefia=True)


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Substituicao",
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


def _tipo_impedimento(nome: str) -> TipoImpedimento:
    tipo, _ = TipoImpedimento.objects.get_or_create(nome=nome)
    return tipo


def _impedir(perfil: Perfil, nome_do_tipo: str, inicio: date | None = None, fim: date | None = None) -> Impedimento:
    hoje = timezone.localdate()
    return registrar_impedimento(
        perfil,
        NovoImpedimento(
            tipo=_tipo_impedimento(nome_do_tipo).pk,
            data_inicio=inicio or (hoje - DIA),
            data_fim=fim,
        ),
    )


def _designar(substituto: Perfil, titular: Perfil, nome_do_tipo: str, inicio: date | None = None, fim: date | None = None) -> tuple[Impedimento, Substituicao]:
    hoje = timezone.localdate()
    impedimento = _impedir(titular, nome_do_tipo, inicio=inicio or hoje, fim=fim)
    desfecho = designar_substituto(
        impedimento,
        NovaSubstituicao(
            substituto=substituto.pk,
            data_inicio=inicio or hoje,
            data_fim=fim,
        ),
        alcance={titular.unidade_id, substituto.unidade_id},
    )
    assert desfecho.substituicao is not None
    return impedimento, desfecho.substituicao


def _fresco(perfil: Perfil) -> Perfil:
    return Perfil.objects.get(pk=perfil.pk)


# ---------------------------------------------------------------------------
# Rotas e leitores de HTML
# ---------------------------------------------------------------------------


def _url_modal_designar(servidor_id: int, impedimento_id: int) -> str:
    return reverse("user_admin:modal_designar", kwargs={"servidor": servidor_id, "impedimento": impedimento_id})


def _url_gravar_designacao(servidor_id: int, impedimento_id: int) -> str:
    return reverse("user_admin:gravar_designacao", kwargs={"servidor": servidor_id, "impedimento": impedimento_id})


def _url_modal_trocar(servidor_id: int, substituicao_id: int) -> str:
    return reverse("user_admin:modal_trocar", kwargs={"servidor": servidor_id, "substituicao": substituicao_id})


def _url_gravar_troca(servidor_id: int, substituicao_id: int) -> str:
    return reverse("user_admin:gravar_troca", kwargs={"servidor": servidor_id, "substituicao": substituicao_id})


def _url_modal_encerrar(servidor_id: int, substituicao_id: int) -> str:
    return reverse("user_admin:modal_encerrar", kwargs={"servidor": servidor_id, "substituicao": substituicao_id})


def _url_gravar_encerramento(servidor_id: int, substituicao_id: int) -> str:
    return reverse("user_admin:gravar_encerramento", kwargs={"servidor": servidor_id, "substituicao": substituicao_id})


def _url_modal_direto() -> str:
    return reverse("user_admin:modal_designar_substituto")


def _url_opcoes() -> str:
    return reverse("user_admin:opcoes_substituicao")


def _url_face() -> str:
    return reverse("user_admin:face_substituicao")


def _sopa(resposta: object) -> BeautifulSoup:
    return BeautifulSoup(resposta.content.decode(), "html.parser")  # type: ignore[attr-defined]


def _controle(sopa: BeautifulSoup, tag: str, nome: str) -> Tag:
    controle = sopa.find(tag, attrs={"name": nome})
    assert isinstance(controle, Tag), f"a tela não trouxe o {tag} de {nome}"
    return controle


def _siglas_do_select(sopa: BeautifulSoup, nome: str) -> set[str]:
    select = sopa.find("select", attrs={"name": nome})
    assert select is not None, f"a tela não trouxe o select de {nome}"
    return {
        opcao.get_text(strip=True).split(" · ")[0]
        for opcao in select.find_all("option")
        if opcao.get("value")
    }


# ---------------------------------------------------------------------------
# 1 · Comportamento do ato (SPEC user_admin/024 §8)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_designar_grava_e_devolve_a_secao(client: Client) -> None:
    unidade = _unidade("SUB-GRAVA")
    dirigente = _dirigente(unidade, "9701000")
    titular = _perfil(unidade, "9701010", "Titular Grava", cargo_comissao=_cargo_chefia("Diretor T"))
    substituto = _perfil(unidade, "9701020", "Substituto Grava")
    hoje = timezone.localdate()
    impedimento = _impedir(titular, "Férias Grava", inicio=hoje, fim=hoje + 10 * DIA)

    client.force_login(_fresco(dirigente))
    resposta = client.post(
        _url_gravar_designacao(titular.pk, impedimento.pk),
        {
            "substituto": str(substituto.pk),
            "data_inicio": hoje.isoformat(),
            "data_fim": (hoje + 10 * DIA).isoformat(),
        },
    )

    assert resposta.status_code == 200
    substituicao = Substituicao.objects.get(impedimento=impedimento)
    assert substituicao.substituto == substituto
    assert substituicao.data_inicio == hoje
    assert substituicao.data_fim == hoje + 10 * DIA

    sopa = _sopa(resposta)
    secao = sopa.find(id="secao-exercicio")
    assert isinstance(secao, Tag)
    assert secao["hx-swap-oob"] == "outerHTML"
    assert substituto.nome in secao.get_text()

    painel = sopa.find(id="painel-unidade")
    assert isinstance(painel, Tag)
    assert painel["hx-swap-oob"] == "outerHTML"

    # O poço do modal é esvaziado para fechar
    secao.extract()
    painel.extract()
    assert sopa.get_text(strip=True) == ""


@banco
@pytest.mark.django_db
def test_designacao_invalida_volta_como_recusa(client: Client) -> None:
    unidade = _unidade("SUB-RECUSA")
    dirigente = _dirigente(unidade, "9701100")
    titular = _perfil(unidade, "9701110", "Titular Recusa", cargo_comissao=_cargo_chefia("Diretor R"))
    substituto = _perfil(unidade, "9701120", "Substituto Recusa")
    hoje = timezone.localdate()
    impedimento = _impedir(titular, "Férias Recusa", inicio=hoje, fim=hoje + 10 * DIA)

    client.force_login(_fresco(dirigente))
    # data_fim anterior à data_inicio
    resposta = client.post(
        _url_gravar_designacao(titular.pk, impedimento.pk),
        {
            "substituto": str(substituto.pk),
            "data_inicio": (hoje + 5 * DIA).isoformat(),
            "data_fim": hoje.isoformat(),
        },
    )

    assert resposta.status_code == 422
    assert ERRO_FIM_ANTES_DO_INICIO_SUBSTITUICAO in resposta.content.decode()
    sopa = _sopa(resposta)
    assert "campo-realce-erro" in _controle(sopa, "input", "data_fim")["class"]
    assert Substituicao.objects.filter(impedimento=impedimento).exists() is False


@banco
@pytest.mark.django_db
def test_trocar_encerra_a_anterior_na_vespera(client: Client) -> None:
    unidade = _unidade("SUB-TROCA")
    dirigente = _dirigente(unidade, "9701200")
    titular = _perfil(unidade, "9701210", "Titular Troca", cargo_comissao=_cargo_chefia("Diretor Tr"))
    sub1 = _perfil(unidade, "9701220", "Substituto Um")
    sub2 = _perfil(unidade, "9701230", "Substituto Dois")
    hoje = timezone.localdate()

    impedimento, subst1 = _designar(sub1, titular, "Férias Troca", inicio=hoje, fim=hoje + 20 * DIA)

    client.force_login(_fresco(dirigente))
    nova_data_inicio = hoje + 5 * DIA
    resposta = client.post(
        _url_gravar_troca(titular.pk, subst1.pk),
        {
            "substituto": str(sub2.pk),
            "data_inicio": nova_data_inicio.isoformat(),
            "data_fim": (hoje + 20 * DIA).isoformat(),
        },
    )

    assert resposta.status_code == 200
    subst1.refresh_from_db()
    assert subst1.data_fim == nova_data_inicio - DIA

    subst2 = Substituicao.objects.get(impedimento=impedimento, substituto=sub2)
    assert subst2.data_inicio == nova_data_inicio
    assert subst2.data_fim == hoje + 20 * DIA
    assert Substituicao.objects.filter(impedimento=impedimento).count() == 2


@banco
@pytest.mark.django_db
def test_encerrar_registra_ou_apaga(client: Client) -> None:
    unidade = _unidade("SUB-ENC")
    dirigente = _dirigente(unidade, "9701300")
    titular = _perfil(unidade, "9701310", "Titular Enc", cargo_comissao=_cargo_chefia("Diretor E"))
    sub_vigente = _perfil(unidade, "9701320", "Sub Vigente")
    sub_futuro = _perfil(unidade, "9701330", "Sub Futuro")
    hoje = timezone.localdate()

    # Cobertura vigente: termina hoje
    imp1, vig = _designar(sub_vigente, titular, "Licença Vigente", inicio=hoje - 2 * DIA, fim=hoje + 10 * DIA)
    # Cobertura futura: apagada
    imp2, fut = _designar(sub_futuro, titular, "Licença Futura", inicio=hoje + 11 * DIA, fim=hoje + 20 * DIA)

    client.force_login(_fresco(dirigente))

    # Encerrar vigente
    resp1 = client.post(_url_gravar_encerramento(titular.pk, vig.pk))
    assert resp1.status_code == 200
    vig.refresh_from_db()
    assert vig.data_fim == hoje
    assert Substituicao.objects.filter(pk=vig.pk).exists() is True

    # Encerrar futura
    resp2 = client.post(_url_gravar_encerramento(titular.pk, fut.pk))
    assert resp2.status_code == 200
    assert Substituicao.objects.filter(pk=fut.pk).exists() is False


@banco
@pytest.mark.django_db
def test_substituto_fora_do_alcance_volta_como_recusa(client: Client) -> None:
    dirigida = _unidade("SUB-ALC-DIR")
    fora = _unidade("SUB-ALC-FORA")
    dirigente = _dirigente(dirigida, "9701400")
    titular = _perfil(dirigida, "9701410", "Titular Alc", cargo_comissao=_cargo_chefia("Diretor A"))
    sub_fora = _perfil(fora, "9701420", "Sub Fora")
    hoje = timezone.localdate()
    impedimento = _impedir(titular, "Férias Alc", inicio=hoje, fim=hoje + 10 * DIA)

    client.force_login(_fresco(dirigente))
    resposta = client.post(
        _url_gravar_designacao(titular.pk, impedimento.pk),
        {
            "substituto": str(sub_fora.pk),
            "data_inicio": hoje.isoformat(),
            "data_fim": (hoje + 10 * DIA).isoformat(),
        },
    )

    assert resposta.status_code == 422
    assert ERRO_SUBSTITUTO_FORA_DO_ALCANCE in resposta.content.decode()
    sopa = _sopa(resposta)
    assert "campo-realce-erro" in _controle(sopa, "select", "substituto")["class"]
    assert Substituicao.objects.filter(impedimento=impedimento).exists() is False


@banco
@pytest.mark.django_db
def test_candidatos_recortados_ao_alcance(client: Client) -> None:
    raiz = _unidade("SUB-CAND-RAIZ")
    subordinada = _unidade("SUB-CAND-SUB", pai=raiz)
    fora = _unidade("SUB-CAND-FORA")

    dirigente = _dirigente(subordinada, "9701500")
    titular = _perfil(subordinada, "9701510", "Titular Cand", cargo_comissao=_cargo_chefia("Diretor C"))
    candidato_subordinada = _perfil(subordinada, "9701520", "Cand Sub")
    candidato_raiz = _perfil(raiz, "9701530", "Cand Raiz")
    candidato_fora = _perfil(fora, "9701540", "Cand Fora")

    hoje = timezone.localdate()
    impedimento = _impedir(titular, "Férias Cand", inicio=hoje, fim=hoje + 10 * DIA)

    client.force_login(_fresco(dirigente))
    resposta = client.get(_url_modal_designar(titular.pk, impedimento.pk))

    assert resposta.status_code == 200
    html = resposta.content.decode()
    assert candidato_subordinada.rf in html
    assert candidato_raiz.rf not in html  # Dirigente da subordinada não alcança a unidade pai
    assert candidato_fora.rf not in html


@banco
@pytest.mark.django_db
def test_secao_esconde_os_gestos_de_quem_nao_exerce(client: Client) -> None:
    unidade = _unidade("SUB-BOTOES")
    dirigente = _dirigente(unidade, "9701600")
    titular = _perfil(unidade, "9701610", "Titular Botoes", cargo_comissao=_cargo_chefia("Diretor B"))
    sub = _perfil(unidade, "9701620", "Sub Botoes")
    comum = _perfil(unidade, "9701630", "Comum Botoes")
    hoje = timezone.localdate()
    _impedimento, substituicao = _designar(sub, titular, "Férias Botoes", inicio=hoje, fim=hoje + 10 * DIA)

    pagina = reverse("user_admin:pagina_perfil", kwargs={"pk": titular.pk})

    client.force_login(_fresco(dirigente))
    html_dirigente = client.get(pagina).content.decode()
    assert _url_modal_trocar(titular.pk, substituicao.pk) in html_dirigente
    assert _url_modal_encerrar(titular.pk, substituicao.pk) in html_dirigente

    client.force_login(_fresco(comum))
    html_comum = client.get(pagina).content.decode()
    assert _url_modal_trocar(titular.pk, substituicao.pk) not in html_comum
    assert _url_modal_encerrar(titular.pk, substituicao.pk) not in html_comum


@banco
@pytest.mark.django_db
def test_pagina_unidade_sem_direcao_oferece_designar_a_quem_exerce(client: Client) -> None:
    raiz = _unidade("RAIZ-SDIR")
    dirigente = _dirigente(raiz, "9701650")
    unidade = _unidade("SUB-UNID-SDIR", pai=raiz)
    titular = _dirigente(unidade, "9701660", "Titular Unidade Sem Dir")
    comum = _perfil(unidade, "9701670", "Comum Unidade")
    hoje = timezone.localdate()
    impedimento = _impedir(titular, "Férias Titular Unid", inicio=hoje, fim=hoje + 10 * DIA)

    url_unidade = reverse("unidades:pagina_unidade", kwargs={"pk": unidade.pk})
    url_modal = _url_modal_designar(titular.pk, impedimento.pk)

    # 1. Dirigente que alcança a unidade vê o botão "Designar substituto" apontando para modal_designar
    client.force_login(_fresco(dirigente))
    resposta_dirigente = client.get(url_unidade)
    html_dirigente = resposta_dirigente.content.decode()
    assert resposta_dirigente.status_code == 200
    assert "Designar substituto" in html_dirigente
    assert url_modal in html_dirigente

    # 2. Servidor comum não vê o botão
    client.force_login(_fresco(comum))
    resposta_comum = client.get(url_unidade)
    html_comum = resposta_comum.content.decode()
    assert resposta_comum.status_code == 200
    assert url_modal not in html_comum


@banco
@pytest.mark.django_db
def test_face_direta_reflete_o_estado_do_escolhido(client: Client) -> None:
    unidade = _unidade("SUB-FACES")
    dirigente = _dirigente(unidade, "9701700")

    # 1. Sem cargo em comissão
    sem_cargo = _perfil(unidade, "9701710", "Sem Cargo")
    # 2. Sem impedimento em aberto
    sem_imp = _perfil(unidade, "9701720", "Sem Imp", cargo_comissao=_cargo_chefia("Dir 2"))
    # 3. Afastamento já coberto
    coberto = _perfil(unidade, "9701730", "Coberto", cargo_comissao=_cargo_chefia("Dir 3"))
    sub = _perfil(unidade, "9701740", "Sub Faces")
    hoje = timezone.localdate()
    _designar(sub, coberto, "Férias Coberto", inicio=hoje, fim=hoje + 10 * DIA)
    # 4. Formulário de designação (afastamento com lacuna)
    com_lacuna = _perfil(unidade, "9701750", "Com Lacuna", cargo_comissao=_cargo_chefia("Dir 4"))
    _impedir(com_lacuna, "Licença Lacuna", inicio=hoje, fim=hoje + 10 * DIA)

    client.force_login(_fresco(dirigente))

    # Teste 1: Sem cargo
    face_sem_cargo = client.get(_url_face(), {"servidor": str(sem_cargo.pk)}).content.decode()
    assert "não ocupa cargo em comissão" in face_sem_cargo

    # Teste 2: Sem impedimento
    face_sem_imp = client.get(_url_face(), {"servidor": str(sem_imp.pk)}).content.decode()
    assert "não possui afastamentos" in face_sem_imp

    # Teste 3: Coberto
    face_coberto = client.get(_url_face(), {"servidor": str(coberto.pk)}).content.decode()
    assert "já está totalmente coberto" in face_coberto

    # Teste 4: Com lacuna -> Formulário
    face_form = client.get(_url_face(), {"servidor": str(com_lacuna.pk)}).content.decode()
    assert "Substitui a partir de" in face_form
    assert "Substitui até" in face_form


@banco
@pytest.mark.django_db
def test_face_direta_escolhe_entre_afastamentos(client: Client) -> None:
    unidade = _unidade("SUB-DOIS-IMP")
    dirigente = _dirigente(unidade, "9701800")
    titular = _perfil(unidade, "9701810", "Titular Dois Imp", cargo_comissao=_cargo_chefia("Dir Dois"))
    hoje = timezone.localdate()

    imp1 = _impedir(titular, "Férias Um", inicio=hoje, fim=hoje + 10 * DIA)
    imp2 = _impedir(titular, "Licença Dois", inicio=hoje + 20 * DIA, fim=hoje + 30 * DIA)

    client.force_login(_fresco(dirigente))

    # Sem especificar query string: escolhe o primeiro
    resp_default = client.get(_url_face(), {"servidor": str(titular.pk)})
    assert str(imp1.data_inicio) in resp_default.content.decode()

    # Especificando imp2
    resp_escolhido = client.get(_url_face(), {"servidor": str(titular.pk), "impedimento": str(imp2.pk)})
    assert str(imp2.data_inicio) in resp_escolhido.content.decode()


@banco
@pytest.mark.django_db
def test_modal_direto_recorta_unidades_ao_alcance(client: Client) -> None:
    raiz = _unidade("SUB-DIR-RAIZ")
    meio = _unidade("SUB-DIR-MEIO", pai=raiz)
    _unidade("SUB-DIR-BAIXO", pai=meio)
    _unidade("SUB-DIR-TIA", pai=raiz)
    _unidade("SUB-DIR-FORA")
    dirigente = _dirigente(meio, "9701900")

    client.force_login(_fresco(dirigente))
    sopa = _sopa(client.get(_url_modal_direto()))

    assert _siglas_do_select(sopa, "unidade") == {"SUB-DIR-MEIO", "SUB-DIR-BAIXO"}


# ---------------------------------------------------------------------------
# 2 · Segurança da ação (SPEC user_admin/024 §8 + skill acao-administrativa)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_anonimo_vai_ao_login_sem_registrar(client: Client) -> None:
    unidade = _unidade("SUB-ANON")
    titular = _perfil(unidade, "9702000", "Titular Anon", cargo_comissao=_cargo_chefia("Dir Anon"))
    sub = _perfil(unidade, "9702010", "Sub Anon")
    hoje = timezone.localdate()
    impedimento = _impedir(titular, "Férias Anon", inicio=hoje, fim=hoje + 10 * DIA)

    resposta = client.post(
        _url_gravar_designacao(titular.pk, impedimento.pk),
        {
            "substituto": str(sub.pk),
            "data_inicio": hoje.isoformat(),
            "data_fim": (hoje + 10 * DIA).isoformat(),
        },
    )

    assert resposta.status_code == 302
    assert resposta["Location"].startswith(str(django_settings.LOGIN_URL))
    assert ExecucaoAcao.objects.count() == 0
    assert Substituicao.objects.count() == 0


@banco
@pytest.mark.django_db
def test_sem_competencia_recebe_403_registrado(client: Client) -> None:
    unidade = _unidade("SUB-403")
    comum = _perfil(unidade, "9702100", "Sem Competencia")
    titular = _perfil(unidade, "9702110", "Titular 403", cargo_comissao=_cargo_chefia("Dir 403"))
    sub = _perfil(unidade, "9702120", "Sub 403")
    hoje = timezone.localdate()
    impedimento = _impedir(titular, "Férias 403", inicio=hoje, fim=hoje + 10 * DIA)

    client.force_login(_fresco(comum))
    resposta = client.post(
        _url_gravar_designacao(titular.pk, impedimento.pk),
        {
            "substituto": str(sub.pk),
            "data_inicio": hoje.isoformat(),
            "data_fim": (hoje + 10 * DIA).isoformat(),
        },
    )

    assert resposta.status_code == 403
    execucao = ExecucaoAcao.objects.get()
    assert execucao.autorizado is False
    assert execucao.perfil_id == comum.pk
    assert Substituicao.objects.count() == 0


@banco
@pytest.mark.django_db
def test_titular_designa_sem_concessao_gravada(client: Client) -> None:
    raiz = _unidade("SUB-TIT-RAIZ")
    subordinada = _unidade("SUB-TIT-SUB", pai=raiz)
    dirigente = _dirigente(raiz, "9702200")
    titular = _perfil(subordinada, "9702210", "Titular Sub", cargo_comissao=_cargo_chefia("Dir Sub"))
    sub = _perfil(subordinada, "9702220", "Substituto Sub")
    hoje = timezone.localdate()
    impedimento = _impedir(titular, "Férias Sub", inicio=hoje, fim=hoje + 10 * DIA)

    client.force_login(_fresco(dirigente))
    resposta = client.post(
        _url_gravar_designacao(titular.pk, impedimento.pk),
        {
            "substituto": str(sub.pk),
            "data_inicio": hoje.isoformat(),
            "data_fim": (hoje + 10 * DIA).isoformat(),
        },
    )

    assert resposta.status_code == 200
    assert Substituicao.objects.filter(impedimento=impedimento).exists()
    assert AtribuicaoUnidade.objects.count() == 0
    assert Concessao.objects.count() == 0


@banco
@pytest.mark.django_db
def test_alvo_de_outro_ramo_e_recusado(client: Client) -> None:
    dirigida = _unidade("SUB-RAMO-DIR")
    fora = _unidade("SUB-RAMO-FORA")
    dirigente = _dirigente(dirigida, "9702300")
    titular_fora = _perfil(fora, "9702310", "Titular Fora", cargo_comissao=_cargo_chefia("Dir Fora"))
    sub_dirigida = _perfil(dirigida, "9702320", "Sub Dirigida")
    hoje = timezone.localdate()
    impedimento = _impedir(titular_fora, "Férias Fora", inicio=hoje, fim=hoje + 10 * DIA)

    client.force_login(_fresco(dirigente))
    resposta = client.post(
        _url_gravar_designacao(titular_fora.pk, impedimento.pk),
        {
            "substituto": str(sub_dirigida.pk),
            "data_inicio": hoje.isoformat(),
            "data_fim": (hoje + 10 * DIA).isoformat(),
        },
    )

    assert resposta.status_code == 403
    execucao = ExecucaoAcao.objects.get()
    assert execucao.autorizado is False
    assert Substituicao.objects.count() == 0


@banco
@pytest.mark.django_db
def test_direcao_em_outra_unidade_nao_alcanca(client: Client) -> None:
    raiz = _unidade("SUB-IRMA-RAIZ")
    irma1 = _unidade("SUB-IRMA-UM", pai=raiz)
    irma2 = _unidade("SUB-IRMA-DOIS", pai=raiz)
    dirigente_irma2 = _dirigente(irma2, "9702400")
    titular_irma1 = _perfil(irma1, "9702410", "Titular Irma1", cargo_comissao=_cargo_chefia("Dir Irma1"))
    sub = _perfil(irma2, "9702420", "Sub Irma2")
    hoje = timezone.localdate()
    impedimento = _impedir(titular_irma1, "Férias Irma1", inicio=hoje, fim=hoje + 10 * DIA)

    client.force_login(_fresco(dirigente_irma2))
    resposta = client.post(
        _url_gravar_designacao(titular_irma1.pk, impedimento.pk),
        {
            "substituto": str(sub.pk),
            "data_inicio": hoje.isoformat(),
            "data_fim": (hoje + 10 * DIA).isoformat(),
        },
    )

    assert resposta.status_code == 403
    assert Substituicao.objects.filter(impedimento=impedimento).exists() is False


@banco
@pytest.mark.django_db
def test_substituicao_de_outro_servidor_da_404(client: Client) -> None:
    unidade = _unidade("SUB-404")
    outra = _unidade("SUB-404-OUTRA")
    dirigente = _dirigente(unidade, "9702500")
    titular1 = _perfil(unidade, "9702510", "Titular 1", cargo_comissao=_cargo_chefia("Dir 1"))
    titular2 = _perfil(outra, "9702520", "Titular 2", cargo_comissao=_cargo_chefia("Dir 2"))
    sub = _perfil(unidade, "9702530", "Sub 404")
    hoje = timezone.localdate()

    _imp2, subst2 = _designar(sub, titular2, "Licença Tit2", inicio=hoje, fim=hoje + 10 * DIA)

    client.force_login(_fresco(dirigente))
    # Par forjado: titular1 (do meu alcance) + subst2 (que pertence ao titular2)
    resp_troca = client.post(
        _url_gravar_troca(titular1.pk, subst2.pk),
        {
            "substituto": str(sub.pk),
            "data_inicio": (hoje + 2 * DIA).isoformat(),
            "data_fim": (hoje + 10 * DIA).isoformat(),
        },
    )
    assert resp_troca.status_code == 404

    resp_enc = client.post(_url_gravar_encerramento(titular1.pk, subst2.pk))
    assert resp_enc.status_code == 404


@banco
@pytest.mark.django_db
def test_impedido_recebe_403_e_exonerado_302(client: Client) -> None:
    unidade = _unidade("SUB-FORA")
    impedido = _dirigente(unidade, "9702600", "Titular Impedido")
    titular_alvo = _perfil(unidade, "9702610", "Alvo Impedido", cargo_comissao=_cargo_chefia("Dir Alvo"))
    sub = _perfil(unidade, "9702620", "Sub Fora")
    hoje = timezone.localdate()
    _impedir(impedido, "Licença Titular", inicio=hoje, fim=hoje + 10 * DIA)
    imp_alvo = _impedir(titular_alvo, "Férias Alvo", inicio=hoje, fim=hoje + 10 * DIA)

    client.force_login(_fresco(impedido))
    resposta = client.post(
        _url_gravar_designacao(titular_alvo.pk, imp_alvo.pk),
        {
            "substituto": str(sub.pk),
            "data_inicio": hoje.isoformat(),
            "data_fim": (hoje + 10 * DIA).isoformat(),
        },
    )
    assert resposta.status_code == 403
    negativas = ExecucaoAcao.objects.filter(autorizado=False).count()

    exonerado = _dirigente(_unidade("SUB-EXON"), "9702630", "Titular Exonerado")
    exonerado.is_active = False
    exonerado.save(update_fields=["is_active"])

    client.force_login(exonerado)
    resposta = client.post(
        _url_gravar_designacao(titular_alvo.pk, imp_alvo.pk),
        {
            "substituto": str(sub.pk),
            "data_inicio": hoje.isoformat(),
            "data_fim": (hoje + 10 * DIA).isoformat(),
        },
    )
    assert resposta.status_code == 302
    assert resposta["Location"].startswith(str(django_settings.LOGIN_URL))
    assert ExecucaoAcao.objects.filter(autorizado=False).count() == negativas


@banco
@pytest.mark.django_db
def test_substituto_designa_durante_a_cobertura(client: Client) -> None:
    unidade_titular = _unidade("SUB-COB-TIT")
    unidade_substituto = _unidade("SUB-COB-SUB")
    titular = _dirigente(unidade_titular, "9702700", "Titular Coberto")
    substituto = _perfil(unidade_substituto, "9702710", "Substituto Cobrindo")
    alvo = _perfil(unidade_titular, "9702720", "Alvo Coberto", cargo_comissao=_cargo_chefia("Dir Coberto"))
    novo_sub = _perfil(unidade_titular, "9702730", "Novo Sub")
    hoje = timezone.localdate()

    # Substituto passa a responder pela unidade do titular
    _designar(substituto, titular, "Licença Titular", inicio=hoje - DIA, fim=hoje + 10 * DIA)
    imp_alvo = _impedir(alvo, "Férias Alvo", inicio=hoje, fim=hoje + 5 * DIA)

    client.force_login(_fresco(substituto))
    resposta = client.post(
        _url_gravar_designacao(alvo.pk, imp_alvo.pk),
        {
            "substituto": str(novo_sub.pk),
            "data_inicio": hoje.isoformat(),
            "data_fim": (hoje + 5 * DIA).isoformat(),
        },
    )

    assert resposta.status_code == 200
    assert Substituicao.objects.filter(impedimento=imp_alvo).exists()
    execucao = ExecucaoAcao.objects.filter(autorizado=True, operacao="designar").last()
    assert execucao is not None
    assert execucao.perfil_id == substituto.pk
    assert execucao.unidade_id == unidade_substituto.pk
    assert execucao.substituindo_id == titular.pk


@banco
@pytest.mark.django_db
def test_ato_grava_quem_cargo_unidade_operacao_e_alvo(client: Client) -> None:
    unidade = _unidade("SUB-REG")
    outra = _unidade("SUB-REG-OUTRA")
    dirigente = _dirigente(unidade, "9702800")
    titular = _perfil(unidade, "9702810", "Titular Reg", cargo_comissao=_cargo_chefia("Dir Reg"))
    sub = _perfil(unidade, "9702820", "Sub Reg")
    hoje = timezone.localdate()
    impedimento = _impedir(titular, "Férias Reg", inicio=hoje, fim=hoje + 10 * DIA)

    client.force_login(_fresco(dirigente))
    resposta = client.post(
        _url_gravar_designacao(titular.pk, impedimento.pk),
        {
            "substituto": str(sub.pk),
            "data_inicio": hoje.isoformat(),
            "data_fim": (hoje + 10 * DIA).isoformat(),
        },
    )
    assert resposta.status_code == 200

    execucao = ExecucaoAcao.objects.get(autorizado=True)
    assert execucao.perfil_id == dirigente.pk
    assert execucao.unidade_id == unidade.pk
    assert execucao.cargo_base_id == dirigente.cargo_base_id
    assert execucao.cargo_comissao_id == dirigente.cargo_comissao_id
    assert execucao.operacao == "designar"
    assert execucao.alvo_tipo == "servidor"
    assert execucao.alvo_identificador == titular.rf

    # Mudar a lotação depois não reescreve a linha
    dirigente.unidade = outra
    dirigente.save(update_fields=["unidade"])
    execucao.refresh_from_db()
    assert execucao.unidade_id == unidade.pk


@banco
@pytest.mark.django_db
def test_designar_trocar_e_encerrar_sao_distinguiveis_no_historico(client: Client) -> None:
    unidade = _unidade("SUB-HIST")
    dirigente = _dirigente(unidade, "9702900")
    titular = _perfil(unidade, "9702910", "Titular Hist", cargo_comissao=_cargo_chefia("Dir Hist"))
    sub1 = _perfil(unidade, "9702920", "Sub Hist 1")
    sub2 = _perfil(unidade, "9702930", "Sub Hist 2")
    hoje = timezone.localdate()
    impedimento = _impedir(titular, "Férias Hist", inicio=hoje, fim=hoje + 20 * DIA)

    client.force_login(_fresco(dirigente))

    # 1. Designar
    client.post(
        _url_gravar_designacao(titular.pk, impedimento.pk),
        {
            "substituto": str(sub1.pk),
            "data_inicio": hoje.isoformat(),
            "data_fim": (hoje + 20 * DIA).isoformat(),
        },
    )
    subst1 = Substituicao.objects.get(impedimento=impedimento, substituto=sub1)

    # 2. Trocar
    client.post(
        _url_gravar_troca(titular.pk, subst1.pk),
        {
            "substituto": str(sub2.pk),
            "data_inicio": (hoje + 5 * DIA).isoformat(),
            "data_fim": (hoje + 20 * DIA).isoformat(),
        },
    )
    subst2 = Substituicao.objects.get(impedimento=impedimento, substituto=sub2)

    # 3. Encerrar
    client.post(_url_gravar_encerramento(titular.pk, subst2.pk))

    operacoes = set(ExecucaoAcao.objects.values_list("operacao", flat=True))
    assert operacoes == {"designar", "trocar", "encerrar"}


@banco
@pytest.mark.django_db
def test_leitura_autorizada_nao_vira_linha(client: Client) -> None:
    unidade = _unidade("SUB-LEIT")
    outra = _unidade("SUB-LEIT-OUTRA")
    dirigente = _dirigente(unidade, "9703000")
    titular = _perfil(unidade, "9703010", "Titular Leit", cargo_comissao=_cargo_chefia("Dir Leit"))
    titular_fora = _perfil(outra, "9703020", "Titular Fora", cargo_comissao=_cargo_chefia("Dir Fora"))
    sub = _perfil(unidade, "9703030", "Sub Leit")
    hoje = timezone.localdate()

    imp, subst = _designar(sub, titular, "Licença Leit", inicio=hoje, fim=hoje + 10 * DIA)
    imp_fora = _impedir(titular_fora, "Licença Fora", inicio=hoje, fim=hoje + 10 * DIA)

    client.force_login(_fresco(dirigente))
    assert client.get(_url_modal_designar(titular.pk, imp.pk)).status_code == 200
    assert client.get(_url_modal_trocar(titular.pk, subst.pk)).status_code == 200
    assert client.get(_url_modal_encerrar(titular.pk, subst.pk)).status_code == 200
    assert client.get(_url_modal_direto()).status_code == 200
    assert client.get(_url_opcoes(), {"unidade": str(unidade.pk)}).status_code == 200
    assert client.get(_url_face(), {"servidor": str(titular.pk)}).status_code == 200
    assert ExecucaoAcao.objects.count() == 0

    # Negada
    assert client.get(_url_modal_designar(titular_fora.pk, imp_fora.pk)).status_code == 403
    assert ExecucaoAcao.objects.filter(autorizado=False).count() == 1


@banco
@pytest.mark.django_db
def test_escrita_so_por_post(client: Client) -> None:
    unidade = _unidade("SUB-SOPOST")
    dirigente = _dirigente(unidade, "9703100")
    titular = _perfil(unidade, "9703110", "Titular SoPost", cargo_comissao=_cargo_chefia("Dir SoPost"))
    sub = _perfil(unidade, "9703120", "Sub SoPost")
    hoje = timezone.localdate()
    imp, subst = _designar(sub, titular, "Licença SoPost", inicio=hoje, fim=hoje + 10 * DIA)

    client.force_login(_fresco(dirigente))
    resp_des = client.get(_url_gravar_designacao(titular.pk, imp.pk))
    resp_tro = client.get(_url_gravar_troca(titular.pk, subst.pk))
    resp_enc = client.get(_url_gravar_encerramento(titular.pk, subst.pk))

    assert resp_des.status_code == 405
    assert resp_tro.status_code == 405
    assert resp_enc.status_code == 405
    assert ExecucaoAcao.objects.count() == 0
