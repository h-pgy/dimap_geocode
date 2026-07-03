from django.contrib.gis.geos import LineString, Point

from services.domain.logradouro_geocod import SegmentoLogradouroFeature

from .numeracao import Paridade, limite_final, limite_inicial


class InterpoladorSegmento:
    """Interpola o ponto do número sobre a linha do segmento (no CRS de interpolação) e o reprojeta
    ao CRS de saída. Peça separada (SRP §10.1), composta pelo AddressGeocoder — par do
    SolverOrientacaoSegmento."""

    def __call__(
        self,
        linha: LineString,
        escolhido: SegmentoLogradouroFeature,
        numero: int,
        paridade: Paridade,
        output_crs: int,
    ) -> Point:
        proporcao = self._definir_proporcao(escolhido, numero, paridade)
        ponto: Point = linha.interpolate_normalized(proporcao)
        ponto.srid = linha.srid       # o CRS de interpolação já vem rotulado na linha
        ponto.transform(output_crs)   # reprojeção centralizada (§7.3)
        return ponto

    def _definir_proporcao(
        self, escolhido: SegmentoLogradouroFeature, numero: int, paridade: Paridade
    ) -> float:
        # proporção normalizada do número no intervalo; sem intervalo (inicial == final) -> meio
        inicial = limite_inicial(escolhido.attributes, paridade)
        final = limite_final(escolhido.attributes, paridade)
        if final == inicial:
            return 0.5
        return (numero - inicial) / (final - inicial)
