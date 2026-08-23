"""
Testes de apps/user_admin/views.py — `editar_perfil` e `gravar_edicao` (SPEC criacao_usuarios/005):
o modal abre e grava só para quem dirige a unidade de lotação do servidor editado (estrutural, SPEC
autorizacao/003) e a unidade de destino (SPEC autorizacao/004), a recusa volta no modal realçada com
o lápis do campo aberto (SPEC formularios/001), e o sucesso fecha o modal e atualiza a página.

Todos levam o marker `banco`: direção, concessão, alcance e execução são lidos e gravados no banco.
"""

import base64
from datetime import timedelta
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from django.conf import settings as django_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from django.utils import timezone

import pytest
from pytest_django.fixtures import SettingsWrapper

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

SLUG_ACAO = "user_admin.editar_servidor"

# PNG 1x1 real: o ImageField grava no storage e o teste de foto preservada precisa de um arquivo
# de verdade em disco, não de um mock.
PNG_MINIMO = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Editar Servidor",
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
    dados: dict[str, object] = {"nome": "Cargo Editar Servidor", "sigla": "CGES"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _cargo_chefia(nome: str, **overrides: object) -> CargoComissao:
    dados: dict[str, object] = {"sigla": "CDA", "nivel": 1, "e_chefia": True}
    dados.update(overrides)
    return CargoComissao.objects.create(nome=nome, **dados)  # type: ignore[arg-type]


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Editar Servidor",
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
    """Afasta o titular e põe o substituto no lugar: é por aqui que o substituto passa a responder
    pela unidade do titular, além da própria."""
    tipo, _ = TipoImpedimento.objects.get_or_create(nome="Licença Editar Servidor")
    hoje = timezone.localdate()
    impedimento = registrar_impedimento(
        titular,
        NovoImpedimento(tipo=tipo.pk, data_inicio=hoje - timedelta(days=1), data_fim=None),
    )
    designar_substituto(
        impedimento,
        NovaSubstituicao(substituto=substituto.pk, data_inicio=hoje, data_fim=None),
    )


def _conceder(unidade: Unidade, cargo_base: CargoBase) -> Acao:
    acao, _ = Acao.objects.get_or_create(
        slug=SLUG_ACAO,
        defaults={"nome": "Editar servidor", "tooltip": "tt", "estrutural": True},
    )
    atribuicao = AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)
    Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo_base)
    return acao


def _fresco(perfil: Perfil) -> Perfil:
    # O cache de `has_perm` é do objeto Python: cada requisição simulada precisa ver o efeito de
    # uma mudança de estado como uma requisição nova veria.
    return Perfil.objects.get(pk=perfil.pk)


def _url_abrir(servidor_id: int) -> str:
    return reverse("user_admin:editar_perfil", kwargs={"servidor": servidor_id})


def _url_gravar(servidor_id: int) -> str:
    return reverse("user_admin:gravar_edicao", kwargs={"servidor": servidor_id})


def _payload(
    unidade: Unidade,
    cargo: CargoBase,
    rf: str,
    email: str,
    nome: str = "Editado",
    sobrenome: str = "Servidor",
    cargo_comissao: str = "",
) -> dict[str, str]:
    return {
        "unidade": str(unidade.pk),
        "cargo_base": str(cargo.pk),
        "cargo_comissao": cargo_comissao,
        "rf": rf,
        "nome": nome,
        "sobrenome": sobrenome,
        "email": email,
    }


def _controle(soup: BeautifulSoup, tag: str, nome: str) -> Tag:
    controle = soup.find(tag, attrs={"name": nome})
    assert isinstance(controle, Tag), f"a tela não trouxe o {tag} de {nome}"
    return controle


def _lapis_aberto(soup: BeautifulSoup, campo: str) -> bool:
    toggle = soup.find("input", attrs={"id": f"editar-campo-{campo}"})
    assert isinstance(toggle, Tag), f"a tela não trouxe o toggle de {campo}"
    return toggle.has_attr("checked")


