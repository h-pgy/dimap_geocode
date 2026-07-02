from collections.abc import Callable

from django.contrib.gis.geos import Point

from services.domain.geometry import PointGeometry
from services.domain.logradouro_geocod import (
    LogradouroGeocodInput,
    SegmentoLogradouroFeature,
)

from .exceptions import NumeracaoNaoEncontradaError, SegmentoNaoEncontradoError
from .interpolacao import InterpoladorSegmento
from .models import AddressGeocodInput, EnderecoAttributes, EnderecoFeature
from .numeracao import Paridade, intervalo_numeracao, limite_final, limite_inicial
from .orientacao import SolverOrientacaoSegmento

# Contrato da dependência injetada: resolve um codlog em seus segmentos (o LogradouroGeocoder
# satisfaz esta assinatura). Tipar pelo Callable — como fazem LogradouroGeocoder/LoteGeocoder
# com seu fetcher — mantém a composição desacoplada e testável por injeção (§3.3, §10.4).
SegmentosDeCodlog = Callable[[LogradouroGeocodInput], list[SegmentoLogradouroFeature]]


class AddressGeocoder:
    def __init__(self, logradouro_geocoder: SegmentosDeCodlog) -> None:
        self._segmentos = logradouro_geocoder                 # composição (§10.4)
        self._corrigir_orientacao = SolverOrientacaoSegmento()
        self._interpolar = InterpoladorSegmento()

    def __call__(self, entrada: AddressGeocodInput) -> EnderecoFeature:
        return self.pipeline(entrada)                         # porta de entrada fina (§10.4)

    def pipeline(self, entrada: AddressGeocodInput) -> EnderecoFeature:
        paridade = self._definir_paridade(entrada.numero)
        segmentos = self._buscar_segmentos(entrada)
        candidatos = self._filtrar_com_numeracao(segmentos, paridade)
        escolhido = self._segmento_do_numero(candidatos, entrada.numero, paridade)
        linha = self._corrigir_orientacao(escolhido, candidatos, paridade)
        ponto = self._interpolar(
            linha, escolhido, entrada.numero, paridade, entrada.output_crs
        )
        return self._montar_feature(ponto, escolhido, entrada)

    def _definir_paridade(self, numero: int) -> Paridade:
        return Paridade.PAR if numero % 2 == 0 else Paridade.IMPAR

    def _buscar_segmentos(
        self, entrada: AddressGeocodInput
    ) -> list[SegmentoLogradouroFeature]:
        # compõe o LogradouroGeocoder pedindo os segmentos JÁ no CRS de interpolação (métrico)
        segmentos = self._segmentos(LogradouroGeocodInput(
            codlog=entrada.codlog,
            layer_name=entrada.layer_name,
            output_crs=entrada.interpolation_crs,
        ))
        if not segmentos:
            raise SegmentoNaoEncontradoError(entrada.codlog)
        return segmentos

    def _filtrar_com_numeracao(
        self, segmentos: list[SegmentoLogradouroFeature], paridade: Paridade
    ) -> list[SegmentoLogradouroFeature]:
        # mantém só os segmentos com numeração para a paridade buscada (ambos os lados não nulos)
        return [
            s for s in segmentos
            if all(v is not None for v in intervalo_numeracao(s.attributes, paridade))
        ]

    def _segmento_do_numero(
        self, candidatos: list[SegmentoLogradouroFeature], numero: int, paridade: Paridade
    ) -> SegmentoLogradouroFeature:
        contem = [
            s for s in candidatos
            if limite_inicial(s.attributes, paridade) <= numero <= limite_final(s.attributes, paridade)
        ]
        if not contem:
            raise NumeracaoNaoEncontradaError(numero)
        return contem[0]   # mais de um: usa o primeiro (§critérios)

    def _montar_feature(
        self, ponto: Point, escolhido: SegmentoLogradouroFeature, entrada: AddressGeocodInput
    ) -> EnderecoFeature:
        a = escolhido.attributes
        return EnderecoFeature(
            geometry=PointGeometry(type="Point", coordinates=[ponto.x, ponto.y]),
            attributes=EnderecoAttributes(
                codlog=a.codlog,
                nome_logradouro=a.nome_logradouro,
                tipo_logradouro=a.tipo_logradouro,
                numero=entrada.numero,
                id_segmento=a.id_segmento,
                titulo=a.titulo,
            ),
            crs=entrada.output_crs,
        )
