import json
from typing import Any

import pytest
from bs4 import BeautifulSoup, Tag
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from django.test import RequestFactory
from django.urls import reverse

import apps.address_geocoder.views as address_views
import apps.geocodificacao_externa.views as externo_views
import apps.search.views as views
from apps.geocodificacao_externa.secoes import TITULO_GEOCODIFICACAO_EXTERNA
from apps.search.secoes import SecaoResultado
from apps.unidades.models import CorUnidade, Unidade
from apps.user_admin.models import Perfil
from services.domain.address_geocod import (
    EnderecoAttributes,
    EnderecoFeature,
    NumeracaoNaoEncontradaError,
    SegmentoNaoEncontradoError,
)
from services.domain.geocodificador_externo import (
    ConsultaGeocodificacao,
    EnderecoExternoAttributes,
    EnderecoExternoFeature,
    GeocodificadorExterno,
    PoliticaGeocodificacao,
    Precisao,
    Provedor,
    ProvedorGeocodificacao,
)
from services.domain.geometry import PointGeometry
from services.domain.logradouro import Logradouro
from services.domain.logradouros_match import (
    LogradouroMatchOutput,
    ResolucaoLogradouroItem,
    ResolucaoLogradouroResult,
)
from services.domain.roteamento_busca import TipoEntrada

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

TEXTO = "rua augusta, 100"
ENDERECO_FORMATADO = "R. Augusta, 100 - Consolação, São Paulo - SP, 01304-000, Brasil"


class ProvedorDuble(ProvedorGeocodificacao):
    """Devolve os endereços combinados e conta as chamadas."""

    provedor = Provedor.GOOGLE

    def __init__(self, enderecos: list[EnderecoExternoFeature]) -> None:
        super().__init__(PoliticaGeocodificacao())
        self._enderecos = enderecos
        self.chamadas = 0

    def __call__(self, consulta: ConsultaGeocodificacao) -> list[EnderecoExternoFeature]:
        self.chamadas += 1
        return self._enderecos


def _endereco_externo() -> EnderecoExternoFeature:
    return EnderecoExternoFeature(
        geometry=PointGeometry(type="Point", coordinates=[-46.6545, -23.5535]),
        attributes=EnderecoExternoAttributes(
            endereco_formatado=ENDERECO_FORMATADO,
            municipio="São Paulo",
            uf="SP",
            provedor=Provedor.GOOGLE,
            precisao=Precisao.IMOVEL,
        ),
        crs=4326,
    )


def _endereco_oficial() -> EnderecoFeature:
    return EnderecoFeature(
        geometry=PointGeometry(type="Point", coordinates=[-46.6, -23.5]),
        attributes=EnderecoAttributes(
            logradouro=Logradouro(
                codlog="019348",
                tipo_logradouro="R",
                nome_logradouro="AUGUSTA",
            ),
            numero=100,
            id_segmento="SEG1",
            numeracao_inicial=2,
            numeracao_final=298,
        ),
        crs=4326,
    )


def _resolucao_logradouro(encontrado: bool) -> ResolucaoLogradouroResult:
    itens = [
        ResolucaoLogradouroItem(
            logradouro=LogradouroMatchOutput(
                codlog="01934",
                dv="8",
                tipo_codigo="R",
                nome_logradouro="AUGUSTA",
            ),
        ),
    ]
    return ResolucaoLogradouroResult(itens=itens if encontrado else [], usou_fuzzy=False)


class AddressGeocoderDuble:
    """A interpolação da base oficial: devolve o ponto, ou levanta o erro combinado."""

    erro: Exception | None = None

    def __init__(self, *_args: object) -> None:
        pass

    def __call__(self, _entrada: object) -> EnderecoFeature:
        if self.erro is not None:
            raise self.erro
        return _endereco_oficial()


def _perfil() -> Perfil:
    return Perfil(
        rf="890001",
        nome="Servidor",
        sobrenome="Busca",
        unidade=Unidade(nome="DIMAP-1", cor=CorUnidade.AGUA_700),
    )


