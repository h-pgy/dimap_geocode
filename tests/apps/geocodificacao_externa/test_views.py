import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from bs4 import BeautifulSoup, Tag
from django.conf import settings
from django.contrib.sessions.backends.cache import SessionStore
from django.http import HttpRequest
from django.test import Client, RequestFactory
from django.urls import reverse
from pydantic import ValidationError

import apps.geocodificacao_externa.views as views
from apps.mapping import views as mapping_views
from apps.unidades.models import CorUnidade, Unidade
from apps.user_admin.models import Perfil
from services.domain.geocodificador_externo import (
    ConsultaGeocodificacao,
    EnderecoExternoAttributes,
    EnderecoExternoFeature,
    GeocodificacaoExterna,
    GeocodificadorExterno,
    PoliticaGeocodificacao,
    Precisao,
    Provedor,
    ProvedorGeocodificacao,
    ProvedorIndisponivelError,
)
from services.domain.geometry import PointGeometry

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

ENDERECO_FORMATADO = "Alameda Santos, 1293 - Jardim Paulista, São Paulo - SP, 01419-002, Brasil"
TEXTO = "al santos, 1293"

FUSO = ZoneInfo(settings.TIME_ZONE)
AGORA = datetime(2026, 10, 9, 10, 15, tzinfo=FUSO)
CONSULTA_ANTIGA = datetime(2026, 10, 2, 14, 32, tzinfo=FUSO)


class ProvedorDuble(ProvedorGeocodificacao):
    """Devolve os endereços combinados, ou levanta o erro combinado, e conta as chamadas."""

    provedor = Provedor.GOOGLE

    def __init__(
        self,
        enderecos: list[EnderecoExternoFeature],
        erro: Exception | None = None,
    ) -> None:
        super().__init__(PoliticaGeocodificacao())
        self._enderecos = enderecos
        self._erro = erro
        self.chamadas = 0

    def __call__(self, consulta: ConsultaGeocodificacao) -> list[EnderecoExternoFeature]:
        self.chamadas += 1
        if self._erro is not None:
            raise self._erro
        return self._enderecos


class CacheDuble:
    """Em memória, uma por chave: satisfaz o CacheGeocodificacaoLike."""

    def __init__(self, guardadas: list[GeocodificacaoExterna] | None = None) -> None:
        self.guardadas = {g.consulta.chave: g for g in guardadas or []}

    def buscar(self, consulta: ConsultaGeocodificacao) -> GeocodificacaoExterna | None:
        return self.guardadas.get(consulta.chave)

    def guardar(self, geocodificacao: GeocodificacaoExterna) -> None:
        self.guardadas[geocodificacao.consulta.chave] = geocodificacao


def _endereco_externo(precisao: Precisao = Precisao.IMOVEL) -> EnderecoExternoFeature:
    return EnderecoExternoFeature(
        geometry=PointGeometry(type="Point", coordinates=[-46.6571, -23.5621]),
        attributes=EnderecoExternoAttributes(
            endereco_formatado=ENDERECO_FORMATADO,
            municipio="São Paulo",
            uf="SP",
            provedor=Provedor.GOOGLE,
            precisao=precisao,
        ),
        crs=4326,
    )


def _geocodificacao(consultado_em: datetime) -> GeocodificacaoExterna:
    return GeocodificacaoExterna(
        consulta=ConsultaGeocodificacao(texto=TEXTO),
        endereco=_endereco_externo(),
        consultado_em=consultado_em,
    )


def _unidade() -> Unidade:
    return Unidade(nome="DIMAP-1", cor=CorUnidade.AGUA_700)


def _perfil() -> Perfil:
    # Sem banco: o @login_required só pergunta is_authenticated, verdadeiro para qualquer Perfil; a
    # unidade em memória é o que o widget do usuário, no context processor, lê.
    return Perfil(rf="890001", nome="Servidor", sobrenome="Externo", unidade=_unidade())


def _post_logado(dados: dict[str, str]) -> HttpRequest:
    request = RequestFactory().post(reverse("geocodificacao_externa:selecionar"), dados)
    request.user = _perfil()
    # A gaveta aberta entra no histórico da sessão (SPEC design/021), que a RequestFactory não traz.
    request.session = SessionStore()
    return request


