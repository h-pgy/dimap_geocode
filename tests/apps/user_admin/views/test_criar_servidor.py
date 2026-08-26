"""
Testes de apps/user_admin/views.py — `criar_perfil` e `gravar_servidor` (SPEC criacao_usuarios/004):
o formulário abre só para quem dirige a unidade (estrutural, SPEC autorizacao/003), oferece apenas o
alcance de quem abre (SPEC autorizacao/004), e o POST grava o servidor e a execução do ato.

A entrega do e-mail é real (`EnviadorSmtp`), mas desligada por configuração nos testes que chegam a
gravar: o que este arquivo fixa é quem pratica o ato e o que fica registrado, não o envio em si
(SPEC 001) — esse é o `tests/apps/user_admin/test_cadastro.py`.

Todos levam o marker `banco`: direção, concessão e execução são lidas e gravadas no banco.
"""

from datetime import timedelta
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from django.conf import settings as django_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from pydantic import SecretStr

import pytest
from pytest_django.fixtures import SettingsWrapper

from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao, ExecucaoAcao
from apps.user_admin import cadastro
from apps.user_admin.exercicio import designar_substituto, registrar_impedimento
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, CargoComissao, Perfil, TipoImpedimento
from apps.user_admin.schemas import NovaSubstituicao, NovoImpedimento
from apps.unidades.titularidade import definir_titular
from services.utils.smtp import ResultadoEnvio

banco = pytest.mark.banco

SLUG_ACAO = "user_admin.criar_servidor"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Criar Servidor",
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
    dados: dict[str, object] = {"nome": "Cargo Criar Servidor", "sigla": "CGCS"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _cargo_chefia(nome: str) -> CargoComissao:
    return CargoComissao.objects.create(nome=nome, sigla="CDA", nivel=1, e_chefia=True)


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Criar Servidor",
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
    tipo, _ = TipoImpedimento.objects.get_or_create(nome="Licença Criar Servidor")
    hoje = timezone.localdate()
    impedimento = registrar_impedimento(
        titular,
        NovoImpedimento(tipo=tipo.pk, data_inicio=hoje - timedelta(days=1), data_fim=None),
    )
    designar_substituto(
        impedimento,
        NovaSubstituicao(substituto=substituto.pk, data_inicio=hoje, data_fim=None),
    )


def _superusuario(rf: str) -> Perfil:
    return Perfil.objects.create_superuser(
        rf=rf,
        nome="Super",
        sobrenome="Usuário",
        password="segredo123",
        unidade=_unidade(f"CRS-SU-{rf}"),
        cargo_base=_cargo_base(),
    )


def _conceder(unidade: Unidade, cargo_base: CargoBase) -> Acao:
    acao, _ = Acao.objects.get_or_create(
        slug=SLUG_ACAO,
        defaults={"nome": "Cadastrar servidor", "tooltip": "tt", "estrutural": True},
    )
    atribuicao = AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)
    Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo_base)
    return acao


def _fresco(perfil: Perfil) -> Perfil:
    # O cache de `has_perm` é do objeto Python: cada requisição simulada precisa ver o efeito de
    # uma mudança de estado como uma requisição nova veria.
    return Perfil.objects.get(pk=perfil.pk)


def _url_form() -> str:
    return reverse("user_admin:criar_perfil")


def _url_gravar() -> str:
    return reverse("user_admin:gravar_servidor")


def _payload(unidade: Unidade, cargo: CargoBase, rf: str, email: str) -> dict[str, str]:
    return {
        "unidade": str(unidade.pk),
        "cargo_base": str(cargo.pk),
        "cargo_comissao": "",
        "rf": rf,
        "nome": "Novo",
        "sobrenome": "Servidor",
        "email": email,
    }


def _desligar_envio(settings: SettingsWrapper) -> None:
    """Cadastro que chega a gravar precisa concluir sem rede: SMTP desligado por configuração é o
    ambiente de desenvolvimento (SPEC 004, Caveats), e é o que estes testes de autorização usam."""
    settings.EMAIL_ENVIO_HABILITADO = False
    settings.EMAIL_SMTP_USUARIO = "dimap.geocoder@example.com"
    settings.ENFORCE_PREFEITURA_EMAIL = False


def _controle(soup: BeautifulSoup, tag: str, nome: str) -> Tag:
    controle = soup.find(tag, attrs={"name": nome})
    assert isinstance(controle, Tag), f"a tela não trouxe o {tag} de {nome}"
    return controle


