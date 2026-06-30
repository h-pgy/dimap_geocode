import pytest
from pydantic import ValidationError

from services.domain.geometry import GeoFeature, LineGeometry, PolygonGeometry
from services.domain.logradouro_geocod import SegmentoLogradouroAttributes

LINESTRING_COORDS = [[0.0, 0.0], [1.0, 1.0]]
MULTILINESTRING_COORDS = [[[0.0, 0.0], [1.0, 1.0]], [[2.0, 2.0], [3.0, 3.0]]]

# ---------------------------------------------------------------------------
# LineGeometry
# ---------------------------------------------------------------------------


def test_linegeometry_aceita_linestring() -> None:
    g = LineGeometry(type="LineString", coordinates=LINESTRING_COORDS)
    assert g.type == "LineString"


def test_linegeometry_aceita_multilinestring() -> None:
    g = LineGeometry(type="MultiLineString", coordinates=MULTILINESTRING_COORDS)
    assert g.type == "MultiLineString"


def test_linegeometry_rejeita_tipo_invalido() -> None:
    with pytest.raises(ValidationError):
        LineGeometry(type="Point", coordinates=[[0.0, 0.0]])  # type: ignore[arg-type]


def test_linegeometry_rejeita_linestring_com_um_ponto() -> None:
    with pytest.raises(ValidationError):
        LineGeometry(type="LineString", coordinates=[[0.0, 0.0]])


def test_linegeometry_rejeita_linestring_vazia() -> None:
    with pytest.raises(ValidationError):
        LineGeometry(type="LineString", coordinates=[])


def test_linegeometry_rejeita_multilinestring_vazia() -> None:
    with pytest.raises(ValidationError):
        LineGeometry(type="MultiLineString", coordinates=[])


def test_linegeometry_rejeita_coordinates_com_pontos_3d() -> None:
    with pytest.raises(ValidationError):
        LineGeometry(type="LineString", coordinates=[[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])


def test_linegeometry_model_validate_de_dict() -> None:
    data = {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}
    g = LineGeometry.model_validate(data)
    assert g.type == "LineString"
    assert len(g.coordinates) == 2


# ---------------------------------------------------------------------------
# GeoFeature — instanciável e genérico
# ---------------------------------------------------------------------------


def _attrs() -> SegmentoLogradouroAttributes:
    return SegmentoLogradouroAttributes(
        id_segmento="SEG001",
        codlog="156566",
        cd_tipo_logradouro="AV",
        nome_logradouro="PAULISTA",
    )


def test_geofeature_instanciavel() -> None:
    feature = GeoFeature[LineGeometry, SegmentoLogradouroAttributes](
        geometry=LineGeometry(type="LineString", coordinates=LINESTRING_COORDS),
        attributes=_attrs(),
        crs=4326,
    )
    assert feature.crs == 4326
    assert feature.geometry.type == "LineString"
    assert feature.attributes.codlog == "156566"


def test_geofeature_rejeita_geometria_invalida() -> None:
    with pytest.raises(ValidationError):
        GeoFeature[LineGeometry, SegmentoLogradouroAttributes](
            geometry=LineGeometry(type="LineString", coordinates=[[0.0, 0.0]]),  # 1 ponto só
            attributes=_attrs(),
            crs=4326,
        )


# ---------------------------------------------------------------------------
# PolygonGeometry
# ---------------------------------------------------------------------------

ANEL_FECHADO = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]
POLYGON_COORDS = [ANEL_FECHADO]
MULTIPOLYGON_COORDS = [
    [ANEL_FECHADO],
    [[[2.0, 2.0], [3.0, 2.0], [3.0, 3.0], [2.0, 3.0], [2.0, 2.0]]],
]


def test_polygongeometry_aceita_polygon() -> None:
    g = PolygonGeometry(type="Polygon", coordinates=POLYGON_COORDS)
    assert g.type == "Polygon"


def test_polygongeometry_aceita_multipolygon() -> None:
    g = PolygonGeometry(type="MultiPolygon", coordinates=MULTIPOLYGON_COORDS)
    assert g.type == "MultiPolygon"


def test_polygongeometry_rejeita_tipo_invalido() -> None:
    with pytest.raises(ValidationError):
        PolygonGeometry(type="Point", coordinates=POLYGON_COORDS)  # type: ignore[arg-type]


def test_polygongeometry_rejeita_anel_aberto() -> None:
    anel_aberto = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]  # primeiro != último
    with pytest.raises(ValidationError):
        PolygonGeometry(type="Polygon", coordinates=[anel_aberto])


def test_polygongeometry_rejeita_polygon_vazio() -> None:
    with pytest.raises(ValidationError):
        PolygonGeometry(type="Polygon", coordinates=[])


def test_polygongeometry_rejeita_multipolygon_vazio() -> None:
    with pytest.raises(ValidationError):
        PolygonGeometry(type="MultiPolygon", coordinates=[])


def test_polygongeometry_rejeita_profundidade_errada_para_multipolygon() -> None:
    with pytest.raises(ValidationError):
        PolygonGeometry(type="MultiPolygon", coordinates=POLYGON_COORDS)


def test_polygongeometry_model_validate_de_dict() -> None:
    data = {"type": "Polygon", "coordinates": POLYGON_COORDS}
    g = PolygonGeometry.model_validate(data)
    assert g.type == "Polygon"
    assert len(g.coordinates) == 1
