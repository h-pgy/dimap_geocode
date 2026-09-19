import re

import pytest

from services.domain.desenho import Desenho
from services.domain.geometry import PolygonGeometry, reprojetar
from services.domain.lotes_mais_proximos import (
    BuscarLotesDoDesenho,
    CamadaLotes,
    DesenhoGrandeDemaisError,
    DesenhoInvalidoError,
    LotesDoDesenhoInput,
)
from services.integrations.wfs import WfsFeatureCollection, WfsFeatureRequest

CRS_MAPA = 4326
CRS_METRICO = 31983
X0_UTM = 333000.0
Y0_UTM = 7395000.0

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

_PROPS_BASE: dict[str, object] = {
    "cd_identificador": "1001",
    "cd_setor_fiscal": "005",
    "cd_quadra_fiscal": "003",
    "cd_lote": "0048",
    "cd_tipo_lote": "F",
}


def _retangulo_no_mapa(largura: float, altura: float) -> PolygonGeometry:
    anel = [
        [X0_UTM, Y0_UTM],
        [X0_UTM + largura, Y0_UTM],
        [X0_UTM + largura, Y0_UTM + altura],
        [X0_UTM, Y0_UTM + altura],
        [X0_UTM, Y0_UTM],
    ]
    metrico = PolygonGeometry(type="Polygon", coordinates=[anel])
    return reprojetar(metrico, CRS_METRICO, CRS_MAPA)


def _laco_em_oito() -> PolygonGeometry:
    anel = [
        [-46.6560, -23.5620],
        [-46.6550, -23.5610],
        [-46.6550, -23.5620],
        [-46.6560, -23.5610],
        [-46.6560, -23.5620],
    ]
    return PolygonGeometry(type="Polygon", coordinates=[anel])


def _desenho(geometria: PolygonGeometry) -> Desenho:
    return Desenho(id_bancada="7", geometria=geometria)


def _camada(
    *,
    nome: str = "lote_cidadao",
    campo_geometria: str = "ge_poligono",
) -> CamadaLotes:
    return CamadaLotes(
        nome=nome,
        campo_geometria=campo_geometria,
        crs_camada=CRS_METRICO,
        crs_saida=CRS_MAPA,
    )


def _lotes_do_desenho_input(
    geometria: PolygonGeometry,
    *,
    area_maxima_m2: float = 250_000.0,
    camada: CamadaLotes | None = None,
) -> LotesDoDesenhoInput:
    return LotesDoDesenhoInput(
        desenho=_desenho(geometria),
        crs_mapa=CRS_MAPA,
        camada=camada if camada is not None else _camada(),
        area_maxima_m2=area_maxima_m2,
    )


def _feat(id_poligono: str) -> dict[str, object]:
    return {
        "type": "Feature",
        "geometry": _retangulo_no_mapa(10.0, 10.0).model_dump(),
        "properties": {**_PROPS_BASE, "cd_identificador": id_poligono},
    }


def _page(features_raw: list[dict[str, object]]) -> WfsFeatureCollection:
    return WfsFeatureCollection.model_validate(
        {"type": "FeatureCollection", "numberMatched": len(features_raw), "features": features_raw}
    )


# ---------------------------------------------------------------------------
# Consulta: INTERSECTS com o desenho no CRS métrico, saída no CRS do mapa
# ---------------------------------------------------------------------------


def test_intersects_com_desenho_reprojetado() -> None:
    capturado: list[WfsFeatureRequest] = []

    def fetcher_fake(req: WfsFeatureRequest) -> list[WfsFeatureCollection]:
        capturado.append(req)
        return []

    BuscarLotesDoDesenho(fetcher_fake)(_lotes_do_desenho_input(_retangulo_no_mapa(100.0, 100.0)))

    req = capturado[0]
    assert req.srs_name == f"EPSG:{CRS_MAPA}"
    cql = req.cql_filter.to_cql()  # type: ignore[union-attr]
    assert cql.startswith("INTERSECTS(ge_poligono, POLYGON((")
    primeira = re.search(r"POLYGON\(\(\s*([-0-9.]+)\s+([-0-9.]+)", cql)
    assert primeira is not None
    x = float(primeira.group(1))
    y = float(primeira.group(2))
    assert x == pytest.approx(X0_UTM, abs=0.01)
    assert y == pytest.approx(Y0_UTM, abs=0.01)


# ---------------------------------------------------------------------------
# Conferência antes da rede
# ---------------------------------------------------------------------------


def test_desenho_invalido_ou_grande_demais_recusado_sem_consultar() -> None:
    chamadas: list[WfsFeatureRequest] = []

    def fetcher_fake(req: WfsFeatureRequest) -> list[WfsFeatureCollection]:
        chamadas.append(req)
        return []

    buscar = BuscarLotesDoDesenho(fetcher_fake)

    with pytest.raises(DesenhoInvalidoError):
        buscar(_lotes_do_desenho_input(_laco_em_oito()))
    with pytest.raises(DesenhoGrandeDemaisError):
        buscar(_lotes_do_desenho_input(_retangulo_no_mapa(100.0, 100.0), area_maxima_m2=5_000.0))
    assert chamadas == []


# ---------------------------------------------------------------------------
# Resultado: lotes e área do desenho
# ---------------------------------------------------------------------------


def test_lotes_do_desenho_traz_area_e_lotes() -> None:
    pagina = _page([_feat("1001"), _feat("1002")])
    buscar = BuscarLotesDoDesenho(lambda _req: iter([pagina]))

    resultado = buscar(_lotes_do_desenho_input(_retangulo_no_mapa(100.0, 50.0)))

    assert [lote.attributes.id_poligono for lote in resultado.lotes] == ["1001", "1002"]
    assert all(lote.crs == CRS_MAPA for lote in resultado.lotes)
    assert resultado.area_m2 == pytest.approx(5_000.0, rel=1e-3)
    assert resultado.desenho.id_bancada == "7"


# ---------------------------------------------------------------------------
# Integração — WFS GeoSampa real
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIntegracaoGeoSampa:
    """Execute com: pytest -m integration"""

    def _buscar(self) -> BuscarLotesDoDesenho:
        from services.integrations.wfs import WfsConnectionConfig, WfsFetcher

        config = WfsConnectionConfig(
            domain="wfs.geosampa.prefeitura.sp.gov.br",
            endpoint="geoserver/geoportal/wfs",
            namespace="geoportal",
        )
        return BuscarLotesDoDesenho(WfsFetcher(config))

    def test_lotes_do_desenho_no_geosampa(self) -> None:
        # Retângulo de ~40 m na Av. Paulista, 1483 (esquina com a Al. Santos), conferido no GeoSampa.
        anel = [
            [-46.6567, -23.5633],
            [-46.6563, -23.5633],
            [-46.6563, -23.5629],
            [-46.6567, -23.5629],
            [-46.6567, -23.5633],
        ]
        entrada = _lotes_do_desenho_input(PolygonGeometry(type="Polygon", coordinates=[anel]))

        resultado = self._buscar()(entrada)

        ids = {lote.attributes.id_poligono for lote in resultado.lotes}
        assert ids >= {"1967649", "1990340"}
        assert all(lote.crs == CRS_MAPA for lote in resultado.lotes)
