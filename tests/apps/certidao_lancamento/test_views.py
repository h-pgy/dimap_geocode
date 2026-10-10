"""Testes de apps/certidao_lancamento/views.py (SPECs certidao_lancamento/001 e 002):
modal de emissão e as opções de despacho, validação de admissibilidade do lote, orquestração de
emissão com releitura no WFS pelo identificador, mapa opcional, guarda no acervo, ficha pública,
realce de erro no formulário e a bateria completa de segurança da ação administrativa (skill
`acao-administrativa`) — para um lote e para o conjunto de lotes guardado na sessão.
"""

from collections.abc import Sequence
from datetime import timedelta
from functools import partial
from io import BytesIO
from itertools import count
import json
import re
from typing import Any

from PIL import Image as PILImage
from bs4 import BeautifulSoup
from django.conf import settings as django_settings
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader
import pytest

from apps.cargos.models import CargoBase
from apps.certidao_lancamento.views import grupos_de_despacho
from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao, ExecucaoAcao
from apps.documentos.models import DocumentoEmitido
from apps.lotes_mais_proximos.contexto import camada_lotes
from apps.lotes_mais_proximos.sessao import ConjuntoNaSessao, guardar_conjunto
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.exercicio import registrar_impedimento
from apps.user_admin.models import Perfil, TipoImpedimento
from apps.user_admin.schemas import NovoImpedimento
from services.domain.certidao_lancamento.certidao import corpo_do_despacho
from services.domain.certidao_lancamento.models import SentidoDespacho, TipoDespacho
from services.domain.desenho import Desenho
from services.domain.geometry import GeoFeature, PolygonGeometry, reprojetar
from services.domain.lote_geocod.models import LoteAttributes, LoteFeature
from services.domain.lotes_mais_proximos import (
    BuscarLotesDoDesenho,
    ConjuntoDeLotes,
    LotesDoDesenhoInput,
)
from apps.certidao_lancamento.emissao import LoteLido
from services.integrations.wfs import WfsFeatureCollection, WfsFeatureRequest
from services.integrations.wms import WmsHttpError
from services.integrations.wms.models import WmsImage
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


def _perfil_com_concessao(sigla: str, rf: str) -> Perfil:
    unidade = _unidade(sigla)
    perfil = _perfil(unidade, rf=rf)
    _conceder(_atribuir(unidade, _acao(SLUG_ACAO)), perfil.cargo_base)
    return perfil


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


def _lote_lido(attributes: LoteAttributes | None = None) -> LoteLido:
    attrs = attributes or _lote_attributes()
    return LoteLido(feature=_lote_feature(attrs), consultado_em=timezone.localtime())


def _ortofoto_disponivel(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """O WMS entra pelo fetcher falso; o que ele recebeu volta na lista, para provar quando NÃO é chamado."""
    chamadas: list[object] = []

    def _fetcher(_settings: object) -> object:
        def _buscar(req: object) -> WmsImage:
            chamadas.append(req)
            lado = getattr(req, "width", 200)
            imagem = PILImage.new("RGB", (lado, lado), (120, 140, 120))
            buffer = BytesIO()
            imagem.save(buffer, format="PNG")
            return WmsImage(
                content=buffer.getvalue(),
                content_type="image/png",
                width=lado,
                height=lado,
                layer=req.layer,  # type: ignore[attr-defined]
                bbox=req.bbox,  # type: ignore[attr-defined]
            )

        return _buscar

    monkeypatch.setattr("apps.certidao_lancamento.emissao.build_wms_fetcher", _fetcher)
    return chamadas


def _ortofoto_indisponivel(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    chamadas: list[object] = []

    def _fetcher(_settings: object) -> object:
        def _buscar(req: object) -> WmsImage:
            chamadas.append(req)
            raise WmsHttpError("GeoSampa fora do ar")

        return _buscar

    monkeypatch.setattr("apps.certidao_lancamento.emissao.build_wms_fetcher", _fetcher)
    return chamadas


def _post_pedido(**overrides: str) -> dict[str, str]:
    """O que o navegador envia com o formulário aberto como está: deferido, sem mapa nem ressalva
    (checkbox desmarcado não vai no POST)."""
    defaults = {
        "id": "1001",
        "processo": "6017.2026/0012345-6",
        "interessado": "Marina Salgado",
        "sentido": "deferido",
        "tipo_despacho": "possui_lancamento",
    }
    return defaults | overrides


def _tag_input(corpo: str, nome: str, valor: str | None = None) -> str:
    for tag in re.findall(r"<input\b[^>]*>", corpo):
        if f'name="{nome}"' not in tag:
            continue
        if valor is not None and f'value="{valor}"' not in tag:
            continue
        return tag
    raise AssertionError(f"input name={nome!r} value={valor!r} ausente do HTML")


def _marcado(corpo: str, nome: str, valor: str | None = None) -> bool:
    return re.search(r"\bchecked\b", _tag_input(corpo, nome, valor)) is not None


def _texto_do_pdf(pdf: bytes) -> str:
    paginas = PdfReader(BytesIO(pdf)).pages
    return " ".join(" ".join(pagina.extract_text().split()) for pagina in paginas)


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
    assert "tarja-vinculo-pendente" in resp_inexistente.content.decode()

    # 2. Lote municipal / sem lançamento ativo (possui_lancamento == False)
    lote_sem_lancamento = _lote_lido(_lote_attributes(digito=None))
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote_sem_lancamento)
    resp_sem_lanc = client.get(_url_modal(), {"id": "1002", "sql": "005.003.0048-5"})
    assert resp_sem_lanc.status_code == 200
    assert "<form" not in resp_sem_lanc.content.decode()
    assert "tarja-vinculo-pendente" in resp_sem_lanc.content.decode()

    # 3. Lote condominial (is_condominio == True)
    lote_condominio = _lote_lido(_lote_attributes(condominio="01"))
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote_condominio)
    resp_cond = client.get(_url_modal(), {"id": "1003", "sql": "005.003.0048-5"})
    assert resp_cond.status_code == 200
    assert "<form" not in resp_cond.content.decode()
    assert "tarja-vinculo-pendente" in resp_cond.content.decode()

    # 4. Lote certificável com lançamento: abre modal com formulário
    lote_valido = _lote_lido(_lote_attributes())
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote_valido)
    resp_valido = client.get(_url_modal(), {"id": "1001", "sql": "005.003.0048-5"})
    assert resp_valido.status_code == 200
    corpo_valido = resp_valido.content.decode()
    assert "<form" in corpo_valido
    assert 'data-mascara="0000.0000/0000000-0"' in corpo_valido
    assert 'data-mascara="000.000.000-00|00.000.000/0000-00"' in corpo_valido
    for campo in ("processo", "interessado", "cpf_cnpj", "observacoes"):
        assert f'name="{campo}"' in corpo_valido

    # Abre com deferido, "possui lançamento", a ressalva e o mapa marcados
    assert _marcado(corpo_valido, "sentido", "deferido")
    assert not _marcado(corpo_valido, "sentido", "indeferido")
    assert _marcado(corpo_valido, "tipo_despacho", "possui_lancamento")
    assert not _marcado(corpo_valido, "tipo_despacho", "lancamento_parcial")
    assert _marcado(corpo_valido, "incluir_ressalva")
    assert _marcado(corpo_valido, "incluir_planta")

    # Cada texto à vista como sai no PDF: a abertura do sentido e o corpo já com o SQL do lote
    assert "Solicitação DEFERIDA. Com base nas informações presentes no processo" in corpo_valido
    assert "Solicitação INDEFERIDA. Com base nas informações presentes no processo" in corpo_valido
    assert "pelo contribuinte número 005.003.0048-5" in corpo_valido


