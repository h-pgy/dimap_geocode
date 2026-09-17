"""Testes de apps/address_geocoder/views.py: resultado de endereço interpolado abre a gaveta do
endereço (SPEC localizacao_lote/002) — supersede o comportamento da SPEC localizacao_lote/001, que
tirava a gaveta de cena (§2 da SPEC 002: "abre a gaveta lateral do endereço")."""

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
