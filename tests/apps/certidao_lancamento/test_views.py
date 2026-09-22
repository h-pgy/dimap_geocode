"""Testes de apps/certidao_lancamento/views.py (SPEC certidao_lancamento/001):
modal de emissão, validação de admissibilidade do lote, orquestração de emissão com releitura
no WFS pelo identificador, guarda no acervo, realce de erro no formulário e a bateria completa
de segurança da ação administrativa (skill `acao-administrativa`).
"""

from datetime import timedelta
from itertools import count
from unittest.mock import MagicMock

from django.conf import settings as django_settings
from django.test import Client
from django.urls import reverse
from django.utils import timezone
import pytest

from apps.cargos.models import CargoBase
from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao, ExecucaoAcao
from apps.documentos.models import DocumentoEmitido
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.exercicio import registrar_impedimento
from apps.user_admin.models import Perfil, TipoImpedimento
from apps.user_admin.schemas import NovoImpedimento
from services.domain.geometry import GeoFeature, PolygonGeometry
from services.domain.lote_geocod.models import LoteAttributes, LoteFeature
from services.utils.assinatura import ConferirInput, EstadoSelo, conferir_selo

banco = pytest.mark.banco
SLUG_ACAO = "certidao_lancamento.emitir"
_SIGLAS = count(400)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(nome: str = "Tipo Certidão Lançamento") -> TipoUnidade:
    return TipoUnidade.objects.create(
        nome=nome,
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )


def _unidade(sigla: str = "CLAN-1") -> Unidade:
    return Unidade.objects.create(
        nome=f"Unidade {sigla}",
        sigla=sigla,
        tipo=_tipo_unidade(f"Tipo {sigla}"),
    )


def _cargo_base(nome: str = "Auditor Fiscal") -> CargoBase:
    num = next(_SIGLAS)
    return CargoBase.objects.create(nome=f"{nome} {num}", sigla=f"CL{num}")


def _perfil(unidade: Unidade, rf: str = "890001", nome: str = "Servidor") -> Perfil:
    perfil = Perfil(
        rf=rf,
        nome=nome,
        sobrenome="Lançamento",
        cargo_base=_cargo_base(),
        unidade=unidade,
    )
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _acao(slug: str = SLUG_ACAO) -> Acao:
    return Acao.objects.create(
        slug=slug,
        nome="Emitir certidão de existência de lançamento",
        tooltip="Emite o PDF selado que atesta o lançamento do IPTU do lote.",
        ativa=True,
    )


def _atribuir(unidade: Unidade, acao: Acao) -> AtribuicaoUnidade:
    return AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)


def _conceder(atribuicao: AtribuicaoUnidade, cargo_base: CargoBase) -> Concessao:
    return Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo_base)


def _lote_attributes(**overrides: object) -> LoteAttributes:
    defaults: dict[str, object] = {
        "id_poligono": "1001",
        "setor": "005",
        "quadra": "003",
        "lote": "0048",
        "tipo_lote": "F",
        "digito": "5",
        "codlog": "123450",
        "nome_logradouro": "AV PAULISTA",
        "numero_porta": "100",
        "complemento": None,
        "situacao": "ATIVO",
        "condominio": "00",
    }
    return LoteAttributes(**(defaults | overrides))  # type: ignore[arg-type]


def _lote_feature(attributes: LoteAttributes) -> LoteFeature:
    anel = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]
    geom = PolygonGeometry(type="Polygon", coordinates=[anel])
    return GeoFeature(geometry=geom, attributes=attributes, crs=31983)


def _lote_lido(attributes: LoteAttributes | None = None) -> object:
    attrs = attributes or _lote_attributes()
    feat = _lote_feature(attrs)
    try:
        from apps.certidao_lancamento.emissao import LoteLido  # type: ignore[import-not-found]

        return LoteLido(feature=feat, consultado_em=timezone.localtime())
    except ImportError:
        fake = MagicMock()
        fake.feature = feat
        fake.consultado_em = timezone.localtime()
        return fake


def _url_modal() -> str:
    return reverse("certidao_lancamento:modal")


def _url_emitir() -> str:
    return reverse("certidao_lancamento:emitir")