# ---------------------------------------------------------------------------
# A gravação altera o cadastro num ato só, e a foto sem arquivo novo permanece
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_gravacao_altera_o_cadastro_num_ato_so(
    client: Client, settings: SettingsWrapper, tmp_path: Path
) -> None:
    settings.MEDIA_ROOT = tmp_path
    raiz = _unidade("EDT-RAIZ")
    origem = _unidade("EDT-ORIGEM", pai=raiz)
    destino = _unidade("EDT-DESTINO", pai=raiz)
    dirigente = _dirigente(raiz, "940100")
    novo_cargo = _cargo_base(nome="Cargo Novo Ato", sigla="CNA")
    alvo = _perfil(origem, "940101", "Antigo")
    alvo.foto.save("retrato.png", SimpleUploadedFile("retrato.png", PNG_MINIMO))
    nome_arquivo = alvo.foto.name

    client.force_login(_fresco(dirigente))
    resposta = client.post(
        _url_gravar(alvo.pk),
        _payload(destino, novo_cargo, "940101", "novo@prefeitura.sp.gov.br", nome="Novo"),
    )

    assert resposta.status_code == 200
    alvo.refresh_from_db()
    assert alvo.nome == "Novo"
    assert alvo.email == "novo@prefeitura.sp.gov.br"
    assert alvo.unidade_id == destino.pk
    assert alvo.cargo_base_id == novo_cargo.pk
    # Nenhum arquivo novo no POST: a foto que já estava gravada permanece intocada.
    assert alvo.foto.name == nome_arquivo


# ---------------------------------------------------------------------------
# Recusa volta no modal, realçada e com o lápis do campo recusado aberto
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_recusa_volta_no_modal_realcada_sem_gravar(client: Client) -> None:
    unidade = _unidade("EDT-REALCE")
    cargo = _cargo_base()
    dirigente = _dirigente(unidade, "940110")
    outro = _perfil(unidade, "940111", "Outro")
    alvo = _perfil(unidade, "940112", "Alvo Realce")

    client.force_login(_fresco(dirigente))

    # RF já usado por outro servidor.
    resposta = client.post(
        _url_gravar(alvo.pk),
        _payload(unidade, cargo, outro.rf, "alvo@prefeitura.sp.gov.br"),
    )
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 422
    assert "Já existe servidor cadastrado com este RF." in html
    assert "campo-realce-erro" in _controle(soup, "input", "rf")["class"]
    assert _lapis_aberto(soup, "rf")
    assert not _lapis_aberto(soup, "nome")
    # O digitado permanece no input; o lado lido segue mostrando o que está gravado.
    assert _controle(soup, "input", "rf")["value"] == outro.rf
    valor_lido = soup.select_one("#editar-campo-rf ~ .campo-onsen-linha .campo-onsen-valor")
    assert valor_lido is not None
    assert valor_lido.get_text(strip=True) == alvo.rf
    alvo.refresh_from_db()
    assert alvo.rf == "940112"

    # Campo em branco e e-mail torto seguem o mesmo caminho: nada é gravado.
    payload_invalido = _payload(unidade, cargo, "940113", "isto não é e-mail")
    payload_invalido["nome"] = ""
    resposta = client.post(_url_gravar(alvo.pk), payload_invalido)
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 422
    assert "Preencha o campo Nome com a quantidade mínima de caracteres." in html
    assert "E-mail inválido: confira o endereço." in html
    assert "campo-realce-erro" in _controle(soup, "input", "nome")["class"]
    assert "campo-realce-erro" in _controle(soup, "input", "email")["class"]
    assert _lapis_aberto(soup, "nome")
    assert _lapis_aberto(soup, "email")
    alvo.refresh_from_db()
    assert alvo.rf == "940112"
    assert alvo.nome == "Alvo Realce"


