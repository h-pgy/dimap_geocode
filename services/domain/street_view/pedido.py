from services.domain.geometry import reprojetar

from .models import PedidoPanorama, PedidoPanoramaInput


class MontarPedidoPanorama:
    def __call__(self, entrada: PedidoPanoramaInput) -> PedidoPanorama:
        alvo = reprojetar(entrada.ponto, entrada.crs_ponto, entrada.crs_street_view)
        return PedidoPanorama(alvo=alvo, raio_m=entrada.raio_m)