# ---------------------------------------------------------------------------
# Comportamento das Views (SPEC 001 §8)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_modal_de_lote_sem_lancamento_ou_inexistente_mostra_aviso_sem_formulario(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    unidade = _unidade("CLAN-MODAL")
    servidor = _perfil(unidade, rf="890010")
    acao = _acao(SLUG_ACAO)
    atribuicao = _atribuir(unidade, acao)
    _conceder(atribuicao, servidor.cargo_base)
    client.force_login(servidor)

    # 1. Lote inexistente no GeoSampa (ler_lote devolve None)
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: None)
    resp_inexistente = client.get(_url_modal(), {"id": "9999", "sql": "005.003.0048-5"})
    assert resp_inexistente.status_code == 200
    assert "<form" not in resp_inexistente.content.decode()
    assert "alert-warning" in resp_inexistente.content.decode()

    # 2. Lote municipal / sem lançamento ativo (possui_lancamento == False)
    lote_sem_lancamento = _lote_lido(_lote_attributes(digito=None))
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote_sem_lancamento)
    resp_sem_lanc = client.get(_url_modal(), {"id": "1002", "sql": "005.003.0048-5"})
    assert resp_sem_lanc.status_code == 200
    assert "<form" not in resp_sem_lanc.content.decode()
    assert "alert-warning" in resp_sem_lanc.content.decode()

    # 3. Lote condominial (is_condominio == True)
    lote_condominio = _lote_lido(_lote_attributes(condominio="01"))
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote_condominio)
    resp_cond = client.get(_url_modal(), {"id": "1003", "sql": "005.003.0048-5"})
    assert resp_cond.status_code == 200
    assert "<form" not in resp_cond.content.decode()
    assert "alert-warning" in resp_cond.content.decode()

    # 4. Lote certificável com lançamento: abre modal com formulário
    lote_valido = _lote_lido(_lote_attributes())
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote_valido)
    resp_valido = client.get(_url_modal(), {"id": "1001", "sql": "005.003.0048-5"})
    assert resp_valido.status_code == 200
    corpo_valido = resp_valido.content.decode()
    assert "<form" in corpo_valido
    assert 'data-mascara="0000.0000/0000000-0"' in corpo_valido
    assert 'name="processo"' in corpo_valido
    assert 'name="interessado"' in corpo_valido


@banco
@pytest.mark.django_db
def test_emissao_rele_lote_pelo_identificador(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    unidade = _unidade("CLAN-RELE")
    servidor = _perfil(unidade, rf="890020")
    acao = _acao(SLUG_ACAO)
    atribuicao = _atribuir(unidade, acao)
    _conceder(atribuicao, servidor.cargo_base)
    client.force_login(servidor)

    # Imóvel oficial retornado pelo WFS
    lote_oficial = _lote_lido(
        _lote_attributes(
            id_poligono="1001",
            setor="005",
            quadra="003",
            lote="0048",
            digito="5",
            nome_logradouro="AV PAULISTA OFICIAL",
            numero_porta="100",
        )
    )
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote_oficial)

    # POST com campos adulterados pelo cliente no navegador
    resposta = client.post(
        _url_emitir(),
        {
            "id": "1001",
            "processo": "6017.2026/0012345-6",
            "interessado": "Empresa Interessada",
            "sql": "999.999.9999-9",  # adulterado
            "nome_logradouro": "RUA FALSA",  # adulterado
            "numero_porta": "666",  # adulterado
        },
    )

    assert resposta.status_code == 200
    doc = DocumentoEmitido.objects.latest("emitido_em")
    conferencia = conferir_selo(
        ConferirInput(pdf=bytes(doc.arquivo), segredo=django_settings.ASSINATURA_SEGREDO)
    )
    assert conferencia.estado == EstadoSelo.INTEGRO
    assert conferencia.envelope is not None
    # O SQL certificado vem do lote oficial relido no GeoSampa, e não do POST
    assert conferencia.envelope["alvo"]["identificador"] == "005.003.0048-5"
    assert conferencia.envelope["contribuinte"] == "005.003.0048-5"


@banco
@pytest.mark.django_db
def test_emissao_guarda_via_no_acervo_e_devolve_download(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    unidade = _unidade("CLAN-ACERVO")
    servidor = _perfil(unidade, rf="890030")
    acao = _acao(SLUG_ACAO)
    atribuicao = _atribuir(unidade, acao)
    _conceder(atribuicao, servidor.cargo_base)
    client.force_login(servidor)

    lote_valido = _lote_lido(_lote_attributes(id_poligono="1001"))
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote_valido)

    resposta = client.post(
        _url_emitir(),
        {
            "id": "1001",
            "processo": "6017.2026/0012345-6",
            "interessado": "Marina Salgado",
        },
    )

    assert resposta.status_code == 200
    doc = DocumentoEmitido.objects.latest("emitido_em")
    bytes_emitidos = bytes(doc.arquivo)

    # Segunda via devolve exatamente os mesmos bytes
    url_segunda_via = reverse("documentos:segunda_via", kwargs={"codigo": doc.codigo})
    resp_segunda_via = client.get(url_segunda_via)
    assert resp_segunda_via.status_code == 200
    assert resp_segunda_via.content == bytes_emitidos

    # Resposta contém o botão de download apontando para a certidão
    assert doc.codigo in resposta.content.decode()