def _siglas_do_select(soup: BeautifulSoup) -> set[str]:
    select = soup.find("select", attrs={"name": "unidade"})
    assert select is not None, "a tela não trouxe o select de unidade"
    return {opcao.get_text(strip=True).split(" · ")[0] for opcao in select.find_all("option")}


# ---------------------------------------------------------------------------
# O formulário oferece só o alcance de quem abre
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_formulario_oferece_so_as_unidades_do_alcance(client: Client) -> None:
    raiz = _unidade("CRS-RAIZ")
    meio = _unidade("CRS-MEIO", pai=raiz)
    _unidade("CRS-BAIXO", pai=meio)
    _unidade("CRS-TIA", pai=raiz)
    outro_ramo = _unidade("CRS-FORA")
    dirigente = _dirigente(meio, "9301000")
    sem_direcao = _perfil(outro_ramo, "9301010", "Sem Direção")

    client.force_login(dirigente)
    soup = BeautifulSoup(client.get(_url_form()).content.decode(), "html.parser")
    assert _siglas_do_select(soup) == {"CRS-MEIO", "CRS-BAIXO"}

    client.force_login(sem_direcao)
    assert client.get(_url_form()).status_code == 403


# ---------------------------------------------------------------------------
# A listagem só oferece "Novo servidor" a quem pode criar
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_listagem_so_oferece_novo_servidor_a_quem_pode(client: Client) -> None:
    unidade = _unidade("CRS-LISTA")
    outro = _unidade("CRS-LISTA-OUTRO")
    dirigente = _dirigente(unidade, "9301100")
    sem_direcao = _perfil(outro, "9301110", "Sem Direção Lista")
    url_listagem = reverse("user_admin:listar_servidores")

    client.force_login(dirigente)
    assert "Novo servidor" in client.get(url_listagem).content.decode()

    client.force_login(sem_direcao)
    assert "Novo servidor" not in client.get(url_listagem).content.decode()


# ---------------------------------------------------------------------------
# Recusa devolve o próprio formulário, preenchido e realçado
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_campo_invalido_devolve_o_formulario_realcado(
    client: Client, settings: SettingsWrapper
) -> None:
    _desligar_envio(settings)
    unidade = _unidade("CRS-REALCE")
    cargo = _cargo_base()
    dirigente = _dirigente(unidade, "9302400")
    payload = _payload(unidade, cargo, "9302410", "isto não é e-mail")
    payload["nome"] = ""

    client.force_login(dirigente)
    resposta = client.post(_url_gravar(), payload)
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 422
    # Campo em branco com BeforeValidator erra por comprimento GENÉRICO (`too_short`), não por
    # `missing` nem por formato: a frase continua sendo a de obrigatoriedade (SPEC 006).
    assert "Preencha o campo Nome." in html
    assert "E-mail inválido: confira o endereço." in html
    # O realce é do controle recusado, e só dele.
    assert "campo-realce-erro" in _controle(soup, "input", "nome")["class"]
    assert "campo-realce-erro" in _controle(soup, "input", "email")["class"]
    assert "campo-realce-erro" not in _controle(soup, "input", "rf")["class"]
    # O que já estava digitado permanece, e o select mantém a escolha.
    assert _controle(soup, "input", "rf")["value"] == "9302410"
    escolhida = soup.find("option", attrs={"value": str(unidade.pk)})
    assert isinstance(escolhida, Tag)
    assert escolhida.has_attr("selected")
    assert not Perfil.objects.filter(rf="9302410").exists()


# ---------------------------------------------------------------------------
# Barreira de autenticação e de competência
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_anonimo_vai_para_o_login_sem_deixar_linha(client: Client) -> None:
    resposta = client.get(_url_form())

    assert resposta.status_code == 302
    assert resposta["Location"].startswith(str(django_settings.LOGIN_URL))
    assert ExecucaoAcao.objects.count() == 0


@banco
@pytest.mark.django_db
def test_autenticado_sem_competencia_recebe_403_registrado(client: Client) -> None:
    unidade = _unidade("CRS-403")
    perfil = _perfil(unidade, "9301200", "Sem Competência")

    client.force_login(perfil)
    resposta = client.get(_url_form())

    assert resposta.status_code == 403
    execucao = ExecucaoAcao.objects.get()
    assert execucao.autorizado is False


