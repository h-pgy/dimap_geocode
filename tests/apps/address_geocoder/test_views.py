"""Testes de apps/address_geocoder/views.py (SPEC localizacao_lote/001): resultado de endereço é
ponto, não lote — tira a gaveta lateral de cena via OOB (§2 da SPEC)."""

import pytest
from django.test import Client
from django.urls import reverse

import apps.address_geocoder.views as views
from services.domain.address_geocod import EnderecoAttributes, EnderecoFeature
from services.domain.geometry import PointGeometry

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _feature_endereco() -> EnderecoFeature:
    return EnderecoFeature(
        geometry=PointGeometry(type="Point", coordinates=[-46.6, -23.5]),
        attributes=EnderecoAttributes(
            codlog="123456",
            nome_logradouro="PAULISTA",
            tipo_logradouro="AV",
            numero=100,
            id_segmento="SEG1",
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
# Resultado de endereço tira a gaveta
# ---------------------------------------------------------------------------


def test_resultado_de_endereco_tira_a_gaveta(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_geocoder_fake(monkeypatch)

    resposta = client.post(
        reverse("address_geocoder:selecionar"), {"codlog": "123456", "numero": "100"}
    )
    conteudo = resposta.content.decode()

    assert resposta.status_code == 200
    assert 'id="gaveta-entidade" hx-swap-oob="innerHTML"></div>' in conteudo
    assert "gaveta-lateral" not in conteudo
    assert "paleta-gaveta" not in conteudo