# ---------------------------------------------------------------------------
# Recusa do titular: motivo na tarja, nenhum controle realçado
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_recusa_do_titular_vai_para_a_tarja(client: Client) -> None:
    raiz = _unidade("EDT-TIT-RAIZ")
    origem = _unidade("EDT-TIT-ORIGEM", pai=raiz)
    tipo_alta = TipoUnidade.objects.create(
        nome="Tipo Alta Administração Editar",
        nivel=20,
        pode_ser_raiz=True,
        exige_alta_administracao=True,
        nivel_minimo_titular=None,
    )
    destino = Unidade.objects.create(nome="Destino Alta", sigla="EDT-TIT-DEST", tipo=tipo_alta, pai=raiz)
    dirigente = _dirigente(raiz, "940120")
    cargo_normal = _cargo_chefia("Diretor Titular Editar")
    titular = _perfil(origem, "940121", "Titular Editado", cargo_comissao=cargo_normal)
    definir_titular(titular)

    client.force_login(_fresco(dirigente))
    resposta = client.post(
        _url_gravar(titular.pk),
        _payload(
            destino,
            titular.cargo_base,
            titular.rf,
            "titular@prefeitura.sp.gov.br",
            nome=titular.nome,
            cargo_comissao=str(cargo_normal.pk),
        ),
    )
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 422
    assert "O titular precisa de cargo em comissão de chefia compatível com o porte da unidade." in html
    for campo in ("rf", "nome", "sobrenome", "email", "unidade", "cargo_base", "cargo_comissao"):
        assert "campo-realce-erro" not in _controle(
            soup, "select" if campo in {"unidade", "cargo_base", "cargo_comissao"} else "input", campo
        )["class"]
    titular.refresh_from_db()
    assert titular.unidade_id == origem.pk


# ---------------------------------------------------------------------------
# Sucesso: o modal fecha e a página se atualiza sem recarregar
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_sucesso_fecha_o_modal_e_atualiza_a_pagina(client: Client) -> None:
    unidade = _unidade("EDT-SUCESSO")
    cargo = _cargo_base()
    dirigente = _dirigente(unidade, "940130")

    client.force_login(_fresco(dirigente))
    resposta = client.post(
        _url_gravar(dirigente.pk),
        _payload(
            unidade,
            cargo,
            "940130",
            "atualizado@prefeitura.sp.gov.br",
            nome="Atualizado",
            cargo_comissao=str(dirigente.cargo_comissao_id),
        ),
    )
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert 'id="modal-editar-perfil"' not in html
    assert 'id="painel-servidor"' in html
    assert 'hx-swap-oob="outerHTML"' in html
    assert "Atualizado" in html


# ---------------------------------------------------------------------------
# O botão de editar só aparece a quem tem a competência e o alcance
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_botao_de_editar_so_aparece_para_quem_pode(client: Client) -> None:
    unidade = _unidade("EDT-BOTAO")
    outro_ramo = _unidade("EDT-BOTAO-FORA")
    dirigente = _dirigente(unidade, "940140")
    sem_direcao = _perfil(outro_ramo, "940141", "Sem Direção")

    client.force_login(_fresco(dirigente))
    html = client.get(reverse("user_admin:pagina_perfil", kwargs={"pk": dirigente.pk})).content.decode()
    assert "Editar servidor" in html
    assert _url_abrir(dirigente.pk) in html

    client.force_login(_fresco(sem_direcao))
    html = client.get(reverse("user_admin:pagina_perfil", kwargs={"pk": dirigente.pk})).content.decode()
    assert "Editar servidor" not in html
    assert _url_abrir(dirigente.pk) not in html


# ---------------------------------------------------------------------------
# Barreira de autenticação e de competência
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_anonimo_vai_para_o_login_sem_deixar_linha(client: Client) -> None:
    alvo = _perfil(_unidade("EDT-ANON"), "940150", "Alvo Anônimo")

    resposta = client.get(_url_abrir(alvo.pk))

    assert resposta.status_code == 302
    assert resposta["Location"].startswith(str(django_settings.LOGIN_URL))
    assert ExecucaoAcao.objects.count() == 0