@banco
@pytest.mark.django_db
def test_emissao_rele_lote_e_guarda_via_no_acervo(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.force_login(_perfil_com_concessao("CLAN-RELE", rf="890020"))
    _ortofoto_disponivel(monkeypatch)

    # O fetcher fake responde por id: só o 1001 existe, e é o imóvel oficial
    lote_oficial = _lote_lido(
        _lote_attributes(
            id_poligono="1001",
            nome_logradouro="AV PAULISTA OFICIAL",
            numero_porta="100",
        )
    )
    monkeypatch.setattr(
        "apps.certidao_lancamento.views.ler_lote",
        lambda id_poligono: lote_oficial if id_poligono == "1001" else None,
    )

    # POST com campos adulterados pelo cliente no navegador
    resposta = client.post(
        _url_emitir(),
        _post_pedido(
            cpf_cnpj="123.456.789-09",
            sql="999.999.9999-9",  # adulterado
            nome_logradouro="RUA FALSA",  # adulterado
            numero_porta="666",  # adulterado
        ),
    )

    assert resposta.status_code == 200
    doc = DocumentoEmitido.objects.latest("emitido_em")
    bytes_emitidos = bytes(doc.arquivo)
    conferencia = conferir_selo(
        ConferirInput(pdf=bytes_emitidos, segredo=django_settings.ASSINATURA_SEGREDO)
    )
    assert conferencia.estado == EstadoSelo.INTEGRO
    assert conferencia.envelope is not None
    # O SQL e o endereço certificados vêm do lote oficial relido no GeoSampa, e não do POST
    assert conferencia.envelope["alvo"]["identificador"] == "005.003.0048-5"
    assert conferencia.envelope["contribuinte"] == "005.003.0048-5"
    texto = _texto_do_pdf(bytes_emitidos)
    assert "AV PAULISTA OFICIAL" in texto
    assert "RUA FALSA" not in texto

    # O despacho é público; o interessado e o CPF/CNPJ ficam só no PDF
    assert "despacho" in doc.campos_publicos
    assert "interessado" not in doc.campos_publicos
    assert "cpf_cnpj" not in doc.campos_publicos
    assert conferencia.envelope["despacho"] == "Deferido · possui lançamento"
    envelope_guardado = json.dumps(doc.envelope, ensure_ascii=False)
    assert "Marina Salgado" not in envelope_guardado
    assert "123.456.789-09" not in envelope_guardado
    assert "Marina Salgado" in texto
    assert "123.456.789-09" in texto

    # Segunda via devolve exatamente os mesmos bytes, e a resposta oferece o download
    url_segunda_via = reverse("documentos:segunda_via", kwargs={"codigo": doc.codigo})
    resp_segunda_via = client.get(url_segunda_via)
    assert resp_segunda_via.status_code == 200
    assert resp_segunda_via.content == bytes_emitidos
    assert doc.codigo in resposta.content.decode()


@banco
@pytest.mark.django_db
def test_mapa_segue_o_pedido_na_emissao(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.force_login(_perfil_com_concessao("CLAN-MAPA", rf="890025"))
    lote = _lote_lido(_lote_attributes(id_poligono="1001"))
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote)
    chamadas = _ortofoto_disponivel(monkeypatch)

    # Deferimento sem o mapa marcado: emite sem consultar a ortofoto
    resposta = client.post(_url_emitir(), _post_pedido())
    assert resposta.status_code == 200
    assert chamadas == []
    sem_mapa = _texto_do_pdf(bytes(DocumentoEmitido.objects.latest("emitido_em").arquivo))
    assert "Localização do Imóvel" not in sem_mapa

    # Indeferimento com o mapa forçado pelo auditor: a planta é gerada e sai no documento
    resposta = client.post(
        _url_emitir(),
        _post_pedido(
            sentido="indeferido",
            tipo_despacho="imovel_nao_localizado",
            incluir_planta="on",
        ),
    )
    assert resposta.status_code == 200
    assert chamadas != []
    com_mapa = _texto_do_pdf(bytes(DocumentoEmitido.objects.latest("emitido_em").arquivo))
    assert "Localização do Imóvel" in com_mapa

    # Ortofoto indisponível: recusa só o pedido que pediu o mapa
    _ortofoto_indisponivel(monkeypatch)
    emitidos = DocumentoEmitido.objects.count()

    recusado = client.post(_url_emitir(), _post_pedido(incluir_planta="on"))
    assert recusado.status_code == 422
    assert "imagem de localiza" in recusado.content.decode()
    assert DocumentoEmitido.objects.count() == emitidos

    emitido = client.post(_url_emitir(), _post_pedido())
    assert emitido.status_code == 200
    assert DocumentoEmitido.objects.count() == emitidos + 1


@banco
@pytest.mark.django_db
def test_conferencia_mostra_o_despacho_na_ficha(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.force_login(_perfil_com_concessao("CLAN-FICHA", rf="890026"))
    _ortofoto_disponivel(monkeypatch)
    lote = _lote_lido(_lote_attributes(id_poligono="1001"))
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote)

    resposta = client.post(
        _url_emitir(),
        _post_pedido(
            sentido="indeferido",
            tipo_despacho="imovel_nao_localizado",
            cpf_cnpj="123.456.789-09",
        ),
    )
    assert resposta.status_code == 200
    doc = DocumentoEmitido.objects.latest("emitido_em")

    # A conferência é aberta: quem a faz não tem login
    ficha = Client().get(reverse("documentos:conferir", kwargs={"codigo": doc.codigo}))

    assert ficha.status_code == 200
    corpo = ficha.content.decode()
    assert "Indeferido · imóvel não localizado" in corpo
    assert "Marina Salgado" not in corpo
    assert "123.456.789-09" not in corpo


@banco
@pytest.mark.django_db
def test_formulario_invalido_volta_ao_modal_com_realce_e_valores(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.force_login(_perfil_com_concessao("CLAN-INVALIDO", rf="890040"))
    lote = _lote_lido(_lote_attributes(id_poligono="1001"))
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote)

    # Processo e CPF/CNPJ inválidos; o resto, escolhido pelo auditor: indeferido, sem mapa nem ressalva
    resposta = client.post(
        _url_emitir(),
        _post_pedido(
            processo="processo-invalido",
            cpf_cnpj="123.456",
            interessado="Empresa Teste",
            sentido="indeferido",
            tipo_despacho="pedido_de_acesso_a_informacao",
            observacoes="Observação digitada pelo auditor.",
        ),
    )

    assert resposta.status_code == 422
    corpo = resposta.content.decode()
    assert "<form" in corpo
    assert corpo.count("campo-realce-erro") == 2
    assert "formato padr" in corpo
    assert "O CPF deve ter 11 dígitos e o CNPJ, 14" in corpo

    # O que a pessoa digitou e marcou volta como estava
    assert 'value="processo-invalido"' in corpo
    assert 'value="123.456"' in corpo
    assert 'value="Empresa Teste"' in corpo
    assert "Observação digitada pelo auditor." in corpo
    assert _marcado(corpo, "sentido", "indeferido")
    assert not _marcado(corpo, "sentido", "deferido")
    assert _marcado(corpo, "tipo_despacho", "pedido_de_acesso_a_informacao")
    assert not _marcado(corpo, "incluir_planta")
    assert not _marcado(corpo, "incluir_ressalva")
    # Os textos do sentido escolhido seguem à vista
    fieldset_indeferido = re.search(r'<fieldset[^>]*data-mostra-se="indeferido"[^>]*>', corpo)
    assert fieldset_indeferido is not None
    assert "hidden" not in fieldset_indeferido.group(0)


@banco
@pytest.mark.django_db
def test_texto_de_outro_sentido_volta_com_a_tarja_sem_emitir(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.force_login(_perfil_com_concessao("CLAN-OUTRO-SENTIDO", rf="890045"))
    _ortofoto_disponivel(monkeypatch)
    lote = _lote_lido(_lote_attributes(id_poligono="1001"))
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote)
    emitidos = DocumentoEmitido.objects.count()

    # A chave foi trocada para indeferido, mas o texto deferido ficou marcado
    resposta = client.post(
        _url_emitir(),
        _post_pedido(sentido="indeferido", tipo_despacho="possui_lancamento"),
    )

    assert resposta.status_code == 422
    corpo = resposta.content.decode()
    assert "Não foi possível emitir a certidão" in corpo
    assert "Escolha um dos textos de despacho indeferido." in corpo
    assert "campo-realce-erro" not in corpo
    assert DocumentoEmitido.objects.count() == emitidos


# ---------------------------------------------------------------------------
# Opções de despacho do modal (SPEC 001 §8)
# ---------------------------------------------------------------------------


def test_grupos_de_despacho_separam_os_textos_por_sentido() -> None:
    sql = "005.003.0048-5"

    grupos = grupos_de_despacho(TipoDespacho, partial(corpo_do_despacho, sql=sql))

    assert [grupo.sentido for grupo in grupos] == [SentidoDespacho.DEFERIDO, SentidoDespacho.INDEFERIDO]
    deferido, indeferido = grupos
    assert deferido.abertura == "Solicitação DEFERIDA. Com base nas informações presentes no processo, declara-se que"
    assert indeferido.abertura == "Solicitação INDEFERIDA. Com base nas informações presentes no processo, declara-se que"
    # Cada grupo traz só os tipos do seu sentido, com o rótulo do tipo e o corpo já com o SQL
    assert [opcao.valor for opcao in deferido.opcoes] == [
        TipoDespacho.POSSUI_LANCAMENTO,
        TipoDespacho.LANCAMENTO_EM_MAIOR_AREA,
        TipoDespacho.LANCAMENTO_PARCIAL,
    ]
    assert [opcao.valor for opcao in indeferido.opcoes] == [
        TipoDespacho.IMOVEL_NAO_LOCALIZADO,
        TipoDespacho.PEDIDO_DE_ACESSO_A_INFORMACAO,
    ]
    assert deferido.opcoes[0].rotulo == "possui lançamento"
    assert all(sql in opcao.texto for opcao in deferido.opcoes)
    assert not any(sql in opcao.texto for opcao in indeferido.opcoes)

    # O recorte de tipos e o corpo descem como dado: o que não foi oferecido não aparece
    recorte = grupos_de_despacho(
        (TipoDespacho.LANCAMENTO_PARCIAL, TipoDespacho.IMOVEL_NAO_LOCALIZADO),
        lambda tipo: f"corpo de {tipo.value}",
    )
    assert [[opcao.valor for opcao in grupo.opcoes] for grupo in recorte] == [
        [TipoDespacho.LANCAMENTO_PARCIAL],
        [TipoDespacho.IMOVEL_NAO_LOCALIZADO],
    ]
    assert recorte[0].opcoes[0].texto == "corpo de lancamento_parcial"


# ---------------------------------------------------------------------------
# Conformidade (SPEC refatoracao/002 §8)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_modal_mostra_endereco_do_lote(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    unidade = _unidade("CLAN-ENDERECO")
    servidor = _perfil(unidade, rf="890100")
    _conceder(_atribuir(unidade, _acao(SLUG_ACAO)), servidor.cargo_base)
    client.force_login(servidor)

    lote = _lote_lido(
        _lote_attributes(nome_logradouro="AV PAULISTA", numero_porta="100", complemento="APTO 42")
    )
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote)

    corpo = client.get(_url_modal(), {"id": "1001", "sql": "005.003.0048-5"}).content.decode()

    assert "AV PAULISTA" in corpo
    assert "APTO 42" in corpo