@banco
@pytest.mark.django_db
def test_formulario_invalido_volta_ao_modal_com_realce(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    unidade = _unidade("CLAN-INVALIDO")
    servidor = _perfil(unidade, rf="890040")
    acao = _acao(SLUG_ACAO)
    atribuicao = _atribuir(unidade, acao)
    _conceder(atribuicao, servidor.cargo_base)
    client.force_login(servidor)

    lote_valido = _lote_lido(_lote_attributes(id_poligono="1001"))
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote_valido)

    # Processo com formato fora do padrão SEI
    resposta = client.post(
        _url_emitir(),
        {
            "id": "1001",
            "processo": "processo-invalido",
            "interessado": "Empresa Teste",
        },
    )

    assert resposta.status_code == 422
    corpo = resposta.content.decode()
    assert "campo-realce-erro" in corpo
    assert "<form" in corpo


# ---------------------------------------------------------------------------
# Bateria de Segurança da Ação (SPEC 001 §8 e skill `acao-administrativa` §6)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_anonimo_no_modal_vai_ao_login_sem_linha(client: Client) -> None:
    # #1 da skill: anônimo vai ao login, sem registrar linha
    resp_modal = client.get(_url_modal(), {"id": "1001", "sql": "005.003.0048-5"})
    assert resp_modal.status_code == 302
    assert resp_modal["Location"].startswith(str(django_settings.LOGIN_URL))

    resp_emitir = client.post(
        _url_emitir(),
        {"id": "1001", "processo": "6017.2026/0012345-6", "interessado": "Teste"},
    )
    assert resp_emitir.status_code == 302
    assert resp_emitir["Location"].startswith(str(django_settings.LOGIN_URL))

    assert ExecucaoAcao.objects.count() == 0


@banco
@pytest.mark.django_db
def test_sem_concessao_recebe_403_e_linha_de_negativa(client: Client) -> None:
    # #2 da skill: autenticado sem competência recebe 403 e negativa fica registrada
    unidade = _unidade("CLAN-SEM-CONC")
    servidor_sem_concessao = _perfil(unidade, rf="890050")
    client.force_login(servidor_sem_concessao)

    resp_modal = client.get(_url_modal(), {"id": "1001", "sql": "005.003.0048-5"})
    assert resp_modal.status_code == 403

    exec_modal = ExecucaoAcao.objects.filter(autorizado=False).latest("momento")
    assert exec_modal.perfil_id == servidor_sem_concessao.pk

    resp_emitir = client.post(
        _url_emitir(),
        {"id": "1001", "processo": "6017.2026/0012345-6", "interessado": "Teste"},
    )
    assert resp_emitir.status_code == 403

    exec_emitir = ExecucaoAcao.objects.filter(autorizado=False).latest("momento")
    assert exec_emitir.perfil_id == servidor_sem_concessao.pk


@banco
@pytest.mark.django_db
def test_concessao_em_outra_unidade_nao_passa(client: Client) -> None:
    # #3 da skill: quem tem a concessão em outra unidade não passa
    unidade_concessao = _unidade("CLAN-UNID-A")
    unidade_lotacao = _unidade("CLAN-UNID-B")
    servidor = _perfil(unidade_lotacao, rf="890060")

    acao = _acao(SLUG_ACAO)
    atribuicao_a = _atribuir(unidade_concessao, acao)
    _conceder(atribuicao_a, servidor.cargo_base)

    client.force_login(servidor)
    resposta = client.get(_url_modal(), {"id": "1001", "sql": "005.003.0048-5"})
    assert resposta.status_code == 403

    execucao = ExecucaoAcao.objects.filter(autorizado=False).latest("momento")
    assert execucao.perfil_id == servidor.pk


@banco
@pytest.mark.django_db
def test_impedido_recebe_403_e_exonerado_vai_ao_login(client: Client) -> None:
    # #4 da skill: impedido recebe 403; exonerado recebe 302 para login sem linha
    unidade = _unidade("CLAN-IMP-EXO")
    acao = _acao(SLUG_ACAO)
    atribuicao = _atribuir(unidade, acao)

    # 1. Impedido recebe 403
    impedido = _perfil(unidade, rf="890070", nome="Impedido")
    _conceder(atribuicao, impedido.cargo_base)
    tipo_imp, _ = TipoImpedimento.objects.get_or_create(nome="Licença Médica")
    hoje = timezone.localdate()
    registrar_impedimento(
        impedido,
        NovoImpedimento(tipo=tipo_imp.pk, data_inicio=hoje - timedelta(days=1), data_fim=None),
    )

    client.force_login(impedido)
    resp_imp = client.get(_url_modal(), {"id": "1001", "sql": "005.003.0048-5"})
    assert resp_imp.status_code == 403

    # 2. Exonerado (is_active=False) vai ao login
    exonerado = _perfil(unidade, rf="890071", nome="Exonerado")
    _conceder(atribuicao, exonerado.cargo_base)
    exonerado.is_active = False
    exonerado.exonerado_em = timezone.localdate()
    exonerado.save()

    client.force_login(exonerado)
    contagem_antes = ExecucaoAcao.objects.count()
    resp_exo = client.get(_url_modal(), {"id": "1001", "sql": "005.003.0048-5"})
    assert resp_exo.status_code == 302
    assert resp_exo["Location"].startswith(str(django_settings.LOGIN_URL))
    assert ExecucaoAcao.objects.count() == contagem_antes


