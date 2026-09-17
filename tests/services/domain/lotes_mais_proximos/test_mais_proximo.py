import pytest

from services.domain.geometry import PointGeometry
from services.domain.lotes_mais_proximos import (
    CamadaLotes,
    LoteMaisProximo,
    LoteMaisProximoInput,
    NenhumLoteProximoError,
)
from services.integrations.wfs import WfsFeatureCollection, WfsFeatureRequest

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

_PROPS_BASE: dict[str, object] = {
    "cd_identificador": "POL001",
    "cd_setor_fiscal": "005",
    "cd_quadra_fiscal": "003",
    "cd_lote": "0048",
    "cd_tipo_lote": "F",
}


def _quadrado(x0: float, y0: float, lado: float) -> dict[str, object]:
    anel = [
        [x0, y0], [x0 + lado, y0], [x0 + lado, y0 + lado], [x0, y0 + lado], [x0, y0],
    ]
    return {"type": "Polygon", "coordinates": [anel]}


def _feat(props: dict[str, object], geom: dict[str, object]) -> dict[str, object]:
    return {"type": "Feature", "geometry": geom, "properties": props}


def _page(features_raw: list[dict[str, object]]) -> WfsFeatureCollection:
    return WfsFeatureCollection.model_validate(
        {"type": "FeatureCollection", "numberMatched": len(features_raw), "features": features_raw}
    )


def _camada(
    *,
    nome: str = "lote_cidadao",
    campo_geometria: str = "geom",
    crs_camada: int = 31983,
    crs_saida: int = 4326,
) -> CamadaLotes:
    return CamadaLotes(
        nome=nome, campo_geometria=campo_geometria, crs_camada=crs_camada, crs_saida=crs_saida,
    )


def _entrada(
    *,
    coordinates: list[float],
    codlog: str = "123456",
    raio_m: float = 50.0,
    camada: CamadaLotes | None = None,
) -> LoteMaisProximoInput:
    return LoteMaisProximoInput(
        ponto=PointGeometry(type="Point", coordinates=coordinates),
        codlog=codlog,
        raio_m=raio_m,
        camada=camada if camada is not None else _camada(),
    )


def _fetcher(pages: list[WfsFeatureCollection]) -> LoteMaisProximo:
    return LoteMaisProximo(lambda _req: iter(pages))


# ---------------------------------------------------------------------------
# Consulta: CRS da camada e filtro por codlog
# ---------------------------------------------------------------------------


def test_mais_proximo_consulta_no_crs_da_camada_e_filtra_codlog() -> None:
    capturado: list[WfsFeatureRequest] = []

    def fake_fetcher(req: WfsFeatureRequest) -> list[WfsFeatureCollection]:
        capturado.append(req)
        return []

    entrada = _entrada(coordinates=[-46.633, -23.55], codlog="159247")
    with pytest.raises(NenhumLoteProximoError):
        LoteMaisProximo(fake_fetcher)(entrada)

    req = capturado[0]
    assert req.srs_name == "EPSG:31983"
    cql = req.cql_filter.to_cql()  # type: ignore[union-attr]
    assert cql.startswith("DWITHIN(geom,")
    assert ", 50.0, meters)" in cql
    assert "cd_logradouro = '159247'" in cql
    assert cql.count(" AND ") == 1


# ---------------------------------------------------------------------------
# Escolha do lote mais próximo
# ---------------------------------------------------------------------------


def test_mais_proximo_escolhe_menor_distancia() -> None:
    camada = _camada(crs_camada=31983, crs_saida=31983)  # mesmo CRS: distância exata, sem reprojeção
    longe = _feat({**_PROPS_BASE, "cd_identificador": "LONGE"}, _quadrado(50.0, -5.0, 10.0))
    perto = _feat({**_PROPS_BASE, "cd_identificador": "PERTO"}, _quadrado(5.0, -5.0, 10.0))
    geocoder = _fetcher([_page([longe, perto])])

    resultado = geocoder(_entrada(coordinates=[0.0, 0.0], camada=camada))

    assert resultado.lote.attributes.id_poligono == "PERTO"
    assert resultado.distancia_m == pytest.approx(5.0)


def test_sem_lote_no_raio_levanta_erro_proprio() -> None:
    geocoder = _fetcher([_page([])])
    with pytest.raises(NenhumLoteProximoError):
        geocoder(_entrada(coordinates=[0.0, 0.0], camada=_camada(crs_camada=31983, crs_saida=31983)))


def test_lote_devolvido_no_crs_do_mapa() -> None:
    camada = _camada(crs_camada=31983, crs_saida=4326)
    lote = _feat(_PROPS_BASE, _quadrado(333000.0, 7395000.0, 100.0))
    geocoder = _fetcher([_page([lote])])

    # ponto no CRS de saída (4326, lon/lat); o lote acima já está no CRS métrico da camada (31983)
    resultado = geocoder(_entrada(coordinates=[-46.6565, -23.5631], camada=camada))

    assert resultado.lote.crs == 4326
    lon, lat = resultado.lote.geometry.coordinates[0][0]
    assert -47.0 < lon < -46.0
    assert -24.0 < lat < -23.0


# ---------------------------------------------------------------------------
# Integração — WFS GeoSampa real
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIntegracaoGeoSampa:
    """Testa a busca do lote mais próximo contra o WFS real do GeoSampa.
    Execute com: pytest -m integration
    """

    def _build_geocoder(self) -> LoteMaisProximo:
        from services.integrations.wfs import WfsConnectionConfig, WfsFetcher

        config = WfsConnectionConfig(
            domain="wfs.geosampa.prefeitura.sp.gov.br",
            endpoint="geoserver/geoportal/wfs",
            namespace="geoportal",
        )
        return LoteMaisProximo(WfsFetcher(config))

    def test_lote_mais_proximo_no_geosampa(self) -> None:
        # Av. Paulista, 300 (codlog 156566) — ponto plausível na própria via.
        entrada = _entrada(
            coordinates=[-46.6565, -23.5631],
            codlog="156566",
            raio_m=100.0,
            camada=_camada(nome="lote_cidadao", campo_geometria="ge_poligono"),
        )
        resultado = self._build_geocoder()(entrada)
        assert resultado.distancia_m >= 0
        assert resultado.lote.crs == 4326