def _post(url_name: str, dados: dict[str, str], logado: bool = True) -> HttpRequest:
    request = RequestFactory().post(reverse(url_name), dados)
    request.user = _perfil() if logado else AnonymousUser()
    return request


def _instalar_provedor(
    monkeypatch: pytest.MonkeyPatch,
    enderecos: list[EnderecoExternoFeature],
    configurado: bool = True,
) -> ProvedorDuble:
    provedor = ProvedorDuble(enderecos)
    geocodificador = GeocodificadorExterno(provedor) if configurado else None
    monkeypatch.setattr(
        externo_views,
        "build_geocodificador_externo",
        lambda _settings, _cache: geocodificador,
    )
    return provedor


def _instalar_base_oficial(
    monkeypatch: pytest.MonkeyPatch,
    logradouro_encontrado: bool = True,
    erro: Exception | None = None,
) -> None:
    monkeypatch.setattr(views.orquestrador_endereco_lote, "melhor_sugestao", lambda _candidato: None)
    monkeypatch.setattr(
        views,
        "resolver_logradouro",
        lambda _query: _resolucao_logradouro(logradouro_encontrado),
    )
    monkeypatch.setattr(AddressGeocoderDuble, "erro", erro)
    monkeypatch.setattr(address_views, "AddressGeocoder", AddressGeocoderDuble)


def _instalar_secoes_oficiais(monkeypatch: pytest.MonkeyPatch) -> None:
    for tipo in (TipoEntrada.ENDERECO_LOTE, TipoEntrada.ENDERECO):
        secao = SecaoResultado(titulo=f"seção {tipo}", html="<ul></ul>")
        monkeypatch.setitem(views.REGISTRO_SECOES, tipo, lambda _candidato, s=secao: s)


def _soup(conteudo: bytes) -> BeautifulSoup:
    return BeautifulSoup(conteudo.decode(), "html.parser")


def _titulos_das_secoes(soup: BeautifulSoup) -> list[str]:
    return [h3.get_text(strip=True) for h3 in soup.select("section > h3")]


def _payload(soup: BeautifulSoup) -> dict[str, Any] | None:
    script = soup.find("script", id="mapa-payload")
    if not isinstance(script, Tag):
        return None
    return json.loads(script.get_text())  # type: ignore[no-any-return]


def _texto_do(soup: BeautifulSoup, seletor: str) -> str:
    elemento = soup.select_one(seletor)
    assert elemento is not None
    return elemento.get_text(" ", strip=True)


# ---------------------------------------------------------------------------
# Sugestões: a opção externa, por último, sem gastar cota
# ---------------------------------------------------------------------------


def test_sugestoes_trazem_a_opcao_externa_por_ultimo_sem_chamar_o_provedor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_secoes_oficiais(monkeypatch)
    provedor = _instalar_provedor(monkeypatch, [_endereco_externo()])

    resposta = views.rotear_busca(_post("search:rotear_busca", {"termo_pesquisa": TEXTO}))
    soup = _soup(resposta.content)

    assert _titulos_das_secoes(soup)[-1] == TITULO_GEOCODIFICACAO_EXTERNA
    item = soup.select("section")[-1].select_one("li.suggestion-item")
    assert item is not None
    assert item["hx-post"] == reverse("geocodificacao_externa:selecionar")
    assert json.loads(str(item["hx-vals"])) == {"texto": TEXTO}
    assert provedor.chamadas == 0