@banco
@pytest.mark.django_db
def test_autenticado_sem_competencia_recebe_403_registrado(client: Client) -> None:
    unidade = _unidade("EDT-403")
    perfil = _perfil(unidade, "940160", "Sem Competência")
    alvo = _perfil(_unidade("EDT-403-ALVO"), "940161", "Alvo 403")

    client.force_login(perfil)
    resposta = client.get(_url_abrir(alvo.pk))

    assert resposta.status_code == 403
    execucao = ExecucaoAcao.objects.get()
    assert execucao.autorizado is False


# ---------------------------------------------------------------------------
# Estrutural × concessão em outra unidade
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_estrutural_libera_quem_dirige_sem_concessao(client: Client) -> None:
    unidade = _unidade("EDT-ESTR")
    titular = _dirigente(unidade, "940170", "Titular Estrutural")
    outra = _unidade("EDT-ESTR-OUTRA")
    substituto = _perfil(outra, "940171", "Substituto Estrutural")

    client.force_login(titular)
    assert client.get(_url_abrir(titular.pk)).status_code == 200

    # Afastado o titular, quem responde pela direção é o substituto — e a tela é dele enquanto durar.
    _cobrir(substituto, titular)
    client.force_login(_fresco(substituto))
    assert client.get(_url_abrir(titular.pk)).status_code == 200

    client.force_login(_fresco(titular))
    assert client.get(_url_abrir(titular.pk)).status_code == 403


@banco
@pytest.mark.django_db
def test_concessao_em_outra_unidade_nao_libera(client: Client) -> None:
    superior = _unidade("EDT-CONC-SUP")
    subordinada = _unidade("EDT-CONC-SUB", pai=superior)
    cargo = _cargo_base(nome="Cargo Concessão Alheia Editar", sigla="CCAE")
    perfil = _perfil(subordinada, "940180", "Concessão Alheia", cargo_base=cargo)
    # A mesma ação, concedida ao mesmo cargo — mas na unidade superior, não na do perfil.
    _conceder(superior, cargo)

    client.force_login(perfil)
    assert client.get(_url_abrir(perfil.pk)).status_code == 403


# ---------------------------------------------------------------------------
# Fora de exercício não exerce, ainda que dirija no papel
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_perfil_fora_de_exercicio_nao_exerce(client: Client) -> None:
    impedido = _dirigente(_unidade("EDT-IMPEDIDO"), "940190", "Titular Impedido")
    tipo, _ = TipoImpedimento.objects.get_or_create(nome="Licença Sem Cobertura Editar Servidor")
    registrar_impedimento(
        impedido,
        NovoImpedimento(
            tipo=tipo.pk, data_inicio=timezone.localdate() - timedelta(days=1), data_fim=None
        ),
    )
    client.force_login(_fresco(impedido))
    assert client.get(_url_abrir(impedido.pk)).status_code == 403

    exonerado = _dirigente(_unidade("EDT-EXONERADO"), "940191", "Titular Exonerado")
    exonerado.is_active = False
    exonerado.save(update_fields=["is_active"])
    client.force_login(exonerado)
    resposta = client.get(_url_abrir(exonerado.pk))
    assert resposta.status_code == 302
    assert resposta["Location"].startswith(str(django_settings.LOGIN_URL))


# ---------------------------------------------------------------------------
# O alcance vem da lotação do servidor, lida do banco — nunca do request
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_alcance_vem_da_lotacao_do_servidor(client: Client) -> None:
    dirigida = _unidade("EDT-ALC-DIRIGIDA")
    fora = _unidade("EDT-ALC-FORA")
    dirigente = _dirigente(dirigida, "940200")
    dentro = _perfil(dirigida, "940201", "Dentro do Alcance")
    de_fora = _perfil(fora, "940202", "Fora do Alcance")

    client.force_login(_fresco(dirigente))
    assert client.get(_url_abrir(dentro.pk)).status_code == 200

    resposta = client.get(_url_abrir(de_fora.pk))
    assert resposta.status_code == 403
    execucao = ExecucaoAcao.objects.get(autorizado=False)
    assert execucao.perfil_id == dirigente.pk