# ---------------------------------------------------------------------------
# Estrutural × concessão em outra unidade
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_estrutural_libera_quem_dirige_sem_concessao(client: Client) -> None:
    unidade = _unidade("CRS-ESTR")
    titular = _dirigente(unidade, "9301300", "Titular Estrutural")
    outra = _unidade("CRS-ESTR-OUTRA")
    substituto = _perfil(outra, "9301310", "Substituto Estrutural")

    client.force_login(titular)
    assert client.get(_url_form()).status_code == 200

    # Afastado o titular, quem responde pela direção é o substituto — e a tela é dele enquanto durar.
    _cobrir(substituto, titular)
    client.force_login(_fresco(substituto))
    assert client.get(_url_form()).status_code == 200

    client.force_login(_fresco(titular))
    assert client.get(_url_form()).status_code == 403


@banco
@pytest.mark.django_db
def test_concessao_em_outra_unidade_nao_libera(client: Client) -> None:
    superior = _unidade("CRS-CONC-SUP")
    subordinada = _unidade("CRS-CONC-SUB", pai=superior)
    cargo = _cargo_base(nome="Cargo Concessão Alheia", sigla="CCA")
    perfil = _perfil(subordinada, "9301400", "Concessão Alheia", cargo_base=cargo)
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
    impedido = _dirigente(_unidade("CRS-IMPEDIDO"), "9301500", "Titular Impedido")
    tipo, _ = TipoImpedimento.objects.get_or_create(nome="Licença Sem Cobertura Criar Servidor")
    registrar_impedimento(
        impedido,
        NovoImpedimento(
            tipo=tipo.pk, data_inicio=timezone.localdate() - timedelta(days=1), data_fim=None
        ),
    )
    client.force_login(_fresco(impedido))
    assert client.get(_url_form()).status_code == 403

    # Exonerado não é "autenticado sem competência": `is_active=False` já significa "inclusive não
    # entrar" desde a SPEC user_admin/001 (Perfil.exonerado) — o ModelBackend do Django derruba a
    # sessão a cada request, e o exonerado chega ao decorator como anônimo, não como Perfil.
    exonerado = _dirigente(_unidade("CRS-EXONERADO"), "9301510", "Titular Exonerado")
    exonerado.is_active = False
    exonerado.save(update_fields=["is_active"])
    client.force_login(exonerado)
    resposta = client.get(_url_form())
    assert resposta.status_code == 302
    assert resposta["Location"].startswith(str(django_settings.LOGIN_URL))


# ---------------------------------------------------------------------------
# O alcance no POST: alvo fora do ramo, e o parâmetro obrigatório
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_gravar_recusa_unidade_fora_do_alcance(client: Client) -> None:
    dirigida = _unidade("CRS-ALC-DIRIGIDA")
    fora = _unidade("CRS-ALC-FORA")
    cargo = _cargo_base()
    dirigente = _dirigente(dirigida, "9301600")

    client.force_login(dirigente)
    resposta = client.post(
        _url_gravar(), _payload(fora, cargo, "9301610", "fora@prefeitura.sp.gov.br")
    )

    assert resposta.status_code == 403
    assert not Perfil.objects.filter(rf="9301610").exists()


@banco
@pytest.mark.django_db
def test_gravar_sem_o_parametro_do_alvo_e_400(client: Client) -> None:
    dirigida = _unidade("CRS-400")
    cargo = _cargo_base()
    dirigente = _dirigente(dirigida, "9301700")
    payload = _payload(dirigida, cargo, "9301710", "quatrocentos@prefeitura.sp.gov.br")
    del payload["unidade"]

    client.force_login(dirigente)
    antes = ExecucaoAcao.objects.count()
    resposta = client.post(_url_gravar(), payload)

    assert resposta.status_code == 400
    assert ExecucaoAcao.objects.count() == antes
    assert not Perfil.objects.filter(rf="9301710").exists()


# ---------------------------------------------------------------------------
# Ação inativa não libera ninguém, mesmo com concessão gravada
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_acao_inativa_nao_libera_ninguem(client: Client) -> None:
    unidade = _unidade("CRS-INATIVA")
    cargo = _cargo_base(nome="Cargo Concessão Inativa", sigla="CCI")
    perfil = _perfil(unidade, "9301800", "Concessão Sem Direção", cargo_base=cargo)
    acao = _conceder(unidade, cargo)

    client.force_login(perfil)
    assert client.get(_url_form()).status_code == 200

    acao.ativa = False
    acao.save(update_fields=["ativa"])
    client.force_login(_fresco(perfil))
    assert client.get(_url_form()).status_code == 403