@pytest.mark.parametrize(
    ("logado", "configurado"),
    [(False, True), (True, False)],
    ids=["anonimo", "sem-configuracao"],
)
def test_sugestoes_omitem_a_opcao_sem_login_ou_sem_configuracao(
    monkeypatch: pytest.MonkeyPatch,
    logado: bool,
    configurado: bool,
) -> None:
    _instalar_secoes_oficiais(monkeypatch)
    _instalar_provedor(monkeypatch, [_endereco_externo()], configurado=configurado)

    request = _post("search:rotear_busca", {"termo_pesquisa": TEXTO}, logado=logado)
    soup = _soup(views.rotear_busca(request).content)

    assert _titulos_das_secoes(soup)
    assert TITULO_GEOCODIFICACAO_EXTERNA not in _titulos_das_secoes(soup)


# ---------------------------------------------------------------------------
# Enter: a base oficial primeiro, o externo como último recurso
# ---------------------------------------------------------------------------


def test_enter_resolvido_pela_base_oficial_nao_chama_o_provedor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_base_oficial(monkeypatch)
    provedor = _instalar_provedor(monkeypatch, [_endereco_externo()])

    resposta = views.comitar(_post("search:comitar", {"termo_pesquisa": TEXTO}))
    soup = _soup(resposta.content)

    payload = _payload(soup)
    assert payload is not None
    assert payload["geometria"]["features"][0]["geometry"]["coordinates"] == [-46.6, -23.5]
    assert reverse("lotes_mais_proximos:mais_proximo") in resposta.content.decode()
    assert provedor.chamadas == 0


def test_enter_com_numero_fora_da_faixa_cai_no_externo_com_o_aviso(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_base_oficial(monkeypatch, erro=NumeracaoNaoEncontradaError())
    provedor = _instalar_provedor(monkeypatch, [_endereco_externo()])

    resposta = views.comitar(_post("search:comitar", {"termo_pesquisa": TEXTO}))
    soup = _soup(resposta.content)

    assert provedor.chamadas == 1
    assert ENDERECO_FORMATADO in _texto_do(soup, "#gaveta-entidade")
    aviso = _texto_do(soup, '#gaveta-entidade [role="status"]')
    assert address_views.MSG_SEM_NUMERACAO in aviso
    assert "Google" in aviso


def test_enter_com_logradouro_fora_da_base_cai_no_externo_com_o_aviso(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_base_oficial(monkeypatch, logradouro_encontrado=False)
    provedor = _instalar_provedor(monkeypatch, [_endereco_externo()])

    resposta = views.comitar(_post("search:comitar", {"termo_pesquisa": TEXTO}))
    soup = _soup(resposta.content)

    assert provedor.chamadas == 1
    aviso = _texto_do(soup, '#gaveta-entidade [role="status"]')
    assert views.MSG_LOGRADOURO_FORA_DA_BASE in aviso


def test_enter_com_falha_tambem_no_externo_responde_os_dois_motivos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_base_oficial(monkeypatch, erro=SegmentoNaoEncontradoError())
    _instalar_provedor(monkeypatch, [])

    resposta = views.comitar(_post("search:comitar", {"termo_pesquisa": TEXTO}))
    soup = _soup(resposta.content)

    aviso = _texto_do(soup, '[role="alert"]')
    assert f"{address_views.MSG_SEM_SEGMENTO} {externo_views.MSG_SEM_RESULTADO}" in aviso
    assert _payload(soup) is None


@pytest.mark.parametrize(
    ("logado", "configurado"),
    [(False, True), (True, False)],
    ids=["anonimo", "sem-configuracao"],
)
def test_enter_sem_login_ou_sem_configuracao_responde_o_motivo_da_base_oficial(
    monkeypatch: pytest.MonkeyPatch,
    logado: bool,
    configurado: bool,
) -> None:
    _instalar_base_oficial(monkeypatch, erro=NumeracaoNaoEncontradaError())
    provedor = _instalar_provedor(monkeypatch, [_endereco_externo()], configurado=configurado)

    request = _post("search:comitar", {"termo_pesquisa": TEXTO}, logado=logado)
    soup = _soup(views.comitar(request).content)

    assert address_views.MSG_SEM_NUMERACAO in _texto_do(soup, '[role="alert"]')
    assert provedor.chamadas == 0
