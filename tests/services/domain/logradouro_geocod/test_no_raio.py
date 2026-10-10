import pytest

from services.domain.geometry import PointGeometry
from services.domain.logradouro_geocod import SegmentosNoRaio, SegmentosNoRaioInput
from services.integrations.wfs import WfsFeatureCollection, WfsFeatureRequest

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

_PROPS_BASE: dict[str, object] = {
    "cd_identificador": "SEG001",
    "codlog": "156566",
    "cd_tipo_logradouro": "AV",
    "nm_logradouro": "PAULISTA",
}


def _linha_horizontal(y: float) -> dict[str, object]:
    return {"type": "LineString", "coordinates": [[-20.0, y], [20.0, y]]}


def _feat(id_segmento: str, geom: dict[str, object]) -> dict[str, object]:
    props = {**_PROPS_BASE, "cd_identificador": id_segmento}
    return {"type": "Feature", "geometry": geom, "properties": props}


def _page(features_raw: list[dict[str, object]]) -> WfsFeatureCollection:
    return WfsFeatureCollection.model_validate(
        {"type": "FeatureCollection", "numberMatched": len(features_raw), "features": features_raw}
    )


def _entrada(
    *,
    coordinates: list[float],
    crs_ponto: int = 4326,
    raio_m: float = 50.0,
) -> SegmentosNoRaioInput:
    return SegmentosNoRaioInput(
        ponto=PointGeometry(type="Point", coordinates=coordinates),
        crs_ponto=crs_ponto,
        raio_m=raio_m,
        layer_name="segmento_logradouro",
        campo_geometria="ge_linha",
        crs_metrico=31983,
    )


def _segmentos_no_raio(pages: list[WfsFeatureCollection]) -> SegmentosNoRaio:
    return SegmentosNoRaio(lambda _req: iter(pages))


# ---------------------------------------------------------------------------
# Consulta: o raio, no CRS métrico
# ---------------------------------------------------------------------------


def test_segmentos_no_raio_consulta_pelo_raio_no_crs_metrico() -> None:
    capturado: list[WfsFeatureRequest] = []

    def fetcher_duble(req: WfsFeatureRequest) -> list[WfsFeatureCollection]:
        capturado.append(req)
        return []

    buscar_segmentos = SegmentosNoRaio(fetcher_duble)
    buscar_segmentos(_entrada(coordinates=[-46.6559, -23.5614]))

    req = capturado[0]
    assert req.nome_camada == "segmento_logradouro"
    assert req.srs_name == "EPSG:31983"
    cql = req.cql_filter.to_cql()  # type: ignore[union-attr]
    assert cql.startswith("DWITHIN(ge_linha, POINT(3")  # x em UTM 23S: centenas de milhares de metros
    assert cql.endswith(", 50.0, meters)")
    assert " AND " not in cql


# ---------------------------------------------------------------------------
# Medida e ordem
# ---------------------------------------------------------------------------


def test_segmentos_no_raio_saem_do_mais_perto_ao_mais_longe() -> None:
    longe = _feat("LONGE", _linha_horizontal(30.0))
    sobre = _feat("SOBRE", _linha_horizontal(0.0))
    perto = _feat("PERTO", _linha_horizontal(10.0))
    entrada = _entrada(coordinates=[0.0, 0.0], crs_ponto=31983)

    buscar_segmentos = _segmentos_no_raio([_page([longe, sobre]), _page([perto])])
    proximos = buscar_segmentos(entrada)

    assert [p.segmento.attributes.id_segmento for p in proximos] == ["SOBRE", "PERTO", "LONGE"]
    assert [p.distancia_m for p in proximos] == pytest.approx([0.0, 10.0, 30.0])
    assert {p.segmento.crs for p in proximos} == {31983}

    sem_feicoes = _segmentos_no_raio([_page([])])
    assert sem_feicoes(entrada) == ()


# ---------------------------------------------------------------------------
# Integração — WFS GeoSampa real
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIntegracaoGeoSampa:
    """Roda apenas com: uv run pytest -m integration"""

    def test_logradouro_mais_proximo_no_geosampa(self) -> None:
        from services.integrations.wfs import WfsConnectionConfig, WfsFetcher

        config = WfsConnectionConfig(
            domain="wfs.geosampa.prefeitura.sp.gov.br",
            endpoint="geoserver/geoportal/wfs",
            namespace="geoportal",
        )
        # Pista da Av. Paulista em frente ao MASP: na calçada, a passagem sob o museu fica mais perto.
        entrada = _entrada(coordinates=[-46.65636, -23.5615])
        buscar_segmentos = SegmentosNoRaio(WfsFetcher(config))
        proximos = buscar_segmentos(entrada)

        assert proximos[0].segmento.attributes.codlog == "156566"
        assert proximos[0].distancia_m <= 50.0