# ---------------------------------------------------------------------------
# O que fica registrado: lotação do momento, substituição e distinção leitura × escrita
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_execucao_registrada_com_a_lotacao_do_momento(
    client: Client, settings: SettingsWrapper
) -> None:
    _desligar_envio(settings)
    origem = _unidade("CRS-REG-ORIGEM")
    destino = _unidade("CRS-REG-DESTINO")
    cargo = _cargo_base()
    dirigente = _dirigente(origem, "9301900")

    client.force_login(dirigente)
    resposta = client.post(
        _url_gravar(), _payload(origem, cargo, "9301910", "registrado@prefeitura.sp.gov.br")
    )
    assert resposta.status_code == 200

    execucao = ExecucaoAcao.objects.get(operacao="criar")
    assert execucao.perfil_id == dirigente.pk
    assert execucao.unidade_id == origem.pk
    assert execucao.alvo_tipo == "servidor"
    assert execucao.alvo_identificador == "9301910"

    dirigente.unidade = destino
    dirigente.save(update_fields=["unidade"])
    execucao.refresh_from_db()
    assert execucao.unidade_id == origem.pk


@banco
@pytest.mark.django_db
def test_ato_em_substituicao_diz_por_quem_responde(
    client: Client, settings: SettingsWrapper
) -> None:
    _desligar_envio(settings)
    unidade_titular = _unidade("CRS-SUBST-TITULAR")
    unidade_substituto = _unidade("CRS-SUBST-SUBSTITUTO")
    titular = _dirigente(unidade_titular, "9302000", "Titular Substituído")
    substituto = _dirigente(unidade_substituto, "9302010", "Substituto Que Também Dirige")
    cargo = _cargo_base()

    # Por competência própria: age sobre a unidade que ele mesmo dirige.
    client.force_login(substituto)
    resposta = client.post(
        _url_gravar(), _payload(unidade_substituto, cargo, "9302020", "propria@prefeitura.sp.gov.br")
    )
    assert resposta.status_code == 200
    propria = ExecucaoAcao.objects.get(alvo_identificador="9302020")
    assert propria.substituindo_id is None

    # Cobrindo o titular afastado: o registro diz por quem ele respondia.
    _cobrir(substituto, titular)
    client.force_login(_fresco(substituto))
    resposta = client.post(
        _url_gravar(), _payload(unidade_titular, cargo, "9302030", "coberto@prefeitura.sp.gov.br")
    )
    assert resposta.status_code == 200
    coberta = ExecucaoAcao.objects.get(alvo_identificador="9302030")
    assert coberta.substituindo_id == titular.pk


@banco
@pytest.mark.django_db
def test_leitura_autorizada_nao_vira_registro(client: Client) -> None:
    unidade = _unidade("CRS-LEITURA")
    outra = _unidade("CRS-LEITURA-OUTRA")
    dirigente = _dirigente(unidade, "9302100")
    sem_competencia = _perfil(outra, "9302110", "Sem Competência Leitura")

    client.force_login(dirigente)
    assert client.get(_url_form()).status_code == 200
    assert ExecucaoAcao.objects.count() == 0

    client.force_login(sem_competencia)
    assert client.get(_url_form()).status_code == 403
    assert ExecucaoAcao.objects.count() == 1