@banco
@pytest.mark.django_db
def test_unidade_forjada_no_request_nao_abre_servidor_alheio(client: Client) -> None:
    dirigida = _unidade("EDT-FORJA-DIRIGIDA")
    fora = _unidade("EDT-FORJA-FORA")
    cargo = _cargo_base()
    dirigente = _dirigente(dirigida, "940210")
    de_fora = _perfil(fora, "940211", "Alheio Forjado")

    client.force_login(_fresco(dirigente))
    # Manda a PRÓPRIA unidade — dentro do alcance de quem grava — mas o alvo continua sendo o
    # servidor de fora: a origem é lida do banco, e mandar o destino certo não muda isso.
    resposta = client.post(
        _url_gravar(de_fora.pk),
        _payload(dirigida, cargo, "940211", "forjado@prefeitura.sp.gov.br"),
    )

    assert resposta.status_code == 403
    de_fora.refresh_from_db()
    assert de_fora.unidade_id == fora.pk


# ---------------------------------------------------------------------------
# Mover para fora do alcance é recusado, mesmo com a origem dentro dele
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_mover_para_fora_do_alcance_e_recusado(client: Client) -> None:
    dirigida = _unidade("EDT-MOVER-DIRIGIDA")
    fora = _unidade("EDT-MOVER-FORA")
    cargo = _cargo_base()
    dirigente = _dirigente(dirigida, "940220")

    client.force_login(_fresco(dirigente))
    resposta = client.post(
        _url_gravar(dirigente.pk),
        _payload(fora, cargo, dirigente.rf, "mover@prefeitura.sp.gov.br"),
    )

    assert resposta.status_code == 403
    dirigente.refresh_from_db()
    assert dirigente.unidade_id == dirigida.pk


@banco
@pytest.mark.django_db
def test_gravar_sem_o_parametro_do_alvo_e_400(client: Client) -> None:
    dirigida = _unidade("EDT-400")
    dirigente = _dirigente(dirigida, "940230")
    payload = _payload(dirigida, dirigente.cargo_base, dirigente.rf, "quatrocentos@prefeitura.sp.gov.br")
    del payload["unidade"]

    client.force_login(_fresco(dirigente))
    antes = ExecucaoAcao.objects.count()
    resposta = client.post(_url_gravar(dirigente.pk), payload)

    assert resposta.status_code == 400
    assert ExecucaoAcao.objects.count() == antes


# ---------------------------------------------------------------------------
# Ação inativa não libera ninguém, mesmo dirigindo a unidade
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_acao_inativa_nao_libera_ninguem() -> None:
    """O alcance desta ação é sempre conferido — `servidor` vem do caminho, nunca ausente —, então
    só quem dirige chega perto de abrir a tela, e a estrutural não olha para `Acao.ativa`
    (avaliador.py: "ação inativa é a que saiu do registro"). O que a inativação desliga é a
    COMPETÊNCIA por concessão, e é isso que este teste fixa diretamente — como a suíte da SPEC
    autorizacao/003 já faz para o backend em geral, sem depender de um alcance que um perfil só
    com concessão (sem dirigir unidade alguma) nunca teria como satisfazer nesta ação."""
    unidade = _unidade("EDT-INATIVA")
    cargo = _cargo_base(nome="Cargo Concessão Inativa Editar", sigla="CCIE")
    perfil = _perfil(unidade, "940240", "Concessão Sem Direção Editar", cargo_base=cargo)
    _conceder(unidade, cargo)

    assert _fresco(perfil).has_perm(SLUG_ACAO) is True

    acao = Acao.objects.get(slug=SLUG_ACAO)
    acao.ativa = False
    acao.save(update_fields=["ativa"])
    assert _fresco(perfil).has_perm(SLUG_ACAO) is False


