from urllib.parse import urlencode

from services.domain.geometry import PointGeometry, reprojetar

from .models import LinkStreetView, LinkStreetViewInput

URL_BASE = "https://www.google.com/maps/@"
# ~10 cm: mais que isso é ruído na URL.
CASAS_DECIMAIS = 6


class MontarLinkStreetView:
    def __call__(self, entrada: LinkStreetViewInput) -> LinkStreetView:
        return self.pipeline(entrada)

    def pipeline(self, entrada: LinkStreetViewInput) -> LinkStreetView:
        ponto = reprojetar(entrada.ponto, entrada.crs_ponto, entrada.crs_street_view)
        return LinkStreetView(url=self._montar_url(ponto))

    def _montar_url(self, ponto: PointGeometry) -> str:
        # GeoJSON guarda (lon, lat); o Google lê o viewpoint como "lat,lon".
        lon, lat = ponto.coordinates
        lat_arredondada = round(lat, CASAS_DECIMAIS)
        lon_arredondada = round(lon, CASAS_DECIMAIS)
        parametros = {
            # Sem `api=1` o Google ignora os demais parâmetros.
            "api": "1",
            "map_action": "pano",
            "viewpoint": f"{lat_arredondada},{lon_arredondada}",
        }
        return f"{URL_BASE}?{urlencode(parametros)}"
