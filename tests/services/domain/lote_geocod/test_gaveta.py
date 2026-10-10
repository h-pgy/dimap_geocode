"""Testes da gaveta do lote (SPEC localizacao_lote/001): a área medida no polígono diante da área de
terreno declarada no cadastro."""

import pytest

from services.domain.geometry import PolygonGeometry, reprojetar
from services.domain.lote_geocod import (
    DivergenciaArea,
    GavetaLote,
    GavetaLoteInput,
    LoteAttributes,
    LoteFeature,
    MontarGavetaLote,
)

CRS_MAPA = 4326
CRS_METRICO = 31983


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _lote_attributes(area_terreno_m2: float | None = 500.0) -> LoteAttributes:
    return LoteAttributes(
        id_poligono="P1",
        setor="001",
        quadra="002",
        lote="0003",
        tipo_lote="F",
        area_terreno_m2=area_terreno_m2,
    )


def _retangulo_no_mapa(largura: float, altura: float) -> PolygonGeometry:
    x0 = 333000.0
    y0 = 7395000.0
    anel = [[x0, y0], [x0 + largura, y0], [x0 + largura, y0 + altura], [x0, y0 + altura], [x0, y0]]
    metrico = PolygonGeometry(type="Polygon", coordinates=[anel])
    return reprojetar(metrico, CRS_METRICO, CRS_MAPA)


def _gaveta_lote(area_poligono_m2: float, area_terreno_m2: float | None) -> GavetaLote:
    return GavetaLote(
        lote=_lote_attributes(area_terreno_m2),
        area_poligono_m2=area_poligono_m2,
    )


# ---------------------------------------------------------------------------
# Área do polígono
# ---------------------------------------------------------------------------


def test_area_do_poligono_medida_no_crs_metrico() -> None:
    lote = LoteFeature(
        geometry=_retangulo_no_mapa(20.0, 30.0),
        attributes=_lote_attributes(),
        crs=CRS_MAPA,
    )

    gaveta = MontarGavetaLote()(GavetaLoteInput(lote=lote, crs_metrico=CRS_METRICO))

    assert gaveta.area_poligono_m2 == pytest.approx(600.0, abs=0.5)


# ---------------------------------------------------------------------------
# Diferença e divergência de área
# ---------------------------------------------------------------------------


def test_diferenca_de_area_tem_base_no_cadastro_e_sinal() -> None:
    assert _gaveta_lote(525.0, 500.0).diferenca_area_pct == pytest.approx(5.0)
    assert _gaveta_lote(525.0, 625.0).diferenca_area_pct == pytest.approx(-16.0)
    assert _gaveta_lote(525.0, None).diferenca_area_pct is None
    assert _gaveta_lote(525.0, 0.0).diferenca_area_pct is None


@pytest.mark.parametrize(
    ("area_poligono_m2", "esperada"),
    [
        (102.0, DivergenciaArea.TOLERAVEL),
        (102.1, DivergenciaArea.ALERTA),
        (105.0, DivergenciaArea.ALERTA),
        (105.1, DivergenciaArea.ERRO),
        (98.0, DivergenciaArea.TOLERAVEL),
        (97.9, DivergenciaArea.ALERTA),
        (95.0, DivergenciaArea.ALERTA),
        (94.9, DivergenciaArea.ERRO),
    ],
)
def test_divergencia_de_area_nas_bordas(
    area_poligono_m2: float,
    esperada: DivergenciaArea,
) -> None:
    assert _gaveta_lote(area_poligono_m2, 100.0).divergencia_area is esperada
