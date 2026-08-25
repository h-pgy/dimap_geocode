"""
Testes de apps/user_admin/views.py — `modal_impedimento`, `gravar_impedimento`, `modal_retorno`,
`gravar_retorno` e o modal da rota direta com as duas leituras que ele encadeia
(SPEC user_admin/023): registrar impedimento e voltar ao exercício viram ato administrativo, sob
uma competência só, com duas operações.

A ação é estrutural e o alcance é `LotacaoDoServidor`: a unidade a conferir é a lotação do
servidor-alvo, lida no banco a partir do id que vem no caminho da rota — nunca do corpo. O
comportamento dos atos em si (o que `registrar_impedimento` e `retornar_ao_exercicio` gravam) é
`tests/apps/user_admin/test_exercicio.py`; aqui ficam o contrato HTTP das rotas e a bateria de
segurança da skill `acao-administrativa`.

Todos levam o marker `banco`: direção, alcance, impedimento e execução são lidos e gravados no banco.
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
from apps.user_admin.exercicio import designar_substituto, registrar_impedimento
from apps.user_admin.models import (
    CargoBase,
    CargoComissao,
    Impedimento,
    Perfil,
    Substituicao,
    TipoImpedimento,
)
from apps.user_admin.schemas import ERRO_FIM_ANTES_DO_INICIO, NovaSubstituicao, NovoImpedimento

banco = pytest.mark.banco

DIA = timedelta(days=1)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Impedimento",
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
    dados: dict[str, object] = {"nome": "Cargo Impedimento", "sigla": "CGIM"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _cargo_chefia(nome: str) -> CargoComissao:
    return CargoComissao.objects.create(nome=nome, sigla="CDA", nivel=1, e_chefia=True)


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Impedimento",
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
    # Sem sigla: é o `nome` que o cartão da seção escreve, e é por ele que os testes o reconhecem.
    tipo, _ = TipoImpedimento.objects.get_or_create(nome=nome)
    return tipo


def _impedir(perfil: Perfil, nome_do_tipo: str) -> Impedimento:
    return registrar_impedimento(
        perfil,
        NovoImpedimento(
            tipo=_tipo_impedimento(nome_do_tipo).pk,
            data_inicio=timezone.localdate() - DIA,
            data_fim=None,
        ),
    )


def _cobrir(substituto: Perfil, titular: Perfil, nome_do_tipo: str) -> Impedimento:
    """Afasta o titular e põe o substituto no lugar: é por aqui que o substituto passa a responder
    pela unidade do titular, além da própria."""
    impedimento = _impedir(titular, nome_do_tipo)
    designar_substituto(
        impedimento,
        NovaSubstituicao(
            substituto=substituto.pk,
            data_inicio=timezone.localdate(),
            data_fim=None,
        ),
    )
    return impedimento


def _fresco(perfil: Perfil) -> Perfil:
    # O cache de `has_perm` é do objeto Python: cada requisição simulada precisa ver o efeito de
    # uma mudança de estado como uma requisição nova veria.
    return Perfil.objects.get(pk=perfil.pk)


def _payload(tipo: TipoImpedimento, inicio: date, fim: date | None = None) -> dict[str, str]:
    return {
        "tipo": str(tipo.pk),
        "data_inicio": inicio.isoformat(),
        "data_fim": fim.isoformat() if fim is not None else "",
    }


# ---------------------------------------------------------------------------
# Rotas e leitores de HTML
# ---------------------------------------------------------------------------


def _url_modal(servidor_id: int) -> str:
    return reverse("user_admin:modal_impedimento", kwargs={"servidor": servidor_id})


def _url_gravar(servidor_id: int) -> str:
    return reverse("user_admin:gravar_impedimento", kwargs={"servidor": servidor_id})


def _url_modal_retorno(servidor_id: int) -> str:
    return reverse("user_admin:modal_retorno", kwargs={"servidor": servidor_id})


def _url_gravar_retorno(servidor_id: int) -> str:
    return reverse("user_admin:gravar_retorno", kwargs={"servidor": servidor_id})


def _url_modal_direto() -> str:
    return reverse("user_admin:modal_registrar_impedimento")


def _url_opcoes() -> str:
    return reverse("user_admin:opcoes_impedimento")


def _url_face() -> str:
    return reverse("user_admin:face_impedimento")


def _sopa(resposta: object) -> BeautifulSoup:
    return BeautifulSoup(resposta.content.decode(), "html.parser")  # type: ignore[attr-defined]


def _controle(sopa: BeautifulSoup, tag: str, nome: str) -> Tag:
    controle = sopa.find(tag, attrs={"name": nome})
    assert isinstance(controle, Tag), f"a tela não trouxe o {tag} de {nome}"
    return controle


def _siglas_do_select(sopa: BeautifulSoup, nome: str) -> set[str]:
    """As siglas que o select oferece. Opção sem valor fica de fora: ela é o "— escolha —"."""
    select = sopa.find("select", attrs={"name": nome})
    assert select is not None, f"a tela não trouxe o select de {nome}"
    return {
        opcao.get_text(strip=True).split(" · ")[0]
        for opcao in select.find_all("option")
        if opcao.get("value")
    }


# ---------------------------------------------------------------------------
# O ato grava: o servidor sai do exercício na data que o impedimento declara
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_registrar_impedimento_tira_do_exercicio(client: Client) -> None:
    unidade = _unidade("IMP-GRAVA")
    dirigente = _dirigente(unidade, "9601000")
    alvo = _perfil(unidade, "9601010", "Alvo Grava")
    tipo = _tipo_impedimento("Licença Grava")
    hoje = timezone.localdate()

    client.force_login(_fresco(dirigente))
    futuro = client.post(_url_gravar(alvo.pk), _payload(tipo, hoje + 2 * DIA))

    assert futuro.status_code == 200
    # Gravado, mas ainda não vigente: quem sai do exercício sai na data DECLARADA, não ao gravar.
    assert Impedimento.objects.get(perfil=alvo).data_inicio == hoje + 2 * DIA
    assert _fresco(alvo).em_exercicio is True

    vigente = client.post(_url_gravar(alvo.pk), _payload(tipo, hoje))

    assert vigente.status_code == 200
    assert _fresco(alvo).em_exercicio is False


@banco
@pytest.mark.django_db
def test_retorno_devolve_a_cadeira_hoje(client: Client) -> None:
    raiz = _unidade("IMP-RET-RAIZ")
    subordinada = _unidade("IMP-RET-SUB", pai=raiz)
    dirigente = _dirigente(raiz, "9601100")
    alvo = _dirigente(subordinada, "9601110", "Alvo Retorno")
    substituto = _perfil(subordinada, "9601120", "Substituto Retorno")
    impedimento = _cobrir(substituto, alvo, "Licença Retorno")
    hoje = timezone.localdate()

    client.force_login(_fresco(dirigente))
    resposta = client.post(_url_gravar_retorno(alvo.pk))

    assert resposta.status_code == 200
    assert _fresco(alvo).em_exercicio is True
    impedimento.refresh_from_db()
    assert impedimento.data_fim == hoje - DIA
    # A substituição em curso é acertada na mesma transação, e não sobrevive ao retorno.
    assert Substituicao.objects.filter(impedimento=impedimento).count() == 0


@banco
@pytest.mark.django_db
def test_impedimento_iniciado_hoje_e_apagado_e_a_cadeira_segue(client: Client) -> None:
    """Impedimento que começa hoje não tem data anterior ao início para gravar: encerrá-lo seria
    deixá-lo valendo hoje, e a pessoa fora da cadeira por um dia que ninguém pediu."""
    unidade = _unidade("IMP-REVOGA")
    dirigente = _dirigente(unidade, "9601900")
    alvo = _perfil(
        unidade,
        "9601910",
        "Alvo Revoga",
        cargo_comissao=_cargo_chefia("Diretor Revoga"),
    )
    substituto = _perfil(unidade, "9601920", "Substituto Revoga")
    tipo = _tipo_impedimento("Licença Revoga")
    hoje = timezone.localdate()

    comeca_hoje = registrar_impedimento(
        alvo,
        NovoImpedimento(tipo=tipo.pk, data_inicio=hoje, data_fim=None),
    )
    designar_substituto(
        comeca_hoje,
        NovaSubstituicao(substituto=substituto.pk, data_inicio=hoje, data_fim=None),
    )

    client.force_login(_fresco(dirigente))
    resposta = client.post(_url_gravar_retorno(alvo.pk))

    assert resposta.status_code == 200
    # Nunca vigorou: some, e a substituição dele vai junto pelo CASCADE.
    assert Impedimento.objects.filter(pk=comeca_hoje.pk).exists() is False
    assert Substituicao.objects.filter(impedimento_id=comeca_hoje.pk).exists() is False
    assert _fresco(alvo).em_exercicio is True

    # Com um vigente que JÁ vigorou, o ato tem as duas metades na mesma transação.
    ja_vigorou = registrar_impedimento(
        alvo,
        NovoImpedimento(tipo=tipo.pk, data_inicio=hoje - 3 * DIA, data_fim=None),
    )
    outro_hoje = registrar_impedimento(
        alvo,
        NovoImpedimento(tipo=tipo.pk, data_inicio=hoje, data_fim=None),
    )

    assert client.post(_url_gravar_retorno(alvo.pk)).status_code == 200

    ja_vigorou.refresh_from_db()
    assert ja_vigorou.data_fim == hoje - DIA
    assert Impedimento.objects.filter(pk=outro_hoje.pk).exists() is False
    assert _fresco(alvo).em_exercicio is True


@banco
@pytest.mark.django_db
def test_face_do_retorno_escolhe_revogar_ou_voltar(client: Client) -> None:
    unidade = _unidade("IMP-DUAS-FACES")
    dirigente = _dirigente(unidade, "9601950")
    nao_vigorou = _perfil(unidade, "9601960", "Alvo Não Vigorou")
    ja_vigorou = _perfil(unidade, "9601970", "Alvo Já Vigorou")
    registrar_impedimento(
        nao_vigorou,
        NovoImpedimento(
            tipo=_tipo_impedimento("Licença Faces").pk,
            data_inicio=timezone.localdate(),
            data_fim=None,
        ),
    )
    # `_impedir` começa ontem: esse já tirou a pessoa da cadeira.
    _impedir(ja_vigorou, "Licença Faces Antiga")

    client.force_login(_fresco(dirigente))
    revogacao = client.get(_url_modal_retorno(nao_vigorou.pk)).content.decode()
    retorno = client.get(_url_modal_retorno(ja_vigorou.pk)).content.decode()

    assert "Revogar impedimento" in revogacao
    assert "não saiu do exercício" in revogacao
    assert "Voltar ao exercício" not in revogacao

    assert "Voltar ao exercício" in retorno
    assert "Revogar impedimento" not in retorno


@banco
@pytest.mark.django_db
def test_titular_registra_sem_concessao_gravada(client: Client) -> None:
    raiz = _unidade("IMP-ESTR-RAIZ")
    subordinada = _unidade("IMP-ESTR-SUB", pai=raiz)
    dirigente = _dirigente(raiz, "9601200")
    alvo = _perfil(subordinada, "9601210", "Alvo Estrutural")
    tipo = _tipo_impedimento("Licença Estrutural")

    client.force_login(_fresco(dirigente))
    resposta = client.post(_url_gravar(alvo.pk), _payload(tipo, timezone.localdate()))

    assert resposta.status_code == 200
    assert Impedimento.objects.filter(perfil=alvo).exists()
    # Dirigir basta: nada foi atribuído à unidade nem concedido a cargo algum.
    assert AtribuicaoUnidade.objects.count() == 0
    assert Concessao.objects.count() == 0


# ---------------------------------------------------------------------------
# Fim antes do início volta como recusa em português, no próprio modal
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_fim_antes_do_inicio_volta_como_recusa(client: Client) -> None:
    unidade = _unidade("IMP-RECUSA")
    dirigente = _dirigente(unidade, "9601300")
    alvo = _perfil(unidade, "9601310", "Alvo Recusa")
    tipo = _tipo_impedimento("Licença Recusa")
    hoje = timezone.localdate()

    client.force_login(_fresco(dirigente))
    resposta = client.post(_url_gravar(alvo.pk), _payload(tipo, hoje + 5 * DIA, hoje))
    sopa = _sopa(resposta)

    assert resposta.status_code == 422
    assert ERRO_FIM_ANTES_DO_INICIO in resposta.content.decode()
    assert "campo-realce-erro" in _controle(sopa, "input", "data_fim")["class"]
    assert "campo-realce-erro" not in _controle(sopa, "input", "data_inicio")["class"]
    assert Impedimento.objects.filter(perfil=alvo).exists() is False


# ---------------------------------------------------------------------------
# Os botões da seção só existem para quem exerce a ação sobre aquele servidor
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_secao_esconde_os_botoes_de_quem_nao_exerce(client: Client) -> None:
    unidade = _unidade("IMP-BOTOES")
    dirigente = _dirigente(unidade, "9601400")
    alvo = _perfil(unidade, "9601410", "Alvo Botões", cargo_comissao=_cargo_chefia("Diretor Botões"))
    _impedir(alvo, "Licença Botões")
    comum = _perfil(unidade, "9601420", "Comum Botões")
    pagina = reverse("user_admin:pagina_perfil", kwargs={"pk": alvo.pk})

    client.force_login(_fresco(dirigente))
    html = client.get(pagina).content.decode()
    assert _url_modal(alvo.pk) in html
    assert _url_modal_retorno(alvo.pk) in html

    client.force_login(_fresco(comum))
    html = client.get(pagina).content.decode()
    assert _url_modal(alvo.pk) not in html
    assert _url_modal_retorno(alvo.pk) not in html


@banco
@pytest.mark.django_db
def test_gravacao_devolve_secao_atualizada(client: Client) -> None:
    unidade = _unidade("IMP-SECAO")
    dirigente = _dirigente(unidade, "9601500")
    alvo = _perfil(unidade, "9601510", "Alvo Seção")
    tipo = _tipo_impedimento("Licença Seção")

    client.force_login(_fresco(dirigente))
    resposta = client.post(_url_gravar(alvo.pk), _payload(tipo, timezone.localdate()))
    sopa = _sopa(resposta)
    secao = sopa.find(id="secao-exercicio")

    assert resposta.status_code == 200
    assert isinstance(secao, Tag)
    assert secao["hx-swap-oob"] == "outerHTML"
    assert tipo.nome in secao.get_text()
    # Fora do swap fora de banda não sobra nada: o poço do modal recebe vazio, e é assim que o
    # modal fecha.
    secao.extract()
    assert sopa.get_text(strip=True) == ""


# ---------------------------------------------------------------------------
# O modal da rota direta: unidade recortada ao alcance, servidor dentro dela, face pelo estado
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_modal_direto_recorta_unidades_ao_alcance(client: Client) -> None:
    raiz = _unidade("IMP-ALC-RAIZ")
    meio = _unidade("IMP-ALC-MEIO", pai=raiz)
    _unidade("IMP-ALC-BAIXO", pai=meio)
    _unidade("IMP-ALC-TIA", pai=raiz)
    _unidade("IMP-ALC-FORA")
    dirigente = _dirigente(meio, "9601600")

    client.force_login(_fresco(dirigente))
    sopa = _sopa(client.get(_url_modal_direto()))

    assert _siglas_do_select(sopa, "unidade") == {"IMP-ALC-MEIO", "IMP-ALC-BAIXO"}


@banco
@pytest.mark.django_db
def test_opcoes_lista_servidores_da_unidade_escolhida(client: Client) -> None:
    unidade = _unidade("IMP-OPC")
    outra = _unidade("IMP-OPC-OUTRA")
    dirigente = _dirigente(unidade, "9601700")
    dentro = _perfil(unidade, "9601710", "Dentro Opções")
    fora = _perfil(outra, "9601720", "Fora Opções")

    client.force_login(_fresco(dirigente))
    resposta = client.get(_url_opcoes(), {"unidade": str(unidade.pk)})
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert dentro.rf in html
    assert fora.rf not in html


@banco
@pytest.mark.django_db
def test_face_reflete_o_estado_do_escolhido(client: Client) -> None:
    unidade = _unidade("IMP-FACE")
    dirigente = _dirigente(unidade, "9601800")
    em_exercicio = _perfil(unidade, "9601810", "Face Em Exercício")
    impedido = _perfil(unidade, "9601820", "Face Impedido")
    _impedir(impedido, "Licença Face")

    client.force_login(_fresco(dirigente))
    formulario = _sopa(client.get(_url_face(), {"servidor": str(em_exercicio.pk)}))
    confirmacao = _sopa(client.get(_url_face(), {"servidor": str(impedido.pk)}))

    # Em exercício, a face é o formulário do impedimento, e ele grava sobre o escolhido.
    assert _controle(formulario, "input", "data_inicio") is not None
    assert _controle(formulario, "select", "tipo") is not None
    assert _url_gravar(em_exercicio.pk) in str(formulario)

    # Impedido, a face é a confirmação do retorno — sem campo de período algum.
    assert confirmacao.find("input", attrs={"name": "data_inicio"}) is None
    assert _url_gravar_retorno(impedido.pk) in str(confirmacao)


# ---------------------------------------------------------------------------
# Segurança da ação — skill `acao-administrativa`
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_anonimo_vai_ao_login_sem_registrar(client: Client) -> None:
    unidade = _unidade("IMP-ANON")
    alvo = _perfil(unidade, "9602000", "Alvo Anônimo")
    tipo = _tipo_impedimento("Licença Anônima")

    resposta = client.post(_url_gravar(alvo.pk), _payload(tipo, timezone.localdate()))

    assert resposta.status_code == 302
    assert resposta["Location"].startswith(str(django_settings.LOGIN_URL))
    assert ExecucaoAcao.objects.count() == 0
    assert Impedimento.objects.count() == 0


@banco
@pytest.mark.django_db
def test_sem_competencia_recebe_403_registrado(client: Client) -> None:
    unidade = _unidade("IMP-403")
    comum = _perfil(unidade, "9602100", "Sem Competência")
    alvo = _perfil(unidade, "9602110", "Alvo 403")
    tipo = _tipo_impedimento("Licença 403")

    client.force_login(_fresco(comum))
    resposta = client.post(_url_gravar(alvo.pk), _payload(tipo, timezone.localdate()))

    assert resposta.status_code == 403
    execucao = ExecucaoAcao.objects.get()
    assert execucao.autorizado is False
    assert execucao.perfil_id == comum.pk
    assert Impedimento.objects.count() == 0


@banco
@pytest.mark.django_db
def test_alvo_de_outro_ramo_e_recusado(client: Client) -> None:
    dirigida = _unidade("IMP-RAMO-DIRIGIDA")
    fora = _unidade("IMP-RAMO-FORA")
    dirigente = _dirigente(dirigida, "9602200")
    de_fora = _perfil(fora, "9602210", "Alvo De Fora")
    tipo = _tipo_impedimento("Licença Ramo")

    client.force_login(_fresco(dirigente))
    resposta = client.post(_url_gravar(de_fora.pk), _payload(tipo, timezone.localdate()))

    assert resposta.status_code == 403
    execucao = ExecucaoAcao.objects.get()
    assert execucao.autorizado is False
    assert Impedimento.objects.count() == 0


@banco
@pytest.mark.django_db
def test_unidade_do_alvo_vem_do_banco(client: Client) -> None:
    """A lotação a conferir é lida no banco: mandar a própria unidade no corpo — dentro do alcance
    de quem assina — não abre o servidor de outro ramo."""
    dirigida = _unidade("IMP-FORJA-DIRIGIDA")
    fora = _unidade("IMP-FORJA-FORA")
    dirigente = _dirigente(dirigida, "9602300")
    de_fora = _perfil(fora, "9602310", "Alvo Forjado")
    tipo = _tipo_impedimento("Licença Forjada")

    client.force_login(_fresco(dirigente))
    resposta = client.post(
        _url_gravar(de_fora.pk),
        _payload(tipo, timezone.localdate()) | {"unidade": str(dirigida.pk)},
    )

    assert resposta.status_code == 403
    assert Impedimento.objects.count() == 0


@banco
@pytest.mark.django_db
def test_direcao_em_outra_unidade_nao_alcanca(client: Client) -> None:
    raiz = _unidade("IMP-IRMA-RAIZ")
    primeira = _unidade("IMP-IRMA-PRIMEIRA", pai=raiz)
    segunda = _unidade("IMP-IRMA-SEGUNDA", pai=raiz)
    dirigente_da_segunda = _dirigente(segunda, "9602400")
    alvo = _perfil(primeira, "9602410", "Alvo Irmã")
    tipo = _tipo_impedimento("Licença Irmã")

    client.force_login(_fresco(dirigente_da_segunda))
    resposta = client.post(_url_gravar(alvo.pk), _payload(tipo, timezone.localdate()))

    assert resposta.status_code == 403
    assert Impedimento.objects.filter(perfil=alvo).exists() is False


@banco
@pytest.mark.django_db
def test_impedido_recebe_403_e_exonerado_302(client: Client) -> None:
    """Os dois desfechos são diferentes de propósito: o impedido segue autenticado e o `has_perm`
    o nega; o exonerado (`is_active=False`) o Django nem autentica, e ele chega como anônimo."""
    unidade = _unidade("IMP-FORA")
    impedido = _dirigente(unidade, "9602500", "Titular Impedido")
    alvo = _perfil(unidade, "9602510", "Alvo Fora")
    tipo = _tipo_impedimento("Licença Fora")
    _impedir(impedido, "Licença Do Titular")

    client.force_login(_fresco(impedido))
    resposta = client.post(_url_gravar(alvo.pk), _payload(tipo, timezone.localdate()))
    assert resposta.status_code == 403
    negativas = ExecucaoAcao.objects.filter(autorizado=False).count()

    exonerado = _dirigente(_unidade("IMP-EXON"), "9602520", "Titular Exonerado")
    exonerado.is_active = False
    exonerado.save(update_fields=["is_active"])

    client.force_login(exonerado)
    resposta = client.post(_url_gravar(alvo.pk), _payload(tipo, timezone.localdate()))

    assert resposta.status_code == 302
    assert resposta["Location"].startswith(str(django_settings.LOGIN_URL))
    assert ExecucaoAcao.objects.filter(autorizado=False).count() == negativas
    assert Impedimento.objects.filter(perfil=alvo).exists() is False


@banco
@pytest.mark.django_db
def test_substituto_registra_durante_a_cobertura(client: Client) -> None:
    unidade_titular = _unidade("IMP-SUBST-TITULAR")
    unidade_substituto = _unidade("IMP-SUBST-SUBSTITUTO")
    titular = _dirigente(unidade_titular, "9602600", "Titular Coberto")
    substituto = _perfil(unidade_substituto, "9602610", "Substituto Cobrindo")
    alvo = _perfil(unidade_titular, "9602620", "Alvo Coberto")
    tipo = _tipo_impedimento("Licença Cobertura")
    _cobrir(substituto, titular, "Licença Do Titular Coberto")

    client.force_login(_fresco(substituto))
    resposta = client.post(_url_gravar(alvo.pk), _payload(tipo, timezone.localdate()))

    assert resposta.status_code == 200
    assert Impedimento.objects.filter(perfil=alvo).exists()
    execucao = ExecucaoAcao.objects.get(autorizado=True)
    assert execucao.perfil_id == substituto.pk
    # Cargo e unidade do substituto, no momento do ato — e por quem ele respondia.
    assert execucao.unidade_id == unidade_substituto.pk
    assert execucao.cargo_base_id == substituto.cargo_base_id
    assert execucao.substituindo_id == titular.pk


@banco
@pytest.mark.django_db
def test_ato_grava_quem_cargo_unidade_operacao_e_alvo(client: Client) -> None:
    unidade = _unidade("IMP-REG")
    outra = _unidade("IMP-REG-OUTRA")
    dirigente = _dirigente(unidade, "9602700")
    alvo = _perfil(unidade, "9602710", "Alvo Registro")
    tipo = _tipo_impedimento("Licença Registro")

    client.force_login(_fresco(dirigente))
    resposta = client.post(_url_gravar(alvo.pk), _payload(tipo, timezone.localdate()))
    assert resposta.status_code == 200

    execucao = ExecucaoAcao.objects.get(autorizado=True)
    assert execucao.perfil_id == dirigente.pk
    assert execucao.unidade_id == unidade.pk
    assert execucao.cargo_base_id == dirigente.cargo_base_id
    assert execucao.cargo_comissao_id == dirigente.cargo_comissao_id
    assert execucao.operacao == "registrar"
    assert execucao.alvo_tipo == "servidor"
    assert execucao.alvo_identificador == alvo.rf

    # Mudar a lotação depois não reescreve a linha.
    dirigente.unidade = outra
    dirigente.save(update_fields=["unidade"])
    execucao.refresh_from_db()
    assert execucao.unidade_id == unidade.pk


@banco
@pytest.mark.django_db
def test_registrar_retornar_e_revogar_sao_distinguiveis_no_historico(client: Client) -> None:
    unidade = _unidade("IMP-HIST")
    dirigente = _dirigente(unidade, "9602800")
    alvo = _perfil(unidade, "9602810", "Alvo Histórico")
    tipo = _tipo_impedimento("Licença Histórico")
    hoje = timezone.localdate()

    client.force_login(_fresco(dirigente))
    # Começou ontem: já vigorou, e devolver a cadeira é RETORNO.
    client.post(_url_gravar(alvo.pk), _payload(tipo, hoje - DIA))
    client.post(_url_gravar_retorno(alvo.pk))
    # Começa hoje: não vigorou, e desfazê-lo é REVOGAÇÃO.
    client.post(_url_gravar(alvo.pk), _payload(tipo, hoje))
    client.post(_url_gravar_retorno(alvo.pk))

    operacoes = set(ExecucaoAcao.objects.values_list("operacao", flat=True))
    assert operacoes == {"registrar", "retornar", "revogar"}


@banco
@pytest.mark.django_db
def test_leitura_autorizada_nao_vira_linha(client: Client) -> None:
    unidade = _unidade("IMP-LEITURA")
    outra = _unidade("IMP-LEITURA-OUTRA")
    dirigente = _dirigente(unidade, "9602900")
    alvo = _perfil(unidade, "9602910", "Alvo Leitura")
    _impedir(alvo, "Licença Leitura")
    de_fora = _perfil(outra, "9602920", "Fora Leitura")

    client.force_login(_fresco(dirigente))
    assert client.get(_url_modal(alvo.pk)).status_code == 200
    assert client.get(_url_modal_retorno(alvo.pk)).status_code == 200
    assert client.get(_url_modal_direto()).status_code == 200
    assert client.get(_url_opcoes(), {"unidade": str(unidade.pk)}).status_code == 200
    assert client.get(_url_face(), {"servidor": str(alvo.pk)}).status_code == 200
    assert ExecucaoAcao.objects.count() == 0

    # A mesma leitura, negada: essa fica.
    assert client.get(_url_modal(de_fora.pk)).status_code == 403
    assert ExecucaoAcao.objects.filter(autorizado=False).count() == 1


@banco
@pytest.mark.django_db
def test_escrita_so_por_post(client: Client) -> None:
    unidade = _unidade("IMP-SOPOST")
    dirigente = _dirigente(unidade, "9603000")
    alvo = _perfil(unidade, "9603010", "Alvo SóPost")
    _impedir(alvo, "Licença SóPost")
    tipo = _tipo_impedimento("Licença SóPost Nova")

    client.force_login(_fresco(dirigente))
    registrar = client.get(_url_gravar(alvo.pk), _payload(tipo, timezone.localdate()))
    retornar = client.get(_url_gravar_retorno(alvo.pk))

    assert registrar.status_code == 405
    assert retornar.status_code == 405
    assert ExecucaoAcao.objects.count() == 0
    assert Impedimento.objects.filter(perfil=alvo).count() == 1
    assert _fresco(alvo).em_exercicio is False