@banco
@pytest.mark.django_db
def test_formulario_com_dois_campos_invalidos_realca_os_dois(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    unidade = _unidade("CLAN-DOIS-ERROS")
    servidor = _perfil(unidade, rf="890110")
    _conceder(_atribuir(unidade, _acao(SLUG_ACAO)), servidor.cargo_base)
    client.force_login(servidor)

    lote = _lote_lido(_lote_attributes(id_poligono="1001"))
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote)

    resposta = client.post(
        _url_emitir(),
        _post_pedido(processo="nao-e-processo", interessado=""),
    )

    assert resposta.status_code == 422
    corpo = resposta.content.decode()
    # Os dois controles realcados e as duas mensagens na tarja.
    assert corpo.count("campo-realce-erro") == 2
    assert "formato padr" in corpo
    assert "Informe o nome completo" in corpo


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

    _ortofoto_disponivel(monkeypatch)
    lote_valido = _lote_lido(_lote_attributes(id_poligono="1001"))
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote_valido)

    client.force_login(servidor)
    resposta = client.post(_url_emitir(), _post_pedido(interessado="Empresa Alvo"))
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


# ---------------------------------------------------------------------------
# Conjunto de lotes (SPEC 002): builders
# ---------------------------------------------------------------------------

CRS_MAPA = 4326
CRS_METRICO = 31983
CHAVE = "8f92c0de"
X0_UTM = 333_000.0
Y0_UTM = 7_395_000.0
LADO_LOTE = 20.0


