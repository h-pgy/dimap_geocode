import json
import math

from django.contrib.gis.geos import GEOSGeometry, LineString, MultiLineString

from services.domain.logradouro_geocod import SegmentoLogradouroFeature

from .numeracao import Paridade, limite_final, limite_inicial


def linha_geos(feature: SegmentoLogradouroFeature) -> LineString:
    """SegmentoLogradouroFeature -> LineString GEOS, rotulado com o CRS da própria feature
    (`feature.crs`). MultiLineString é fundido (merged) quando contíguo; senão toma-se a parte
    mais longa. Único ponto de conversão coords -> objeto geométrico.

    O SRID é atribuído **depois** de construir a geometria, não passado ao construtor: o
    `GEOSGeometry` assume SRID 4326 por padrão ao desserializar GeoJSON (RFC 7946) e rejeita um
    `srid` explícito que destoe desse default — atribuir depois apenas rotula as coordenadas cruas
    com o CRS em que a feature veio, sem reprojetar."""
    line = feature.geometry
    geom = GEOSGeometry(json.dumps({"type": line.type, "coordinates": line.coordinates}))
    geom.srid = feature.crs
    if isinstance(geom, MultiLineString):
        fundido = geom.merged
        geom = fundido if isinstance(fundido, LineString) else max(geom, key=lambda p: p.length)
    return geom  # type: ignore[return-value]


def _inicio(feature: SegmentoLogradouroFeature, paridade: Paridade) -> int:
    return limite_inicial(feature.attributes, paridade)


def _fim(feature: SegmentoLogradouroFeature, paridade: Paridade) -> int:
    return limite_final(feature.attributes, paridade)


class SolverOrientacaoSegmento:
    """Decide se a linha do segmento precisa ser invertida para casar com o sentido crescente
    da numeração, olhando o segmento adjacente. Composto pelo AddressGeocoder."""

    def __call__(
        self,
        escolhido: SegmentoLogradouroFeature,
        candidatos: list[SegmentoLogradouroFeature],
        paridade: Paridade,
    ) -> LineString:
        linha = linha_geos(escolhido)
        adjacente = self._adjacente(escolhido, candidatos, paridade)
        if adjacente is None:
            # sem vizinho (via de segmento único) não há como inferir orientação;
            # mantém a ordem de coordenadas de origem.
            return linha
        if self._orientacao_correta(escolhido, adjacente, candidatos, paridade, linha):
            return linha
        return LineString(list(linha.coords)[::-1], srid=linha.srid)

    def _is_primeiro(
        self,
        escolhido: SegmentoLogradouroFeature,
        candidatos: list[SegmentoLogradouroFeature],
        paridade: Paridade,
    ) -> bool:
        menor = min(_inicio(c, paridade) for c in candidatos)
        return _inicio(escolhido, paridade) == menor

    def _adjacente(
        self,
        escolhido: SegmentoLogradouroFeature,
        candidatos: list[SegmentoLogradouroFeature],
        paridade: Paridade,
    ) -> SegmentoLogradouroFeature | None:
        if self._is_primeiro(escolhido, candidatos, paridade):
            # posteriores: começam onde este termina; o mais próximo é o adjacente
            final = _fim(escolhido, paridade)
            posteriores = [c for c in candidatos if _inicio(c, paridade) >= final]
            return min(posteriores, key=lambda c: _inicio(c, paridade)) if posteriores else None
        inicial = _inicio(escolhido, paridade)
        anteriores = [c for c in candidatos if _fim(c, paridade) <= inicial]
        return max(anteriores, key=lambda c: _fim(c, paridade)) if anteriores else None

    def _orientacao_correta(
        self,
        escolhido: SegmentoLogradouroFeature,
        adjacente: SegmentoLogradouroFeature,
        candidatos: list[SegmentoLogradouroFeature],
        paridade: Paridade,
        linha: LineString,
    ) -> bool:
        # Qual das DUAS extremidades de `escolhido` encosta no segmento adjacente decide a
        # orientação. Compara-se cada ponta contra o adjacente (via a extremidade mais próxima
        # dele — robusto à orientação do próprio adjacente).
        outra = linha_geos(adjacente)
        dist_inicio = self._dist_ate(linha.coords[0], outra)
        dist_fim = self._dist_ate(linha.coords[-1], outra)
        if self._is_primeiro(escolhido, candidatos, paridade):
            # adjacente é o POSTERIOR (numeração maior): a ponta de MAIOR numeração de
            # `escolhido` (coords[-1]) deve encostar nele.
            return dist_fim <= dist_inicio
        # adjacente é o ANTERIOR (numeração menor): a ponta de MENOR numeração de
        # `escolhido` (coords[0]) deve encostar nele.
        return dist_inicio <= dist_fim

    def _dist_ate(self, ponto: tuple[float, ...], outra: LineString) -> float:
        # distância do ponto à extremidade mais próxima do segmento adjacente
        return min(math.dist(ponto, outra.coords[0]), math.dist(ponto, outra.coords[-1]))
