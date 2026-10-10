import pytest

from services.domain.geocodificador_externo import (
    ConsultaGeocodificacao,
    PoliticaGeocodificacao,
    Precisao,
    Provedor,
    ProvedorGoogle,
    ProvedorIndisponivelError,
)
from services.integrations.geocodificador_externo import TransporteError, google


class ClienteGoogleDuble:
    """Guarda a requisição recebida e devolve a resposta combinada — ou levanta o erro combinado."""

    def __init__(
        self,
        resposta: google.GeocodeResponse | None = None,
        erro: Exception | None = None,
    ) -> None:
        self._resposta = resposta or google.GeocodeResponse()
        self._erro = erro
        self.requisicoes: list[google.GeocodeRequest] = []

    def __call__(self, requisicao: google.GeocodeRequest) -> google.GeocodeResponse:
        self.requisicoes.append(requisicao)
        if self._erro is not None:
            raise self._erro
        return self._resposta


def _componente(
    long_text: str,
    tipo: str,
    short_text: str | None = None,
) -> google.AddressComponent:
    return google.AddressComponent(long_text=long_text, short_text=short_text, types=[tipo])


def _resultado_google(
    granularity: google.Granularity = "ROOFTOP",
    componentes: list[google.AddressComponent] | None = None,
) -> google.GeocodeResult:
    return google.GeocodeResult(
        formatted_address="R. Augusta, 100 - Consolação, São Paulo - SP, 01304-000, Brasil",
        location=google.LatLng(latitude=-23.5537, longitude=-46.6522),
        granularity=granularity,
        address_components=componentes or [],
    )


def _provedor_google(cliente: ClienteGoogleDuble) -> ProvedorGoogle:
    return ProvedorGoogle(PoliticaGeocodificacao(), cliente)


def _consulta() -> ConsultaGeocodificacao:
    return ConsultaGeocodificacao(texto="rua augusta, 100")


# ---------------------------------------------------------------------------
# Resposta do Google → endereço externo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("granularity", "precisao"),
    [
        ("ROOFTOP", Precisao.IMOVEL),
        ("RANGE_INTERPOLATED", Precisao.INTERPOLADA),
        ("GEOMETRIC_CENTER", Precisao.LOGRADOURO),
        ("APPROXIMATE", Precisao.APROXIMADA),
        ("GRANULARITY_UNSPECIFIED", Precisao.APROXIMADA),
    ],
)
def test_parser_google_mapeia_granularity_para_precisao(
    granularity: google.Granularity,
    precisao: Precisao,
) -> None:
    resposta = google.GeocodeResponse(results=[_resultado_google(granularity)])
    provedor = _provedor_google(ClienteGoogleDuble(resposta))

    [endereco] = provedor(_consulta())

    assert endereco.attributes.precisao is precisao


def test_parser_google_extrai_componentes_e_declara_o_crs_do_provedor() -> None:
    componentes = [
        _componente("100", "street_number"),
        _componente("Rua Augusta", "route", short_text="R. Augusta"),
        _componente("Consolação", "sublocality_level_1"),
        _componente("São Paulo", "administrative_area_level_2"),
        _componente("São Paulo", "administrative_area_level_1", short_text="SP"),
        _componente("01304-000", "postal_code"),
    ]
    resposta = google.GeocodeResponse(results=[_resultado_google(componentes=componentes)])
    provedor = _provedor_google(ClienteGoogleDuble(resposta))

    [endereco] = provedor(_consulta())

    a = endereco.attributes
    assert a.logradouro == "Rua Augusta"
    assert a.numero == "100"
    assert a.bairro == "Consolação"
    assert a.municipio == "São Paulo"
    assert a.uf == "SP"
    assert a.cep == "01304-000"
    assert a.provedor is Provedor.GOOGLE
    assert endereco.geometry.coordinates == [-46.6522, -23.5537]
    assert endereco.crs == 4326


# ---------------------------------------------------------------------------
# Política → requisição do Google
# ---------------------------------------------------------------------------


def test_provedor_google_traduz_a_politica_na_requisicao() -> None:
    cliente = ClienteGoogleDuble()

    _provedor_google(cliente)(_consulta())

    [requisicao] = cliente.requisicoes
    assert requisicao.address.address_lines == ["rua augusta, 100"]
    assert requisicao.address.locality == "São Paulo"
    assert requisicao.address.administrative_area == "SP"
    assert requisicao.address.region_code == "BR"
    assert requisicao.language_code == "pt-BR"
    assert requisicao.region_code == "br"


# ---------------------------------------------------------------------------
# Falha do provedor
# ---------------------------------------------------------------------------


def test_falha_do_cliente_google_vira_provedor_indisponivel() -> None:
    cliente = ClienteGoogleDuble(erro=TransporteError("403 Client Error"))

    with pytest.raises(ProvedorIndisponivelError):
        _provedor_google(cliente)(_consulta())