# ---------------------------------------------------------------------------
# A senha não vaza para o registro do ato, com envio ligado ou desligado
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_senha_nao_aparece_no_registro_do_ato(
    client: Client,
    settings: SettingsWrapper,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _desligar_envio(settings)
    senha_fixa = SecretStr("87654321")
    monkeypatch.setattr(cadastro, "gerar_senha_temporaria", lambda *args, **kwargs: senha_fixa)
    unidade = _unidade("CRS-SENHA")
    cargo = _cargo_base()
    dirigente = _dirigente(unidade, "9302200")

    client.force_login(dirigente)
    resposta = client.post(
        _url_gravar(), _payload(unidade, cargo, "9302210", "senha@prefeitura.sp.gov.br")
    )

    assert resposta.status_code == 200
    execucao = ExecucaoAcao.objects.get(alvo_identificador="9302210")
    assert "87654321" not in execucao.operacao
    assert "87654321" not in execucao.alvo_identificador


# ---------------------------------------------------------------------------
# Gravação só por POST
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_gravacao_so_por_post(client: Client) -> None:
    unidade = _unidade("CRS-SOPOST")
    dirigente = _dirigente(unidade, "9302300")

    client.force_login(dirigente)
    resposta = client.get(_url_gravar(), {"unidade": str(unidade.pk)})

    assert resposta.status_code == 405
    assert ExecucaoAcao.objects.count() == 0
    assert Perfil.objects.filter(unidade=unidade).count() == 1  # só o próprio dirigente


# ---------------------------------------------------------------------------
# Cada formato erra com a frase do seu campo
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_recusa_de_formato_volta_realcada_no_controle_certo(
    client: Client, settings: SettingsWrapper
) -> None:
    _desligar_envio(settings)
    unidade = _unidade("CRS-FORMATO")
    cargo = _cargo_base()
    dirigente = _dirigente(unidade, "9302600")
    # RF de seis dígitos e nome numérico passam pela obrigatoriedade: é o formato que os recusa.
    payload = _payload(unidade, cargo, "930261", "formato@prefeitura.sp.gov.br")
    payload["nome"] = "12345"

    client.force_login(dirigente)
    resposta = client.post(_url_gravar(), payload)
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 422
    assert "RF: sete dígitos, com ou sem pontuação (812.345-6)." in html
    assert "Nome: só letras, espaço, hífen e apóstrofo." in html
    assert "campo-realce-erro" in _controle(soup, "input", "rf")["class"]
    assert "campo-realce-erro" in _controle(soup, "input", "nome")["class"]
    assert "campo-realce-erro" not in _controle(soup, "input", "sobrenome")["class"]
    assert not Perfil.objects.filter(email="formato@prefeitura.sp.gov.br").exists()


# ---------------------------------------------------------------------------
# A foto é conferida antes de virar arquivo no disco
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_foto_invalida_e_recusada_sem_gravar_o_cadastro(
    client: Client, settings: SettingsWrapper, tmp_path: Path
) -> None:
    # MEDIA_ROOT no tmp_path: se a conferência falhar, o arquivo indevido não vai para a árvore
    # do projeto — e é justamente essa gravação que o teste diz não poder acontecer.
    settings.MEDIA_ROOT = tmp_path
    _desligar_envio(settings)
    unidade = _unidade("CRS-FOTO")
    cargo = _cargo_base()
    dirigente = _dirigente(unidade, "9302700")
    payload = _payload(unidade, cargo, "9302710", "foto@prefeitura.sp.gov.br")

    client.force_login(dirigente)
    nao_e_imagem = SimpleUploadedFile("retrato.png", b"isto e texto", content_type="image/png")
    resposta = client.post(_url_gravar(), {**payload, "foto": nao_e_imagem})
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 422
    assert "O arquivo enviado não é uma imagem." in html
    assert "campo-realce-erro" in _controle(soup, "input", "foto")["class"]
    assert not Perfil.objects.filter(rf="9302710").exists()

    acima_do_limite = SimpleUploadedFile(
        "retrato.png",
        b"\0" * (2 * 1024 * 1024 + 1),
        content_type="image/png",
    )
    resposta = client.post(_url_gravar(), {**payload, "foto": acima_do_limite})

    assert resposta.status_code == 422
    assert "Foto acima de 2 MB: envie uma imagem menor." in resposta.content.decode()
    assert not Perfil.objects.filter(rf="9302710").exists()


# ---------------------------------------------------------------------------
# A marca de administrador registra operação própria (SPEC user_admin/022)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_cadastro_com_marca_registra_operacao_propria(
    client: Client, settings: SettingsWrapper
) -> None:
    _desligar_envio(settings)
    unidade = _unidade("CRS-ADMIN")
    cargo = _cargo_base()
    superusuario = _superusuario("9302800")

    client.force_login(superusuario)
    resposta = client.post(
        _url_gravar(),
        {
            **_payload(unidade, cargo, "9302810", "novo.admin@prefeitura.sp.gov.br"),
            "administrador": "1",
        },
    )
    assert resposta.status_code == 200
    execucao_admin = ExecucaoAcao.objects.get(alvo_identificador="9302810")
    assert execucao_admin.operacao == "criar_administrador"
    assert Perfil.objects.get(rf="9302810").is_superuser is True

    resposta_comum = client.post(
        _url_gravar(), _payload(unidade, cargo, "9302820", "comum@prefeitura.sp.gov.br")
    )
    assert resposta_comum.status_code == 200
    execucao_comum = ExecucaoAcao.objects.get(alvo_identificador="9302820")
    assert execucao_comum.operacao == "criar"
    assert Perfil.objects.get(rf="9302820").is_superuser is False


# ---------------------------------------------------------------------------
# A senha em tela quando o envio está desligado (SPEC criacao_usuarios/007)
# ---------------------------------------------------------------------------