def _retangulo_no_mapa(x0: float, y0: float, largura: float, altura: float) -> PolygonGeometry:
    anel = [
        [x0, y0],
        [x0 + largura, y0],
        [x0 + largura, y0 + altura],
        [x0, y0 + altura],
        [x0, y0],
    ]
    metrico = PolygonGeometry(type="Polygon", coordinates=[anel])
    return reprojetar(metrico, CRS_METRICO, CRS_MAPA)


# Os lotes ficam lado a lado a partir de (X0_UTM, Y0_UTM); o desenho os contém com 50 m de sobra.
X0_DESENHO = X0_UTM - 50.0
LARGURA_DESENHO = 160.0
DESENHO_QUE_CONTEM = _retangulo_no_mapa(X0_DESENHO, Y0_UTM - 50.0, LARGURA_DESENHO, 120.0)


def _feicao_lote(id_poligono: str, indice: int, **props: object) -> dict[str, object]:
    """A feição como o GeoSampa a devolve: o SQL sai 005.003.<0048 + indice>-5, na RUA AUGUSTA."""
    base: dict[str, object] = {
        "cd_identificador": id_poligono,
        "cd_setor_fiscal": "005",
        "cd_quadra_fiscal": "003",
        "cd_lote": f"{48 + indice:04d}",
        "cd_tipo_lote": "F",
        "cd_digito_sql": "5",
        "cd_condominio": "00",
        "tx_situ_lote": "ATIVO",
        "nm_logradouro_completo": "RUA AUGUSTA",
        "cd_numero_porta": str(100 + 2 * indice),
    }
    geometria = _retangulo_no_mapa(X0_UTM + indice * LADO_LOTE, Y0_UTM, LADO_LOTE, LADO_LOTE)
    return {
        "type": "Feature",
        "geometry": geometria.model_dump(),
        "properties": base | props,
    }


