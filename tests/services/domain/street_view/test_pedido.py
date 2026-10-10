from services.domain.geometry import PointGeometry, reprojetar
from services.domain.street_view import MontarPedidoPanorama, PedidoPanoramaInput

CRS_GEOGRAFICO = 4326
CRS_METRICO = 31983
LON = -46.6559
LAT = -23.5614
RAIO_M = 35.0
# ~0,5 m em latitude: a folga que "a menos de um metro" permite.
TOLERANCIA_GRAUS = 5e-6

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _ponto() -> PointGeometry:
    return PointGeometry(type="Point", coordinates=[LON, LAT])


# ---------------------------------------------------------------------------
# O pedido do panorama
# ---------------------------------------------------------------------------


def test_pedido_reprojeta_alvo_de_crs_metrico() -> None:
    ponto_metrico = reprojetar(_ponto(), CRS_GEOGRAFICO, CRS_METRICO)
    entrada = PedidoPanoramaInput(
        ponto=ponto_metrico,
        crs_ponto=CRS_METRICO,
        crs_street_view=CRS_GEOGRAFICO,
        raio_m=RAIO_M,
    )
    montar_pedido = MontarPedidoPanorama()

    pedido = montar_pedido(entrada)

    lon, lat = pedido.alvo.coordinates
    assert abs(lat - LAT) < TOLERANCIA_GRAUS
    assert abs(lon - LON) < TOLERANCIA_GRAUS
    assert pedido.raio_m == RAIO_M