@banco
@pytest.mark.django_db
def test_emissao_grava_autor_cargo_unidade_operacao_e_alvo(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    # #10 da skill: o ato autorizado grava autor, cargo, unidade, operação e alvo
    unidade_autor = _unidade("CLAN-REG-AUTOR")
    outra_unidade = _unidade("CLAN-REG-OUTRA")
    servidor = _perfil(unidade_autor, rf="890080")
    acao = _acao(SLUG_ACAO)
    atribuicao = _atribuir(unidade_autor, acao)
    _conceder(atribuicao, servidor.cargo_base)

    lote_valido = _lote_lido(_lote_attributes(id_poligono="1001"))
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote_valido)

    client.force_login(servidor)
    resposta = client.post(
        _url_emitir(),
        {
            "id": "1001",
            "processo": "6017.2026/0012345-6",
            "interessado": "Empresa Alvo",
        },
    )
    assert resposta.status_code == 200

    doc = DocumentoEmitido.objects.latest("emitido_em")
    execucao = ExecucaoAcao.objects.get(autorizado=True)
    assert execucao.perfil_id == servidor.pk
    assert execucao.unidade_id == unidade_autor.pk
    assert execucao.cargo_base_id == servidor.cargo_base_id
    assert execucao.operacao == "emitir"
    assert execucao.alvo_tipo == "documento"
    assert execucao.alvo_identificador == doc.codigo

    # Mudar a lotação depois não altera a linha gravada
    servidor.unidade = outra_unidade
    servidor.save(update_fields=["unidade"])
    execucao.refresh_from_db()
    assert execucao.unidade_id == unidade_autor.pk


@banco
@pytest.mark.django_db
def test_abrir_modal_nao_registra_e_negativa_registra(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    # #12 da skill: leitura autorizada não vira linha; leitura negada vira linha
    unidade = _unidade("CLAN-NAO-REG")
    autorizado = _perfil(unidade, rf="890090", nome="Autorizado")
    nao_autorizado = _perfil(unidade, rf="890091", nome="NaoAutorizado")
    acao = _acao(SLUG_ACAO)
    atribuicao = _atribuir(unidade, acao)
    _conceder(atribuicao, autorizado.cargo_base)

    lote_valido = _lote_lido(_lote_attributes(id_poligono="1001"))
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote_valido)

    # 1. Abertura autorizada do modal não vira linha no registro de ações
    client.force_login(autorizado)
    resp_autorizado = client.get(_url_modal(), {"id": "1001", "sql": "005.003.0048-5"})
    assert resp_autorizado.status_code == 200
    assert ExecucaoAcao.objects.count() == 0

    # 2. Abertura negada do modal grava linha de negativa
    client.force_login(nao_autorizado)
    resp_negado = client.get(_url_modal(), {"id": "1001", "sql": "005.003.0048-5"})
    assert resp_negado.status_code == 403
    assert ExecucaoAcao.objects.filter(autorizado=False).count() == 1


@banco
@pytest.mark.django_db
def test_acao_inativa_nao_libera_com_concessao_gravada(client: Client) -> None:
    # #13 da skill: ação inativa não libera ninguém, mesmo com concessão gravada
    unidade = _unidade("CLAN-INATIVA")
    servidor = _perfil(unidade, rf="890100")
    acao = _acao(SLUG_ACAO)
    atribuicao = _atribuir(unidade, acao)
    _conceder(atribuicao, servidor.cargo_base)

    # Desativa a ação no catálogo
    acao.ativa = False
    acao.save(update_fields=["ativa"])

    client.force_login(servidor)
    resposta = client.get(_url_modal(), {"id": "1001", "sql": "005.003.0048-5"})
    assert resposta.status_code == 403


@banco
@pytest.mark.django_db
def test_emitir_so_por_post(client: Client) -> None:
    # #15 da skill: emissão só por POST
    unidade = _unidade("CLAN-SO-POST")
    servidor = _perfil(unidade, rf="890110")
    acao = _acao(SLUG_ACAO)
    atribuicao = _atribuir(unidade, acao)
    _conceder(atribuicao, servidor.cargo_base)

    client.force_login(servidor)
    resposta = client.get(_url_emitir())
    assert resposta.status_code == 405
    assert ExecucaoAcao.objects.count() == 0
