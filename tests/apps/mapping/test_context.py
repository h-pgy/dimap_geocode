"""Testes unitários de apps/mapping/context.py."""

from django.conf import settings

from apps.mapping.context import (
    contexto_aviso,
    contexto_mapa,
    contexto_mapa_base,
)
from apps.mapping.models import CamadaBaseItem


# ---------------------------------------------------------------------------
# contexto_mapa_base
# ---------------------------------------------------------------------------


def test_contexto_mapa_base_estrutura() -> None:
    contexto = contexto_mapa_base()
    assert "wms" in contexto
    assert "config" in contexto
    assert contexto["config"]["centro"] == settings.MAP_CENTRO_DEFAULT
    assert contexto["config"]["zoom"] == settings.MAP_ZOOM_DEFAULT
    assert contexto["wms"]["url"] == settings.WMS_URL
    assert contexto["wms"]["version"] == settings.WMS_VERSION


def test_contexto_mapa_base_valida_camadas_como_camada_base_item() -> None:
    contexto = contexto_mapa_base()
    bases = contexto["wms"]["bases"]
    itens = [CamadaBaseItem(**b) for b in bases]
    assert len(itens) >= 2
    assert itens[0].nome == "Ortofoto"
    assert itens[0].glifo == "glifo-satelite"
    assert itens[1].nome == "Mapa base"
    assert itens[1].glifo == "glifo-mapa-base"


# ---------------------------------------------------------------------------
# contexto_mapa e contexto_aviso
# ---------------------------------------------------------------------------


def test_contexto_mapa() -> None:
    geom = {"type": "Point", "coordinates": [-46.63, -23.55]}
    resultado = contexto_mapa(geom, "#48CAE4")
    assert resultado == {"payload": {"geometria": geom, "cor": "#48CAE4"}}


def test_contexto_aviso() -> None:
    resultado = contexto_aviso("Endereço não localizado.")
    assert resultado == {"mensagem": "Endereço não localizado."}
