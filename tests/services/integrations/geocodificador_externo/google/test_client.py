import json
from collections.abc import Iterator
from typing import Any
from unittest.mock import Mock

import pytest
import requests
from pydantic import SecretStr

from services.integrations.geocodificador_externo import (
    ClienteGeocodificacaoError,
    RespostaInvalidaError,
    TransporteError,
    google,
)
from services.utils.http import HttpFetcher, HttpRetryPolicy

TOKEN = "AIzaSy-token-de-teste-que-nunca-pode-vazar"
URL_V4 = "https://geocode.googleapis.com/v4/geocode/address"

RESPOSTA_V4: dict[str, Any] = {
    "results": [
        {
            "place": "//places.googleapis.com/places/ChIJ-teste",
            "placeId": "ChIJ-teste",
            "location": {"latitude": -23.5537, "longitude": -46.6522},
            "granularity": "ROOFTOP",
            "viewport": {
                "low": {"latitude": -23.555, "longitude": -46.654},
                "high": {"latitude": -23.552, "longitude": -46.651},
            },
            "formattedAddress": "R. Augusta, 100 - Consolação, São Paulo - SP, 01304-000, Brasil",
            "postalAddress": {
                "regionCode": "BR",
                "languageCode": "pt-BR",
                "postalCode": "01304-000",
                "administrativeArea": "SP",
                "locality": "São Paulo",
                "addressLines": ["R. Augusta, 100"],
            },
            "addressComponents": [
                {"longText": "100", "types": ["street_number"], "languageCode": "pt"},
                {
                    "longText": "Rua Augusta",
                    "shortText": "R. Augusta",
                    "types": ["route"],
                    "languageCode": "pt",
                },
            ],
            "types": ["street_address"],
        }
    ]
}


def _politica() -> HttpRetryPolicy:
    # Espera zero: o que se testa é o desfecho da falha, não quanto tempo dorme.
    return HttpRetryPolicy(
        max_retries=1,
        retry_wait_min_seconds=0.0,
        retry_wait_max_seconds=0.0,
        status_para_retry=(500, 502, 503, 504),
    )


def _url_completa(url: str, **kwargs: Any) -> str:
    # O requests põe a URL com a query string nas mensagens de erro: se a chave estivesse nos
    # params, é por aqui que ela vazaria.
    preparada = requests.Request("GET", url, params=kwargs.get("params")).prepare()
    return str(preparada.url)


def _resposta(status: int = 200, conteudo: bytes = b"{}") -> Mock:
    resposta = Mock()
    resposta.status_code = status
    resposta.content = conteudo
    resposta.raise_for_status.return_value = None
    return resposta


def _resposta_json(corpo: dict[str, Any]) -> Mock:
    return _resposta(conteudo=json.dumps(corpo).encode())


def _session(get: Any) -> Mock:
    session = Mock()
    session.headers = {}
    session.get.side_effect = get
    return session


def _session_com_resposta(resposta: Mock) -> Mock:
    return _session([resposta])


def _session_sem_rede() -> Mock:
    def get(url: str, **kwargs: Any) -> Mock:
        raise requests.exceptions.ConnectionError(
            f"Max retries exceeded with url: {_url_completa(url, **kwargs)}"
        )

    return _session(get)


def _session_com_status(status: int) -> Mock:
    def get(url: str, **kwargs: Any) -> Mock:
        resposta = _resposta(status)
        resposta.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status} Client Error: Forbidden for url: {_url_completa(url, **kwargs)}"
        )
        return resposta

    return _session(get)


def _session_em_loop_de_redirect() -> Mock:
    def get(url: str, **kwargs: Any) -> Mock:
        raise requests.exceptions.TooManyRedirects(
            f"Exceeded 30 redirects: {_url_completa(url, **kwargs)}"
        )

    return _session(get)


def _cliente(session: Mock) -> google.Cliente:
    return google.Cliente(
        token=SecretStr(TOKEN),
        fetcher=HttpFetcher(_politica(), session=session),
    )


def _requisicao() -> google.GeocodeRequest:
    return google.GeocodeRequest(
        address=google.PostalAddress(
            address_lines=["rua augusta, 100"],
            locality="São Paulo",
            administrative_area="SP",
            region_code="BR",
        ),
        language_code="pt-BR",
        region_code="br",
    )


def _cadeia(exc: BaseException) -> Iterator[BaseException]:
    vistas: set[int] = set()
    pendentes: list[BaseException | None] = [exc]
    while pendentes:
        atual = pendentes.pop()
        if atual is None or id(atual) in vistas:
            continue
        vistas.add(id(atual))
        yield atual
        pendentes.append(atual.__cause__)
        pendentes.append(atual.__context__)