SENHA_EM_TELA = SecretStr("47019352")


def _ligar_envio(settings: SettingsWrapper, monkeypatch: pytest.MonkeyPatch) -> None:
    """Envio ligado sem rede: o `EnviadorSmtp` vira um fake que entrega tudo."""
    settings.EMAIL_ENVIO_HABILITADO = True
    settings.EMAIL_SMTP_USUARIO = "dimap.geocoder@example.com"
    settings.ENFORCE_PREFEITURA_EMAIL = False
    monkeypatch.setattr(
        cadastro,
        "EnviadorSmtp",
        lambda *args: lambda mensagem: ResultadoEnvio(
            entregue_ao_servidor=True, destinatarios_recusados=()
        ),
    )


def _fixar_senha(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cadastro, "gerar_senha_temporaria", lambda *args, **kwargs: SENHA_EM_TELA)


@banco
@pytest.mark.django_db
def test_modal_da_senha_no_html_com_envio_desligado(
    client: Client, settings: SettingsWrapper, monkeypatch: pytest.MonkeyPatch
) -> None:
    _desligar_envio(settings)
    _fixar_senha(monkeypatch)
    unidade = _unidade("CRS-MODAL")
    cargo = _cargo_base()
    dirigente = _dirigente(unidade, "9303000")

    client.force_login(dirigente)
    resposta = client.post(
        _url_gravar(), _payload(unidade, cargo, "9303010", "modal@prefeitura.sp.gov.br")
    )
    html = resposta.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    assert resposta.status_code == 200
    assert "47019352" in html
    assert "Só para desenvolvimento." in html
    # O modal chega aberto e por fora da casca administrativa (SPEC 007, §6).
    toggle = soup.find("input", attrs={"id": "modal-senha"})
    assert isinstance(toggle, Tag)
    assert toggle.has_attr("checked")
    poco = soup.find("div", attrs={"id": "poco-modal"})
    assert isinstance(poco, Tag)
    assert poco["hx-swap-oob"] == "innerHTML"


@banco
@pytest.mark.django_db
def test_senha_ausente_do_html_com_envio_ligado(
    client: Client, settings: SettingsWrapper, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ligar_envio(settings, monkeypatch)
    _fixar_senha(monkeypatch)
    unidade = _unidade("CRS-SEM-MODAL")
    cargo = _cargo_base()
    dirigente = _dirigente(unidade, "9303100")

    client.force_login(dirigente)
    resposta = client.post(
        _url_gravar(), _payload(unidade, cargo, "9303110", "semmodal@prefeitura.sp.gov.br")
    )
    html = resposta.content.decode()

    assert resposta.status_code == 200
    assert "47019352" not in html
    assert "modal-senha" not in html
    assert "foi enviada para" in html


@banco
@pytest.mark.django_db
def test_painel_de_sucesso_nao_promete_email_sem_envio(
    client: Client, settings: SettingsWrapper, monkeypatch: pytest.MonkeyPatch
) -> None:
    _desligar_envio(settings)
    _fixar_senha(monkeypatch)
    unidade = _unidade("CRS-FRASE")
    cargo = _cargo_base()
    dirigente = _dirigente(unidade, "9303200")

    client.force_login(dirigente)
    resposta = client.post(
        _url_gravar(), _payload(unidade, cargo, "9303210", "frase@prefeitura.sp.gov.br")
    )
    html = resposta.content.decode()

    assert "Servidor cadastrado" in html
    assert "foi enviada para" not in html
    assert "entregue a senha de primeiro acesso a mão" in html


@banco
@pytest.mark.django_db
def test_cadastro_recusado_nao_expoe_senha(
    client: Client, settings: SettingsWrapper, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recusa sai pelos `except` do ato, antes de a senha virar desfecho — mesmo sem envio."""
    _desligar_envio(settings)
    _fixar_senha(monkeypatch)
    unidade = _unidade("CRS-RECUSA-SENHA")
    cargo = _cargo_base()
    dirigente = _dirigente(unidade, "9303300")
    _perfil(unidade, "9303310", "Já Existe", email="repetido@prefeitura.sp.gov.br")

    client.force_login(dirigente)
    resposta = client.post(
        _url_gravar(), _payload(unidade, cargo, "9303310", "repetido@prefeitura.sp.gov.br")
    )
    html = resposta.content.decode()

    assert resposta.status_code == 422
    assert "47019352" not in html
    assert "modal-senha" not in html
