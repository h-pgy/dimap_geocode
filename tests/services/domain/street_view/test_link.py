from urllib.parse import parse_qs, urlsplit

from services.domain.geometry import PointGeometry, reprojetar
from services.domain.street_view import LinkStreetViewInput, MontarLinkStreetView

CRS_GEOGRAFICO = 4326
CRS_METRICO = 31983
LON = -46.6559
LAT = -23.5614
# ~0,5 m em latitude: a folga que "a menos de um metro" permite.
TOLERANCIA_GRAUS = 5e-6

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _ponto() -> PointGeometry:
    return PointGeometry(type="Point", coordinates=[LON, LAT])


def _url_do_link(ponto: PointGeometry, crs_ponto: int) -> str:
    montar_link = MontarLinkStreetView()
    entrada = LinkStreetViewInput(
        ponto=ponto,
        crs_ponto=crs_ponto,
        crs_street_view=CRS_GEOGRAFICO,
    )
    return montar_link(entrada).url


# ---------------------------------------------------------------------------
# O link do panorama
# ---------------------------------------------------------------------------


def test_link_escreve_latitude_antes_da_longitude() -> None:
    url = _url_do_link(_ponto(), CRS_GEOGRAFICO)

    assert url.startswith("https://www.google.com/maps/@?")
    assert "viewpoint=-23.5614%2C-46.6559" in url
    parametros = parse_qs(urlsplit(url).query)
    assert parametros["api"] == ["1"]
    assert parametros["map_action"] == ["pano"]


def test_link_reprojeta_ponto_de_crs_metrico() -> None:
    ponto_metrico = reprojetar(_ponto(), CRS_GEOGRAFICO, CRS_METRICO)

    url = _url_do_link(ponto_metrico, CRS_METRICO)

    viewpoint = parse_qs(urlsplit(url).query)["viewpoint"][0]
    lat_texto, lon_texto = viewpoint.split(",")
    lat = float(lat_texto)
    lon = float(lon_texto)
    assert abs(lat - LAT) < TOLERANCIA_GRAUS
    assert abs(lon - LON) < TOLERANCIA_GRAUS