def _pagina(feicoes: Sequence[dict[str, object]]) -> WfsFeatureCollection:
    return WfsFeatureCollection.model_validate(
        {"type": "FeatureCollection", "numberMatched": len(feicoes), "features": list(feicoes)}
    )


def _conjunto(
    feicoes: Sequence[dict[str, object]],
    removidos: frozenset[str] = frozenset(),
) -> ConjuntoDeLotes:
    buscar_lotes = BuscarLotesDoDesenho(lambda _req: iter([_pagina(feicoes)]))
    apurado = buscar_lotes(
        LotesDoDesenhoInput(
            desenho=Desenho(id_bancada="7", geometria=DESENHO_QUE_CONTEM),
            crs_mapa=CRS_MAPA,
            camada=camada_lotes(),
            area_maxima_m2=250_000.0,
        )
    )
    return ConjuntoDeLotes(apurado=apurado, removidos=removidos)


def _guardar_na_sessao(client: Client, conjunto: ConjuntoDeLotes, chave: str = CHAVE) -> None:
    sessao = client.session
    guardar_conjunto(sessao, ConjuntoNaSessao(chave=chave, conjunto=conjunto))
    sessao.save()


def _geosampa_responde(
    monkeypatch: pytest.MonkeyPatch,
    feicoes: Sequence[dict[str, object]],
) -> list[WfsFeatureRequest]:
    """A releitura da emissão entra pelo fetcher falso; as consultas voltam na lista."""
    consultas: list[WfsFeatureRequest] = []

    def _fetcher(req: WfsFeatureRequest) -> object:
        consultas.append(req)
        return iter([_pagina(feicoes)])

    monkeypatch.setattr("apps.certidao_lancamento.emissao.build_fetcher", lambda _settings: _fetcher)
    return consultas


