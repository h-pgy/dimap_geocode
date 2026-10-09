"""Testes de apps/address_geocoder/views.py: resultado de endereço interpolado abre a gaveta do
endereço (SPEC localizacao_lote/002) — supersede o comportamento da SPEC localizacao_lote/001, que
tirava a gaveta de cena (§2 da SPEC 002: "abre a gaveta lateral do endereço")."""

import json

import pandas as pd
import pytest
from bs4 import BeautifulSoup, Tag
from django.test import Client, RequestFactory
from django.urls import reverse

import apps.address_geocoder.views as views
import apps.geocodificacao_externa.views as externo_views
from apps.search.secoes import SecaoResultado
from apps.unidades.models import CorUnidade, Unidade
from apps.user_admin.models import Perfil
from services.domain.address_geocod import (
    EnderecoAttributes,
    EnderecoFeature,
    NumeracaoNaoEncontradaError,
)
from services.domain.geocodificador_externo import (
    ConsultaGeocodificacao,
    EnderecoExternoFeature,
    GeocodificadorExterno,
    PoliticaGeocodificacao,
    Provedor,
    ProvedorGeocodificacao,
)
from services.domain.codlog_match import CodlogMatcher
from services.domain.codlog_match.catalog import CodlogCatalog
from services.domain.geometry import PointGeometry
from services.domain.logradouro import Logradouro
from services.domain.logradouros_match.catalog import (
    NOMES_LOGRADOUROS_FILE,
    TIPOS_CACHE_FILE,
    TITULOS_CACHE_FILE,
    LogradouroCatalog,
)
from services.domain.logradouros_match.literal_matcher import LiteralLogradouroMatcher
from services.domain.logradouros_match.matcher import LogradouroMatcher
from services.domain.logradouros_match.resolver import LogradouroResolver
from services.domain.roteamento_busca import (
    CodlogParse,
    EnderecoCodlogParse,
    EnderecoParse,
    LogradouroParse,
)
from services.utils.io import write_parquet_to_data

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _logradouro(
    titulo: str | None = None,
    preposicao: str | None = None,
) -> Logradouro:
    return Logradouro(
        codlog="123456",
        tipo_logradouro="AV",
        titulo=titulo,
        preposicao=preposicao,
        nome_logradouro="PAULISTA",
    )


def _feature_endereco(logradouro: Logradouro | None = None) -> EnderecoFeature:
    return EnderecoFeature(
        geometry=PointGeometry(type="Point", coordinates=[-46.6, -23.5]),
        attributes=EnderecoAttributes(
            logradouro=logradouro or _logradouro(),
            numero=100,
            id_segmento="SEG1",
            numeracao_inicial=52,
            numeracao_final=298,
        ),
        crs=4326,
    )


class _FakeAddressGeocoder:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    def __call__(self, _entrada: object) -> EnderecoFeature:
        return _feature_endereco()


def _instalar_geocoder_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(views, "AddressGeocoder", _FakeAddressGeocoder)


# ---------------------------------------------------------------------------
# Resultado de endereço abre a gaveta, com faixa de numeração e botão de busca
# ---------------------------------------------------------------------------