def _soup(conteudo: bytes) -> BeautifulSoup:
    return BeautifulSoup(conteudo.decode(), "html.parser")


def _payload(soup: BeautifulSoup) -> dict[str, Any] | None:
    script = soup.find("script", id="mapa-payload")
    if not isinstance(script, Tag):
        return None
    return json.loads(script.get_text())  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Geocodificou: ponto no mapa e gaveta do endereço externo
# ---------------------------------------------------------------------------


def test_geocodificar_externo_desenha_ponto_e_abre_gaveta() -> None:
    geocodificador = GeocodificadorExterno(ProvedorDuble([_endereco_externo(Precisao.INTERPOLADA)]))

    resposta = views.geocodificar_externo(_post_logado({}), geocodificador, "al santos, 1293")
    soup = _soup(resposta.content)

    payload = _payload(soup)
    assert payload is not None
    assert [f["geometry"]["type"] for f in payload["geometria"]["features"]] == ["Point"]

    gaveta = soup.find(id="gaveta-entidade")
    assert isinstance(gaveta, Tag)
    assert gaveta.has_attr("hx-swap-oob")
    texto = gaveta.get_text()
    assert ENDERECO_FORMATADO in texto
    assert "Google" in texto
    assert "Interpolada na via" in texto

    form = gaveta.find("form")
    assert isinstance(form, Tag)
    assert form["hx-post"] == reverse("lotes_mais_proximos:mais_proximo_do_ponto")
    campos = {i["name"]: i["value"] for i in form.find_all("input", type="hidden")}
    assert campos == {"lon": "-46.6571", "lat": "-23.5621", "origem": ENDERECO_FORMATADO}


def test_gaveta_do_endereco_externo_traz_o_item_do_street_view() -> None:
    geocodificador = GeocodificadorExterno(ProvedorDuble([_endereco_externo()]))

    resposta = views.geocodificar_externo(_post_logado({}), geocodificador, "al santos, 1293")
    gaveta = _soup(resposta.content).find(id="gaveta-entidade")

    assert isinstance(gaveta, Tag)
    item = gaveta.select_one(f'[hx-get="{reverse("street_view:abrir")}"]')
    assert item is not None
    assert item.name == "button"
    assert "Visão da rua" in item.get_text()
    vals = json.loads(str(item["hx-vals"]))
    assert {nome: float(valor) for nome, valor in vals.items()} == {
        "lon": -46.6571,
        "lat": -23.5621,
    }
    assert item["hx-target"] == "#gaveta-inferior-conteudo"
    lista = item.find_parent(class_="poco-acoes__lista")
    assert isinstance(lista, Tag)
    assert lista.has_attr("data-troca-cena")


# ---------------------------------------------------------------------------
# A gaveta declara quem encontrou, quando, e se veio do cache
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("guardadas", "momento", "cacheado", "chamadas"),
    [
        ([_geocodificacao(consultado_em=CONSULTA_ANTIGA)], "02/10/2026 14:32", True, 0),
        ([], "09/10/2026 10:15", False, 1),
    ],
    ids=["cacheado", "recem-consultado"],
)
def test_gaveta_declara_provedor_momento_e_selo_de_cacheado(
    monkeypatch: pytest.MonkeyPatch,
    guardadas: list[GeocodificacaoExterna],
    momento: str,
    cacheado: bool,
    chamadas: int,
) -> None:
    monkeypatch.setattr(views.timezone, "now", lambda: AGORA)
    provedor = ProvedorDuble([_endereco_externo()])
    geocodificador = GeocodificadorExterno(provedor, CacheDuble(guardadas))

    resposta = views.geocodificar_externo(_post_logado({}), geocodificador, TEXTO)
    gaveta = _soup(resposta.content).find(id="gaveta-entidade")

    assert isinstance(gaveta, Tag)
    texto = gaveta.get_text()
    assert "Google" in texto
    assert momento in texto
    assert ("Cacheado" in texto) is cacheado
    assert provedor.chamadas == chamadas