def _geosampa_proibido(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fetcher(_req: WfsFeatureRequest) -> object:
        raise AssertionError("esta rota não consulta o GeoServer")

    monkeypatch.setattr("apps.certidao_lancamento.emissao.build_fetcher", lambda _settings: _fetcher)


def _post_conjunto(confirmados: Sequence[str], **overrides: str) -> dict[str, Any]:
    """O que o navegador envia com o modal do conjunto aberto como está, sem mapa nem ressalva."""
    defaults: dict[str, Any] = {
        "chave": CHAVE,
        "confirmados": list(confirmados),
        "processo": "6017.2026/0012345-6",
        "interessado": "Marina Salgado",
        "sentido": "deferido",
        "tipo_despacho": "lancamento_em_maior_area",
    }
    return defaults | overrides


def _envelope_do_pdf(documento: DocumentoEmitido) -> dict[str, Any]:
    conferencia = conferir_selo(
        ConferirInput(pdf=bytes(documento.arquivo), segredo=django_settings.ASSINATURA_SEGREDO)
    )
    assert conferencia.estado == EstadoSelo.INTEGRO
    assert conferencia.envelope is not None
    return conferencia.envelope


def _url_modal_conjunto() -> str:
    return reverse("certidao_lancamento:modal_conjunto")


def _url_emitir_conjunto() -> str:
    return reverse("certidao_lancamento:emitir_conjunto")


# ---------------------------------------------------------------------------
# Comportamento das views do conjunto (SPEC 002 §8)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_modal_do_conjunto_le_a_sessao_sem_consultar_o_wfs(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.force_login(_perfil_com_concessao("CLAN-CJ-MODAL", rf="891010"))
    _geosampa_proibido(monkeypatch)
    feicoes = [_feicao_lote("1001", 0), _feicao_lote("1002", 1), _feicao_lote("1003", 2)]

    # Restaram dois dos três lotes, e o desenho os contém
    _guardar_na_sessao(client, _conjunto(feicoes, removidos=frozenset({"1003"})))
    resposta = client.get(_url_modal_conjunto(), {"id": CHAVE})
    assert resposta.status_code == 200
    corpo = resposta.content.decode()
    soup = BeautifulSoup(corpo, "html.parser")

    # O formulário leva a chave e a lista que o modal mostrou
    formulario = soup.select_one("form")
    assert formulario is not None
    assert formulario["hx-post"] == _url_emitir_conjunto()
    assert [campo["value"] for campo in formulario.select('input[name="chave"]')] == [CHAVE]
    confirmados = [campo["value"] for campo in formulario.select('input[name="confirmados"]')]
    assert confirmados == ["1001", "1002"]
    assert "005.003.0048-5" in corpo
    assert "005.003.0049-5" in corpo
    assert "005.003.0050-5" not in corpo

    # Abre deferido, com o tipo que a geometria sugere já marcado e o texto no plural, com o rol
    assert _marcado(corpo, "sentido", "deferido")
    assert _marcado(corpo, "tipo_despacho", "lancamento_em_maior_area")
    assert not _marcado(corpo, "tipo_despacho", "possui_lancamento")
    assert "pelos contribuintes números 005.003.0048-5 e 005.003.0049-5." in corpo
    assert _marcado(corpo, "incluir_planta")

    # Lote sem lançamento ativo entre os que restaram: aviso que o nomeia, sem formulário
    sem_lancamento = _feicao_lote("1002", 1, tx_situ_lote="CANCELADO")
    _guardar_na_sessao(client, _conjunto([feicoes[0], sem_lancamento]))
    resp_impeditivo = client.get(_url_modal_conjunto(), {"id": CHAVE})
    assert resp_impeditivo.status_code == 200
    corpo_impeditivo = resp_impeditivo.content.decode()
    assert "<form" not in corpo_impeditivo
    assert "tarja-vinculo-pendente" in corpo_impeditivo
    assert "RUA AUGUSTA, 102" in corpo_impeditivo

    # Lote condominial: o mesmo aviso
    condominial = _feicao_lote("1002", 1, cd_condominio="01")
    _guardar_na_sessao(client, _conjunto([feicoes[0], condominial]))
    corpo_condominial = client.get(_url_modal_conjunto(), {"id": CHAVE}).content.decode()
    assert "<form" not in corpo_condominial
    assert "tarja-vinculo-pendente" in corpo_condominial

    # Conjunto vazio: todos os lotes foram tirados da tabela
    _guardar_na_sessao(client, _conjunto(feicoes, removidos=frozenset({"1001", "1002", "1003"})))
    resp_vazio = client.get(_url_modal_conjunto(), {"id": CHAVE})
    assert resp_vazio.status_code == 200
    corpo_vazio = resp_vazio.content.decode()
    assert "<form" not in corpo_vazio
    assert "tarja-vinculo-pendente" in corpo_vazio


@banco
@pytest.mark.django_db
def test_recusa_do_conjunto_preserva_o_tipo_escolhido(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.force_login(_perfil_com_concessao("CLAN-CJ-RECUSA", rf="891020"))
    # O formulário é recusado antes de qualquer consulta ao GeoServer
    _geosampa_proibido(monkeypatch)
    feicoes = [_feicao_lote("1001", 0), _feicao_lote("1002", 1)]
    _guardar_na_sessao(client, _conjunto(feicoes))

    # A geometria sugere "em maior área"; o auditor escolheu "possui lançamento" e errou o processo
    resposta = client.post(
        _url_emitir_conjunto(),
        _post_conjunto(
            ["1001", "1002"],
            processo="processo-invalido",
            tipo_despacho="possui_lancamento",
        ),
    )

    assert resposta.status_code == 422
    corpo = resposta.content.decode()
    assert "<form" in corpo
    assert corpo.count("campo-realce-erro") == 1
    assert 'value="processo-invalido"' in corpo
    assert _marcado(corpo, "tipo_despacho", "possui_lancamento")
    assert not _marcado(corpo, "tipo_despacho", "lancamento_em_maior_area")
    assert DocumentoEmitido.objects.count() == 0


@banco
@pytest.mark.django_db
def test_emissao_certifica_os_lotes_relidos(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.force_login(_perfil_com_concessao("CLAN-CJ-RELE", rf="891030"))
    _ortofoto_disponivel(monkeypatch)
    consultado = [
        _feicao_lote("1001", 0, nm_logradouro_completo="RUA ANTIGA"),
        _feicao_lote("1002", 1),
    ]
    _guardar_na_sessao(client, _conjunto(consultado))

    # Depois da consulta o GeoSampa mudou o endereço do 1001, e o desenho passou a cruzar o 1009
    relido = [
        _feicao_lote("1001", 0, nm_logradouro_completo="RUA NOVA"),
        _feicao_lote("1002", 1),
        _feicao_lote("1009", 2),
    ]
    consultas = _geosampa_responde(monkeypatch, relido)

    resposta = client.post(
        _url_emitir_conjunto(),
        _post_conjunto(["1001", "1002"], cpf_cnpj="123.456.789-09"),
    )

    assert resposta.status_code == 200
    assert len(consultas) == 1
    doc = DocumentoEmitido.objects.latest("emitido_em")
    assert doc.codigo in resposta.content.decode()
    # A certidão atesta a leitura da emissão; o lote que apareceu depois não entra
    texto = _texto_do_pdf(bytes(doc.arquivo))
    assert "RUA NOVA" in texto
    assert "RUA ANTIGA" not in texto
    assert "005.003.0048-5 e 005.003.0049-5" in texto
    assert "005.003.0050-5" not in texto

    # Contribuintes, processo e despacho são públicos; o interessado e o CPF/CNPJ ficam só no PDF
    assert set(doc.campos_publicos) == {"contribuintes", "processo", "despacho"}
    envelope = _envelope_do_pdf(doc)
    assert envelope["alvo"]["tipo"] == "conjunto_lotes"
    assert envelope["alvo"]["identificador"] == "2 lotes"
    assert envelope["contribuintes"] == "005.003.0048-5, 005.003.0049-5"
    assert envelope["processo"] == "6017.2026/0012345-6"
    assert envelope["despacho"] == "Deferido · lançamento em maior área"
    assert "Marina Salgado" not in json.dumps(doc.envelope, ensure_ascii=False)

    # A ficha pública, sem login, mostra os três
    ficha = Client().get(reverse("documentos:conferir", kwargs={"codigo": doc.codigo}))
    assert ficha.status_code == 200
    corpo_ficha = ficha.content.decode()
    assert "005.003.0048-5, 005.003.0049-5" in corpo_ficha
    assert "6017.2026/0012345-6" in corpo_ficha
    assert "Deferido · lançamento em maior área" in corpo_ficha
    assert "Marina Salgado" not in corpo_ficha
    assert "123.456.789-09" not in corpo_ficha

    # O 1002 perdeu o lançamento entre o modal e a emissão: volta o aviso, e nada é emitido
    _geosampa_responde(
        monkeypatch,
        [relido[0], _feicao_lote("1002", 1, tx_situ_lote="CANCELADO")],
    )
    recusada = client.post(_url_emitir_conjunto(), _post_conjunto(["1001", "1002"]))
    assert recusada.status_code == 422
    corpo_recusada = recusada.content.decode()
    assert "<form" not in corpo_recusada
    assert "tarja-vinculo-pendente" in corpo_recusada
    assert "RUA AUGUSTA, 102" in corpo_recusada
    assert DocumentoEmitido.objects.count() == 1


@banco
@pytest.mark.django_db
def test_mapa_do_conjunto_segue_o_pedido(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.force_login(_perfil_com_concessao("CLAN-CJ-MAPA", rf="891040"))
    feicoes = [_feicao_lote("1001", 0), _feicao_lote("1002", 1)]
    _guardar_na_sessao(client, _conjunto(feicoes))
    _geosampa_responde(monkeypatch, feicoes)
    chamadas = _ortofoto_disponivel(monkeypatch)

    # Sem o mapa marcado: emite sem consultar a ortofoto
    resposta = client.post(_url_emitir_conjunto(), _post_conjunto(["1001", "1002"]))
    assert resposta.status_code == 200
    assert chamadas == []
    sem_mapa = _texto_do_pdf(bytes(DocumentoEmitido.objects.latest("emitido_em").arquivo))
    assert "Localização dos Imóveis" not in sem_mapa

    # Indeferimento com o mapa forçado pelo auditor: a planta sai no documento
    resposta = client.post(
        _url_emitir_conjunto(),
        _post_conjunto(
            ["1001", "1002"],
            sentido="indeferido",
            tipo_despacho="imovel_nao_localizado",
            incluir_planta="on",
        ),
    )
    assert resposta.status_code == 200
    assert len(chamadas) == 1
    com_mapa = _texto_do_pdf(bytes(DocumentoEmitido.objects.latest("emitido_em").arquivo))
    assert "Localização dos Imóveis" in com_mapa
    # A planta enquadra o desenho inteiro, que vai além dos lotes
    enquadramento = chamadas[0].bbox  # type: ignore[attr-defined]
    assert enquadramento.minx <= X0_DESENHO + 1.0
    assert enquadramento.maxx >= X0_DESENHO + LARGURA_DESENHO - 1.0

    # Ortofoto indisponível: recusa só o pedido que pediu o mapa
    _ortofoto_indisponivel(monkeypatch)
    emitidos = DocumentoEmitido.objects.count()

    recusado = client.post(
        _url_emitir_conjunto(),
        _post_conjunto(["1001", "1002"], incluir_planta="on"),
    )
    assert recusado.status_code == 422
    assert "imagem de localiza" in recusado.content.decode()
    assert DocumentoEmitido.objects.count() == emitidos

    emitido = client.post(_url_emitir_conjunto(), _post_conjunto(["1001", "1002"]))
    assert emitido.status_code == 200
    assert DocumentoEmitido.objects.count() == emitidos + 1


@banco
@pytest.mark.django_db
def test_conjunto_diferente_do_modal_e_recusado_sem_emitir(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.force_login(_perfil_com_concessao("CLAN-CJ-ALTERADO", rf="891050"))
    _ortofoto_disponivel(monkeypatch)
    feicoes = [_feicao_lote("1001", 0), _feicao_lote("1002", 1), _feicao_lote("1003", 2)]
    confirmados = ["1001", "1002", "1003"]

    # Lote tirado na tabela depois que o modal abriu
    _guardar_na_sessao(client, _conjunto(feicoes, removidos=frozenset({"1003"})))
    _geosampa_responde(monkeypatch, feicoes)
    tirado_depois = client.post(_url_emitir_conjunto(), _post_conjunto(confirmados))

    # Lote que saiu da camada entre a consulta e a emissão
    _guardar_na_sessao(client, _conjunto(feicoes))
    _geosampa_responde(monkeypatch, feicoes[:2])
    fora_da_camada = client.post(_url_emitir_conjunto(), _post_conjunto(confirmados))

    # Id forjado nos confirmados
    _geosampa_responde(monkeypatch, feicoes)
    forjado = client.post(_url_emitir_conjunto(), _post_conjunto([*confirmados, "9999"]))

    # Lote do conjunto omitido dos confirmados
    omitido = client.post(_url_emitir_conjunto(), _post_conjunto(confirmados[:2]))

    # Resultado substituído por outra consulta: a chave do modal já não é a vigente
    _guardar_na_sessao(client, _conjunto(feicoes), chave="chave-da-consulta-nova")
    _geosampa_proibido(monkeypatch)
    substituido = client.post(_url_emitir_conjunto(), _post_conjunto(confirmados))

    for resposta in (tirado_depois, fora_da_camada, forjado, omitido, substituido):
        assert resposta.status_code == 409
        corpo = resposta.content.decode()
        assert "<form" not in corpo
        assert "tarja-vinculo-critica" in corpo
    assert DocumentoEmitido.objects.count() == 0


# ---------------------------------------------------------------------------
# Bateria de Segurança da Ação sobre o conjunto (SPEC 002 §8 e skill `acao-administrativa` §6)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_anonimo_no_modal_do_conjunto_vai_ao_login_sem_linha(client: Client) -> None:
    # #1 da skill: anônimo vai ao login, sem registrar linha
    resp_modal = client.get(_url_modal_conjunto(), {"id": CHAVE})
    assert resp_modal.status_code == 302
    assert resp_modal["Location"].startswith(str(django_settings.LOGIN_URL))

    resp_emitir = client.post(_url_emitir_conjunto(), _post_conjunto(["1001"]))
    assert resp_emitir.status_code == 302
    assert resp_emitir["Location"].startswith(str(django_settings.LOGIN_URL))

    assert ExecucaoAcao.objects.count() == 0
    assert DocumentoEmitido.objects.count() == 0


@banco
@pytest.mark.django_db
def test_sem_concessao_no_conjunto_recebe_403_e_linha_de_negativa(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    # #2 da skill: autenticado sem competência recebe 403 e a negativa fica registrada
    servidor_sem_concessao = _perfil(_unidade("CLAN-CJ-SEM-CONC"), rf="891060")
    client.force_login(servidor_sem_concessao)
    _geosampa_proibido(monkeypatch)
    _guardar_na_sessao(client, _conjunto([_feicao_lote("1001", 0)]))

    resp_modal = client.get(_url_modal_conjunto(), {"id": CHAVE})
    assert resp_modal.status_code == 403
    negativas = ExecucaoAcao.objects.filter(autorizado=False, perfil=servidor_sem_concessao)
    assert negativas.count() == 1

    resp_emitir = client.post(_url_emitir_conjunto(), _post_conjunto(["1001"]))
    assert resp_emitir.status_code == 403
    assert negativas.count() == 2
    assert DocumentoEmitido.objects.count() == 0


@banco
@pytest.mark.django_db
def test_emissao_do_conjunto_grava_autor_cargo_unidade_operacao_e_alvo(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    # #10 da skill: o ato autorizado grava autor, cargo, unidade, operação e alvo
    unidade_autor = _unidade("CLAN-CJ-REG-AUTOR")
    outra_unidade = _unidade("CLAN-CJ-REG-OUTRA")
    servidor = _perfil(unidade_autor, rf="891070")
    _conceder(_atribuir(unidade_autor, _acao(SLUG_ACAO)), servidor.cargo_base)
    client.force_login(servidor)
    feicoes = [_feicao_lote("1001", 0), _feicao_lote("1002", 1)]
    _guardar_na_sessao(client, _conjunto(feicoes))
    _geosampa_responde(monkeypatch, feicoes)
    _ortofoto_disponivel(monkeypatch)

    resposta = client.post(_url_emitir_conjunto(), _post_conjunto(["1001", "1002"]))
    assert resposta.status_code == 200

    doc = DocumentoEmitido.objects.latest("emitido_em")
    execucao = ExecucaoAcao.objects.get(autorizado=True)
    assert execucao.perfil_id == servidor.pk
    assert execucao.unidade_id == unidade_autor.pk
    assert execucao.cargo_base_id == servidor.cargo_base_id
    assert execucao.operacao == "emitir_conjunto"
    assert execucao.alvo_tipo == "documento"
    assert execucao.alvo_identificador == doc.codigo

    # Mudar a lotação depois não altera a linha gravada
    servidor.unidade = outra_unidade
    servidor.save(update_fields=["unidade"])
    execucao.refresh_from_db()
    assert execucao.unidade_id == unidade_autor.pk


@banco
@pytest.mark.django_db
def test_emitir_e_emitir_conjunto_distinguiveis_no_registro(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    # #11 da skill: a certidão de um lote e a do conjunto são a mesma ação, com operações distintas
    client.force_login(_perfil_com_concessao("CLAN-CJ-OPERACOES", rf="891080"))
    _ortofoto_disponivel(monkeypatch)
    lote = _lote_lido(_lote_attributes(id_poligono="1001"))
    monkeypatch.setattr("apps.certidao_lancamento.views.ler_lote", lambda _id: lote)
    feicoes = [_feicao_lote("1001", 0), _feicao_lote("1002", 1)]
    _guardar_na_sessao(client, _conjunto(feicoes))
    _geosampa_responde(monkeypatch, feicoes)

    de_um_lote = client.post(_url_emitir(), _post_pedido())
    do_conjunto = client.post(_url_emitir_conjunto(), _post_conjunto(["1001", "1002"]))
    assert de_um_lote.status_code == 200
    assert do_conjunto.status_code == 200

    execucoes = ExecucaoAcao.objects.filter(autorizado=True).order_by("momento")
    assert [execucao.operacao for execucao in execucoes] == ["emitir", "emitir_conjunto"]
    documentos = DocumentoEmitido.objects.order_by("emitido_em")
    assert [_envelope_do_pdf(doc)["operacao"] for doc in documentos] == ["emitir", "emitir_conjunto"]


@banco
@pytest.mark.django_db
def test_abrir_modal_do_conjunto_nao_registra(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    # #12 da skill: abrir o modal é leitura autorizada, e não vira linha
    client.force_login(_perfil_com_concessao("CLAN-CJ-NAO-REG", rf="891090"))
    _geosampa_proibido(monkeypatch)
    _guardar_na_sessao(client, _conjunto([_feicao_lote("1001", 0)]))

    resposta = client.get(_url_modal_conjunto(), {"id": CHAVE})

    assert resposta.status_code == 200
    assert ExecucaoAcao.objects.count() == 0


@banco
@pytest.mark.django_db
def test_emitir_conjunto_so_por_post(client: Client) -> None:
    # #15 da skill: emissão só por POST
    client.force_login(_perfil_com_concessao("CLAN-CJ-SO-POST", rf="891100"))

    resposta = client.get(_url_emitir_conjunto())

    assert resposta.status_code == 405
    assert ExecucaoAcao.objects.count() == 0
    assert DocumentoEmitido.objects.count() == 0
