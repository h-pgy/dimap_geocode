from services.domain.geometry.models import (
    GeoFeature,
    GeoJsonProperties,
    PointGeometry,
)
from services.domain.geometry.serializers import to_geojson_feature_collection
from pydantic import BaseModel


class DummyAttributes(BaseModel):
    id: int


def test_to_geojson_feature_collection_omits_none_properties():
    # Arrange
    geom = PointGeometry(type="Point", coordinates=[-46.6333, -23.5505])
    attr = DummyAttributes(id=1)
    feature = GeoFeature[PointGeometry, DummyAttributes](
        geometry=geom, attributes=attr, crs=4326
    )

    def _properties(f: GeoFeature[PointGeometry, DummyAttributes]) -> GeoJsonProperties:
        return GeoJsonProperties(
            popup_html="<p>Test</p>",
            rotulo="Label",
            cor=None,  # This should be omitted in the output
        )

    # Act
    resultado = to_geojson_feature_collection([feature], _properties)

    # Assert
    assert resultado["type"] == "FeatureCollection"
    assert len(resultado["features"]) == 1
    
    props_serializadas = resultado["features"][0]["properties"]
    assert props_serializadas["popup_html"] == "<p>Test</p>"
    assert props_serializadas["rotulo"] == "Label"
    assert "cor" not in props_serializadas


def test_to_geojson_feature_collection_includes_cor_when_present():
    # Arrange
    geom = PointGeometry(type="Point", coordinates=[-46.6333, -23.5505])
    attr = DummyAttributes(id=1)
    feature = GeoFeature[PointGeometry, DummyAttributes](
        geometry=geom, attributes=attr, crs=4326
    )

    def _properties(f: GeoFeature[PointGeometry, DummyAttributes]) -> GeoJsonProperties:
        return GeoJsonProperties(
            popup_html="<p>Test</p>",
            rotulo="Label",
            cor="#ea580c",  # This should be included in the output
        )

    # Act
    resultado = to_geojson_feature_collection([feature], _properties)

    # Assert
    props_serializadas = resultado["features"][0]["properties"]
    assert props_serializadas["cor"] == "#ea580c"