# ---------------------------------------------------------------------------
# Falha do provedor: o aviso diz qual, e nada é desenhado
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("provedor", "mensagem", "tom_esperado"),
    [
        (ProvedorDuble([]), views.MSG_SEM_RESULTADO, "alert-warning"),
        (ProvedorDuble([], erro=ProvedorIndisponivelError("cota")), views.MSG_INDISPONIVEL, "alert-error"),
    ],
    ids=["sem-resultado-aceito", "provedor-indisponivel"],
)
def test_geocodificar_externo_com_falha_responde_aviso_que_diz_qual(
    provedor: ProvedorDuble,
    mensagem: str,
    tom_esperado: str,
) -> None:
    geocodificador = GeocodificadorExterno(provedor)

    resposta = views.geocodificar_externo(_post_logado({}), geocodificador, "al santos, 1293")
    soup = _soup(resposta.content)

    aviso = soup.select_one('[role="alert"]')
    assert aviso is not None
    assert mensagem in aviso.get_text()
    assert tom_esperado in aviso["class"]
    assert _payload(soup) is None


# ---------------------------------------------------------------------------
# Texto acima do teto: nem chega ao provedor
# ---------------------------------------------------------------------------


def test_texto_acima_do_teto_eh_recusado_sem_chamar_o_provedor() -> None:
    provedor = ProvedorDuble([_endereco_externo()])
    geocodificador = GeocodificadorExterno(provedor)

    with pytest.raises(ValidationError):
        views.geocodificar_externo(_post_logado({}), geocodificador, "a" * 501)

    assert provedor.chamadas == 0


# ---------------------------------------------------------------------------
# A rota: login e configuração
# ---------------------------------------------------------------------------


def test_selecionar_anonimo_vai_para_o_login_sem_chamar_o_provedor(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provedor = ProvedorDuble([_endereco_externo()])
    monkeypatch.setattr(
        views,
        "build_geocodificador_externo",
        lambda _settings, _cache: GeocodificadorExterno(provedor),
    )

    resposta = client.post(reverse("geocodificacao_externa:selecionar"), {"texto": "al santos, 1293"})

    assert resposta.status_code == 302
    assert resposta["Location"].startswith(settings.LOGIN_URL)
    assert provedor.chamadas == 0


def test_selecionar_sem_configuracao_responde_indisponivel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(views, "build_geocodificador_externo", lambda _settings, _cache: None)

    resposta = views.selecionar(_post_logado({"texto": "al santos, 1293"}))
    soup = _soup(resposta.content)

    aviso = soup.select_one('[role="alert"]')
    assert aviso is not None
    assert views.MSG_INDISPONIVEL in aviso.get_text()
    assert "alert-error" in aviso["class"]
    assert _payload(soup) is None



# ---------------------------------------------------------------------------
# Histórico da gaveta lateral (SPEC design/021)
# ---------------------------------------------------------------------------

CHAVE_DO_ENDERECO = "externo-alameda-santos-1293-jardim-paulista-sao-paulo-sp-01419-002-brasil"


def test_gaveta_do_endereco_externo_entra_no_historico() -> None:
    geocodificador = GeocodificadorExterno(ProvedorDuble([_endereco_externo()]))
    abrir = _post_logado({})

    resposta = views.geocodificar_externo(abrir, geocodificador, "al santos, 1293")

    raiz = _soup(resposta.content).select_one(".gaveta-lateral")
    assert isinstance(raiz, Tag)
    assert raiz["data-gaveta"] == CHAVE_DO_ENDERECO
    pedir = RequestFactory().get(reverse("mapping:historico_gaveta"), {"chave": "outra-gaveta"})
    pedir.user = abrir.user
    pedir.session = abrir.session
    itens = _soup(mapping_views.historico_gaveta(pedir).content).select(".item-historico")
    assert len(itens) == 1
    assert itens[0].select_one('use[href="#glifo-gaveta-endereco_externo"]') is not None
    assert itens[0].get_text(strip=True) == ENDERECO_FORMATADO
