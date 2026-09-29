import pytest

from services.domain.geometry import PointGeometry
from services.domain.lotes_mais_proximos import (
    CamadaLotes,
    LoteMaisProximoDoPonto,
    LoteMaisProximoDoPontoInput,
    NenhumLoteNoRaioError,
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
        [x0, y0],
        [x0 + lado, y0],
        [x0 + lado, y0 + lado],
        [x0, y0 + lado],
        [x0, y0],
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
        nome=nome,
        campo_geometria=campo_geometria,
        crs_camada=crs_camada,
        crs_saida=crs_saida,
    )


def _entrada(
    *,
    coordinates: list[float],
    raio_m: float = 50.0,
    camada: CamadaLotes | None = None,
) -> LoteMaisProximoDoPontoInput:
    return LoteMaisProximoDoPontoInput(
        ponto=PointGeometry(type="Point", coordinates=coordinates),
        raio_m=raio_m,
        camada=camada if camada is not None else _camada(),
    )


def _lote_mais_proximo_do_ponto(pages: list[WfsFeatureCollection]) -> LoteMaisProximoDoPonto:
    return LoteMaisProximoDoPonto(lambda _req: iter(pages))


# ---------------------------------------------------------------------------
# Consulta: só o raio, no CRS da camada
# ---------------------------------------------------------------------------


def test_mais_proximo_do_ponto_consulta_so_pelo_raio() -> None:
    capturado: list[WfsFeatureRequest] = []

    def fetcher_duble(req: WfsFeatureRequest) -> list[WfsFeatureCollection]:
        capturado.append(req)
        return []

    with pytest.raises(NenhumLoteNoRaioError):
        LoteMaisProximoDoPonto(fetcher_duble)(_entrada(coordinates=[-46.633, -23.55]))

    req = capturado[0]
    assert req.srs_name == "EPSG:31983"
    cql = req.cql_filter.to_cql()  # type: ignore[union-attr]
    assert cql.startswith("DWITHIN(geom, POINT(3")  # x em UTM 23S: centenas de milhares de metros
    assert ", 50.0, meters)" in cql
    assert "cd_logradouro" not in cql
    assert " AND " not in cql


# ---------------------------------------------------------------------------
# Escolha do lote
# ---------------------------------------------------------------------------


def test_mais_proximo_do_ponto_escolhe_menor_distancia() -> None:
    camada = _camada(crs_camada=31983, crs_saida=31983)
    longe = _feat({**_PROPS_BASE, "cd_identificador": "LONGE"}, _quadrado(50.0, -5.0, 10.0))
    perto = _feat({**_PROPS_BASE, "cd_identificador": "PERTO"}, _quadrado(5.0, -5.0, 10.0))

    resultado = _lote_mais_proximo_do_ponto([_page([longe, perto])])(
        _entrada(coordinates=[0.0, 0.0], camada=camada)
    )

    assert resultado.lote.attributes.id_poligono == "PERTO"
    assert resultado.distancia_m == pytest.approx(5.0)


def test_mais_proximo_do_ponto_sem_lote_levanta_erro_proprio() -> None:
    camada = _camada(crs_camada=31983, crs_saida=31983)
    with pytest.raises(NenhumLoteNoRaioError):
        _lote_mais_proximo_do_ponto([_page([])])(_entrada(coordinates=[0.0, 0.0], camada=camada))


# ---------------------------------------------------------------------------
# Integração — WFS GeoSampa real
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIntegracaoGeoSampa:
    """Roda apenas com: uv run pytest -m integration"""

    def test_lote_mais_proximo_do_ponto_no_geosampa(self) -> None:
        from services.integrations.wfs import WfsConnectionConfig, WfsFetcher

        config = WfsConnectionConfig(
            domain="wfs.geosampa.prefeitura.sp.gov.br",
            endpoint="geoserver/geoportal/wfs",
            namespace="geoportal",
        )
        # Av. Paulista, 300: ponto na via, cercado de lotes.
        entrada = _entrada(
            coordinates=[-46.6565, -23.5631],
            camada=_camada(nome="lote_cidadao", campo_geometria="ge_poligono"),
        )
        resultado = LoteMaisProximoDoPonto(WfsFetcher(config))(entrada)

        assert resultado.distancia_m <= 50.0
        assert resultado.lote.crs == 4326
