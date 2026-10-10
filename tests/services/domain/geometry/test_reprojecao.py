import pytest

from services.domain.geometry import PointGeometry, PolygonGeometry
from services.domain.geometry.reprojecao import reprojetar

# ---------------------------------------------------------------------------
# reprojetar — origem != 4326 não pode levantar (SPEC localizacao_lote/002)
# ---------------------------------------------------------------------------
# GEOSGeometry lê GeoJSON como SRID 4326 por padrão (RFC 7946); passar `srid=origem` direto no
# construtor faz a lib rejeitar quando origem != 4326 ("Input geometry already has SRID: 4326").
# É exatamente o caso de uso central desta SPEC (reprojetar o lote de volta de 31983 -> 4326).


def test_reprojetar_de_crs_metrico_para_4326_nao_levanta() -> None:
    ponto = PointGeometry(type="Point", coordinates=[333000.0, 7395000.0])
    resultado = reprojetar(ponto, 31983, 4326)
    lon, lat = resultado.coordinates
    assert -47.0 < lon < -46.0
    assert -24.0 < lat < -23.0


def test_reprojetar_poligono_ida_e_volta_preserva_coordenadas() -> None:
    poligono = PolygonGeometry(
        type="Polygon",
        coordinates=[[
            [333000.0, 7395000.0],
            [333100.0, 7395000.0],
            [333100.0, 7395100.0],
            [333000.0, 7395100.0],
            [333000.0, 7395000.0],
        ]],
    )
    ida = reprojetar(poligono, 31983, 4326)
    volta = reprojetar(ida, 4326, 31983)
    for (x0, y0), (x1, y1) in zip(poligono.coordinates[0], volta.coordinates[0]):
        assert x1 == pytest.approx(x0, abs=0.5)
        assert y1 == pytest.approx(y0, abs=0.5)
