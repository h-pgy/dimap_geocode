from abc import ABC, abstractmethod
from typing import ClassVar

from .models import ConsultaGeocodificacao, EnderecoExternoFeature, PoliticaGeocodificacao, Provedor


class ProvedorGeocodificacao(ABC):
    provedor: ClassVar[Provedor]

    def __init__(self, politica: PoliticaGeocodificacao) -> None:
        self.politica = politica

    @abstractmethod
    def __call__(self, consulta: ConsultaGeocodificacao) -> list[EnderecoExternoFeature]:
        """Os resultados na ordem do provedor, no CRS do provedor (declarado em cada feature)."""
