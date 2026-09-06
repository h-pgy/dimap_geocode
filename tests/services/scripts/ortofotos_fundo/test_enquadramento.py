"""Testes de services/scripts/ortofotos_fundo/enquadramento.py (SPEC design/010): a bbox que
enquadra cada ortofoto de fundo, centrada no ponto e reprojetada para o CRS métrico de recorte.
"""

import pytest
from django.contrib.gis.geos import Point

from config.pontos_fundo import PontoFundo
from services.integrations.wms import WmsConnectionConfig
from services.scripts.ortofotos_fundo.contrato import OrtofotoConfig
from services.scripts.ortofotos_fundo.enquadramento import enquadrar

CRS_ENTRADA = 4326
CRS_SAIDA = 31983


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _ponto(**overrides: object) -> PontoFundo:
    defaults: dict[str, object] = {
        "descricao": "Praça da Sé — Centro",
        "lat": -23.5505,
        "lng": -46.6333,
    }
    defaults.update(overrides)
    return PontoFundo(**defaults)


def _config(**overrides: object) -> OrtofotoConfig:
    defaults: dict[str, object] = {
        "pontos": {"se": _ponto()},
        "conexao": WmsConnectionConfig(
            vector_url="https://wms.test/ows",
            raster_url="https://wms.test/raster",
        ),
        "destino": "/tmp/ortofotos-fundo-inexistente",
        "camada": "geoportal:ORTO_RGB_2020",
        "metros_por_pixel": 4.4,
        "largura_px": 2000,
        "altura_px": 1250,
        "crs_entrada": CRS_ENTRADA,
        "crs_saida": CRS_SAIDA,
    }
    defaults.update(overrides)
    return OrtofotoConfig(**defaults)


# ---------------------------------------------------------------------------
# Enquadramento
# ---------------------------------------------------------------------------


def test_enquadramento_centra_no_ponto() -> None:
    ponto = _ponto()
    config = _config()

    bbox = enquadrar(ponto, config)

    centro_esperado = Point(ponto.lng, ponto.lat, srid=config.crs_entrada)
    centro_esperado.transform(config.crs_saida)
    meia_largura = config.largura_px / 2 * config.metros_por_pixel
    meia_altura = config.altura_px / 2 * config.metros_por_pixel

    assert bbox.crs == f"EPSG:{config.crs_saida}"
    assert bbox.minx == pytest.approx(centro_esperado.x - meia_largura)
    assert bbox.maxx == pytest.approx(centro_esperado.x + meia_largura)
    assert bbox.miny == pytest.approx(centro_esperado.y - meia_altura)
    assert bbox.maxy == pytest.approx(centro_esperado.y + meia_altura)
    assert (bbox.maxx - bbox.minx) == pytest.approx(config.largura_px * config.metros_por_pixel)