# ---------------------------------------------------------------------------
# Requisição
# ---------------------------------------------------------------------------


def test_cliente_envia_endereco_estruturado_e_o_token_so_no_header() -> None:
    session = _session_com_resposta(_resposta_json(RESPOSTA_V4))

    _cliente(session)(_requisicao())

    args, kwargs = session.get.call_args
    assert args[0] == URL_V4
    assert kwargs["params"] == {
        "address.addressLines": ["rua augusta, 100"],
        "address.locality": "São Paulo",
        "address.administrativeArea": "SP",
        "address.regionCode": "BR",
        "languageCode": "pt-BR",
        "regionCode": "br",
    }
    assert kwargs["headers"]["X-Goog-Api-Key"] == TOKEN
    assert TOKEN not in _url_completa(*args, **kwargs)
    assert TOKEN not in str(kwargs["params"])


# ---------------------------------------------------------------------------
# Resposta
# ---------------------------------------------------------------------------


def test_resposta_vira_espelho_tipado() -> None:
    resposta = _cliente(_session_com_resposta(_resposta_json(RESPOSTA_V4)))(_requisicao())

    resultado = resposta.results[0]
    assert resultado.location.latitude == pytest.approx(-23.5537)
    assert resultado.location.longitude == pytest.approx(-46.6522)
    assert resultado.granularity == "ROOFTOP"
    assert resultado.formatted_address.startswith("R. Augusta, 100")
    numero, rua = resultado.address_components
    assert numero.long_text == "100"
    assert numero.short_text is None
    assert rua.long_text == "Rua Augusta"
    assert rua.short_text == "R. Augusta"
    assert rua.types == ["route"]


@pytest.mark.parametrize("corpo", [{}, {"results": []}], ids=["omitida", "vazia"])
def test_resposta_sem_resultados_devolve_lista_vazia(corpo: dict[str, Any]) -> None:
    resposta = _cliente(_session_com_resposta(_resposta_json(corpo)))(_requisicao())

    assert resposta.results == []


# ---------------------------------------------------------------------------
# Falhas
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("session", "trecho"),
    [(_session_sem_rede, "ConnectionError"), (lambda: _session_com_status(403), "403")],
    ids=["rede", "http_403"],
)
def test_falha_de_transporte_levanta_erro_da_integracao(
    session: Any,
    trecho: str,
) -> None:
    with pytest.raises(TransporteError) as excinfo:
        _cliente(session())(_requisicao())

    assert trecho in str(excinfo.value)


@pytest.mark.parametrize(
    "conteudo",
    [
        b"<html><body>Service Unavailable</body></html>",
        json.dumps(
            {"results": [RESPOSTA_V4["results"][0] | {"granularity": "SUPER_ROOFTOP"}]}
        ).encode(),
    ],
    ids=["html", "granularity_desconhecida"],
)
def test_corpo_fora_do_contrato_levanta_resposta_invalida(conteudo: bytes) -> None:
    with pytest.raises(RespostaInvalidaError):
        _cliente(_session_com_resposta(_resposta(conteudo=conteudo)))(_requisicao())


@pytest.mark.parametrize(
    "session",
    [
        _session_sem_rede,
        lambda: _session_com_status(403),
        _session_em_loop_de_redirect,
        lambda: _session_com_resposta(_resposta(conteudo=b"<html></html>")),
    ],
    ids=["rede", "http_definitivo", "redirect_em_excesso", "corpo_invalido"],
)
def test_nenhuma_excecao_da_integracao_vaza_o_token(session: Any) -> None:
    with pytest.raises(ClienteGeocodificacaoError) as excinfo:
        _cliente(session())(_requisicao())

    for exc in _cadeia(excinfo.value):
        assert TOKEN not in str(exc), type(exc).__name__
        assert TOKEN not in repr(exc), type(exc).__name__


# ---------------------------------------------------------------------------
# Integração com a API real
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_geocoding_real_do_google() -> None:
    from django.conf import settings

    cliente = google.build_cliente(settings)
    assert cliente is not None, "o gate exige GOOGLE_GEOCODING_TOKEN no ambiente"

    conhecido = cliente(_requisicao())
    assert len(conhecido.results) >= 1

    inexistente = cliente(
        google.GeocodeRequest(
            address=google.PostalAddress(address_lines=["qxzwvkj ypfhgt 987654321"]),
        )
    )
    assert inexistente.results == []