def test_endereco_interpolado_abre_gaveta_com_faixa_e_botao(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_geocoder_fake(monkeypatch)

    resposta = client.post(
        reverse("address_geocoder:selecionar"), {"codlog": "123456", "numero": "100"}
    )
    conteudo = resposta.content.decode()

    assert resposta.status_code == 200
    assert 'id="gaveta-entidade" hx-swap-oob="innerHTML">' in conteudo
    assert "gaveta-lateral" in conteudo
    assert "paleta-gaveta" in conteudo
    assert "123456" in conteudo
    assert "52" in conteudo and "298" in conteudo  # faixa de numeração do segmento
    assert reverse("lotes_mais_proximos:mais_proximo") in conteudo
    assert "badge-info" not in conteudo  # sem score (endereço por codlog): sem grau de certeza


def test_gaveta_do_endereco_mostra_o_nome_completo_do_logradouro(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    endereco = _feature_endereco(_logradouro(titulo="DR", preposicao="DE"))

    class _GeocoderComTituloEPreposicao(_FakeAddressGeocoder):
        def __call__(self, _entrada: object) -> EnderecoFeature:
            return endereco

    monkeypatch.setattr(views, "AddressGeocoder", _GeocoderComTituloEPreposicao)

    resposta = client.post(
        reverse("address_geocoder:selecionar"), {"codlog": "123456", "numero": "100"}
    )
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")

    cabecalho = soup.select_one("#gaveta-entidade .gaveta-lateral-cabecalho")
    assert cabecalho is not None
    assert "AV DR DE PAULISTA, 100" in cabecalho.get_text()
    script = soup.find("script", id="mapa-payload")
    assert isinstance(script, Tag)
    feature = json.loads(script.get_text())["geometria"]["features"][0]
    assert "AV DR DE PAULISTA, 100" in feature["properties"]["popup_html"]
    assert feature["properties"]["rotulo"] == "AV DR DE PAULISTA, 100"


def test_endereco_por_nome_aproximado_mostra_grau_de_certeza(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_geocoder_fake(monkeypatch)

    resposta = client.post(
        reverse("address_geocoder:selecionar"),
        {"codlog": "123456", "numero": "100", "score": "87.3"},
    )
    conteudo = resposta.content.decode()

    assert "badge-info" in conteudo
    assert "87%" in conteudo


# ---------------------------------------------------------------------------
# Clique numa sugestão oficial que falha: aviso, sem cair no externo
# ---------------------------------------------------------------------------


class _ProvedorDuble(ProvedorGeocodificacao):
    provedor = Provedor.GOOGLE

    def __init__(self) -> None:
        super().__init__(PoliticaGeocodificacao())
        self.chamadas = 0

    def __call__(self, consulta: ConsultaGeocodificacao) -> list[EnderecoExternoFeature]:
        self.chamadas += 1
        return []


class _AddressGeocoderForaDaFaixa:
    def __init__(self, *_args: object) -> None:
        pass

    def __call__(self, _entrada: object) -> EnderecoFeature:
        raise NumeracaoNaoEncontradaError()


def _perfil() -> Perfil:
    return Perfil(
        rf="890001",
        nome="Servidor",
        sobrenome="Clique",
        unidade=Unidade(nome="DIMAP-1", cor=CorUnidade.AGUA_700),
    )


def test_clique_em_sugestao_oficial_que_falha_mantem_o_aviso(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(views, "AddressGeocoder", _AddressGeocoderForaDaFaixa)
    provedor = _ProvedorDuble()
    monkeypatch.setattr(
        externo_views,
        "build_geocodificador_externo",
        lambda _settings, _cache: GeocodificadorExterno(provedor),
    )
    request = RequestFactory().post(
        reverse("address_geocoder:selecionar"), {"codlog": "019348", "numero": "9999"}
    )
    request.user = _perfil()

    conteudo = views.selecionar(request).content.decode()

    assert views.MSG_SEM_NUMERACAO in conteudo
    assert provedor.chamadas == 0


# ---------------------------------------------------------------------------
# Street View na gaveta do endereço: só para quem está logado
# ---------------------------------------------------------------------------


def _controle_street_view(conteudo: str) -> Tag | None:
    gaveta = BeautifulSoup(conteudo, "html.parser").find(id="gaveta-entidade")
    assert isinstance(gaveta, Tag)
    return gaveta.select_one("a[data-janela-popup]")


def test_gaveta_do_endereco_logado_traz_o_controle_do_street_view(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_geocoder_fake(monkeypatch)
    request = RequestFactory().post(
        reverse("address_geocoder:selecionar"), {"codlog": "123456", "numero": "100"}
    )
    request.user = _perfil()

    conteudo = views.selecionar(request).content.decode()

    controle = _controle_street_view(conteudo)
    assert controle is not None
    assert controle["href"] == reverse("street_view:abrir") + "?lon=-46.6&lat=-23.5"
    assert controle["target"] == "_blank"
    url_aviso = reverse("street_view:popup_bloqueado") + "?toggle=gaveta-endereco-toggle"
    assert controle["data-aviso-bloqueio"] == url_aviso


def test_gaveta_do_endereco_anonimo_nao_traz_o_controle(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_geocoder_fake(monkeypatch)

    resposta = client.post(
        reverse("address_geocoder:selecionar"), {"codlog": "123456", "numero": "100"}
    )

    assert _controle_street_view(resposta.content.decode()) is None


# ---------------------------------------------------------------------------
# Sugestões de endereço: o nome completo do logradouro, o mesmo da gaveta
# ---------------------------------------------------------------------------

LUIS_ANTONIO = "AV BRIG LUIS ANTONIO"

_NOMES: dict[str, list[object]] = {
    "codlog": ["121657"],
    "cd_tipo_logradouro": ["AV"],
    "cd_titulo_logradouro": ["BRIG"],
    "tx_preposicao_logradouro": [None],
    "nm_logradouro": ["LUIS ANTONIO"],
}


class FakeCodlogCatalog(CodlogCatalog):
    """Subclasse escapa do singleton (o bypass do __new__ é só para a classe base)."""

    def __init__(self, dados: dict[str, list[object]]) -> None:
        self._dados = dados

    @property
    def logradouros(self) -> pd.DataFrame:
        df = pd.DataFrame(self._dados)
        df["_codlog5"] = df["codlog"].str[:5]
        return df


def _instalar_catalogos(monkeypatch: pytest.MonkeyPatch) -> None:
    # Parquets no diretório temporário (fixture _isolar_diretorio_de_dados do conftest), lidos
    # pelo catálogo de verdade — nasce frio pelo reset do singleton no conftest.
    write_parquet_to_data(_NOMES, NOMES_LOGRADOUROS_FILE)
    write_parquet_to_data({"nome_tipo": ["AV"], "cd_tipo_logradouro": ["AV"]}, TIPOS_CACHE_FILE)
    write_parquet_to_data(
        {"cd_titulo_logradouro": ["BRIG"], "nome_titulo": ["BRIGADEIRO"]},
        TITULOS_CACHE_FILE,
    )
    catalogo = LogradouroCatalog()
    resolver = LogradouroResolver(
        literal=LiteralLogradouroMatcher(catalog=catalogo),
        fuzzy=LogradouroMatcher(catalog=catalogo),
        catalog=catalogo,
    )
    monkeypatch.setattr(views, "match_codlog", CodlogMatcher(catalog=FakeCodlogCatalog(_NOMES)))
    monkeypatch.setattr(views, "resolver_logradouro", resolver)


def _nome_na_sugestao(secao: SecaoResultado | None) -> str:
    assert secao is not None
    nome = BeautifulSoup(secao.html, "html.parser").select_one("li.suggestion-item .font-medium")
    assert nome is not None
    return nome.get_text(strip=True)


def test_sugestoes_mostram_o_nome_completo_do_logradouro(monkeypatch: pytest.MonkeyPatch) -> None:
    _instalar_catalogos(monkeypatch)

    por_codlog = views.secao_endereco_codlog(
        EnderecoCodlogParse(
            codlog=CodlogParse(codlog="12165", digito_verificador="7"),
            numero=100,
            numero_bruto="100",
        )
    )
    por_nome = views.secao_endereco(
        EnderecoParse(
            logradouro=LogradouroParse(tipo_logradouro="av", nome="luis antonio"),
            numero=100,
            numero_bruto="100",
        )
    )

    assert _nome_na_sugestao(por_codlog) == f"{LUIS_ANTONIO}, 100"
    assert _nome_na_sugestao(por_nome) == f"{LUIS_ANTONIO}, 100"