# ---------------------------------------------------------------------------
# O que fica registrado: lotação do momento, substituição e distinção leitura × escrita
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_execucao_registrada_com_a_lotacao_do_momento(client: Client) -> None:
    origem = _unidade("EDT-REG-ORIGEM")
    destino = _unidade("EDT-REG-DESTINO")
    dirigente = _dirigente(origem, "940250")

    client.force_login(_fresco(dirigente))
    resposta = client.post(
        _url_gravar(dirigente.pk),
        _payload(
            origem,
            dirigente.cargo_base,
            dirigente.rf,
            "registrado@prefeitura.sp.gov.br",
            cargo_comissao=str(dirigente.cargo_comissao_id),
        ),
    )
    assert resposta.status_code == 200

    execucao = ExecucaoAcao.objects.get(operacao="editar")
    assert execucao.perfil_id == dirigente.pk
    assert execucao.unidade_id == origem.pk
    assert execucao.alvo_tipo == "servidor"
    assert execucao.alvo_identificador == dirigente.rf

    dirigente.unidade = destino
    dirigente.save(update_fields=["unidade"])
    execucao.refresh_from_db()
    assert execucao.unidade_id == origem.pk


@banco
@pytest.mark.django_db
def test_ato_em_substituicao_diz_por_quem_responde(client: Client) -> None:
    unidade_titular = _unidade("EDT-SUBST-TITULAR")
    unidade_substituto = _unidade("EDT-SUBST-SUBSTITUTO")
    titular = _dirigente(unidade_titular, "940260", "Titular Substituído Editar")
    substituto = _dirigente(unidade_substituto, "940261", "Substituto Que Também Dirige Editar")

    # Por competência própria: age sobre o próprio cadastro.
    client.force_login(substituto)
    resposta = client.post(
        _url_gravar(substituto.pk),
        _payload(
            unidade_substituto,
            substituto.cargo_base,
            substituto.rf,
            "propria@prefeitura.sp.gov.br",
            cargo_comissao=str(substituto.cargo_comissao_id),
        ),
    )
    assert resposta.status_code == 200
    propria = ExecucaoAcao.objects.get(alvo_identificador=substituto.rf)
    assert propria.substituindo_id is None

    # Cobrindo o titular afastado: o registro diz por quem ele respondia, e o alvo é o próprio
    # titular — a unidade dele entra no alcance do substituto pela cobertura.
    _cobrir(substituto, titular)
    client.force_login(_fresco(substituto))
    resposta = client.post(
        _url_gravar(titular.pk),
        _payload(
            unidade_titular,
            titular.cargo_base,
            titular.rf,
            "coberto@prefeitura.sp.gov.br",
            cargo_comissao=str(titular.cargo_comissao_id),
        ),
    )
    assert resposta.status_code == 200
    coberta = ExecucaoAcao.objects.get(alvo_identificador=titular.rf)
    assert coberta.substituindo_id == titular.pk


@banco
@pytest.mark.django_db
def test_abrir_o_modal_nao_vira_registro(client: Client) -> None:
    unidade = _unidade("EDT-LEITURA")
    outra = _unidade("EDT-LEITURA-OUTRA")
    dirigente = _dirigente(unidade, "940270")
    sem_competencia = _perfil(outra, "940271", "Sem Competência Leitura Editar")

    client.force_login(_fresco(dirigente))
    assert client.get(_url_abrir(dirigente.pk)).status_code == 200
    assert ExecucaoAcao.objects.count() == 0

    client.force_login(_fresco(sem_competencia))
    assert client.get(_url_abrir(dirigente.pk)).status_code == 403
    assert ExecucaoAcao.objects.count() == 1


# ---------------------------------------------------------------------------
# Gravação só por POST
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_gravacao_so_por_post(client: Client) -> None:
    unidade = _unidade("EDT-SOPOST")
    dirigente = _dirigente(unidade, "940280")

    client.force_login(_fresco(dirigente))
    resposta = client.get(_url_gravar(dirigente.pk), {"unidade": str(unidade.pk)})

    assert resposta.status_code == 405
    assert ExecucaoAcao.objects.count() == 0
    dirigente.refresh_from_db()
    assert dirigente.unidade_id == unidade.pk
