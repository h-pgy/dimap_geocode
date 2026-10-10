from collections.abc import Callable

from django.contrib.gis.geos import LineString, Point
from pydantic import BaseModel

from services.domain.geometry import para_geos, reprojetar
from services.domain.logradouro_geocod import (
    LogradouroGeocodInput,
    SegmentoLogradouroFeature,
    SegmentoProximo,
    SegmentosNoRaioInput,
)

from .exceptions import NenhumSegmentoNumeradoNoRaioError
from .geocoder import SegmentosDeCodlog, montar_endereco
from .interpolacao import InterpoladorSegmento
from .lado import lado_do_ponto
from .models import PARIDADE_POR_LADO, EnderecoFeature
from .numeracao import Paridade, limite_final, limite_inicial, tem_numeracao
from .orientacao import SolverOrientacaoSegmento

SegmentosDoPonto = Callable[[SegmentosNoRaioInput], tuple[SegmentoProximo, ...]]


class EnderecoMaisProximoInput(BaseModel):
    consulta: SegmentosNoRaioInput
    output_crs: int


class EnderecoMaisProximo:
    def __init__(
        self,
        segmentos_no_raio: SegmentosDoPonto,
        logradouro_geocoder: SegmentosDeCodlog,
    ) -> None:
        self._segmentos_no_raio = segmentos_no_raio
        self._segmentos = logradouro_geocoder
        self._corrigir_orientacao = SolverOrientacaoSegmento()
        self._interpolar = InterpoladorSegmento()

    def __call__(self, entrada: EnderecoMaisProximoInput) -> EnderecoFeature:
        return self.pipeline(entrada)

    def pipeline(self, entrada: EnderecoMaisProximoInput) -> EnderecoFeature:
        proximos = self._segmentos_no_raio(entrada.consulta)
        escolhido = self._primeiro_numerado(proximos, entrada.consulta.raio_m)
        lados = self._lados_numerados(escolhido)
        # O solver acha o vizinho por uma faixa só; o sentido que ele devolve vale para os dois lados.
        referencia = lados[0]
        vizinhos = self._vizinhos_com_numeracao(escolhido, referencia, entrada.consulta)
        linha = self._corrigir_orientacao(escolhido, vizinhos, referencia)
        ponto = self._ponto_metrico(entrada.consulta)
        paridade = self._paridade_do_ponto(lados, linha, ponto)
        numero = self._numero_do_ponto(linha, escolhido, ponto, paridade)
        # Reinterpola o número arredondado: o ponto do endereço é o que a busca daria para ele.
        ponto_endereco = self._interpolar(linha, escolhido, numero, paridade, entrada.output_crs)
        return montar_endereco(ponto_endereco, escolhido, numero, paridade, entrada.output_crs)

    def _primeiro_numerado(
        self,
        proximos: tuple[SegmentoProximo, ...],
        raio_m: float,
    ) -> SegmentoLogradouroFeature:
        for proximo in proximos:
            if self._lados_numerados(proximo.segmento):
                return proximo.segmento
        raise NenhumSegmentoNumeradoNoRaioError(raio_m)

    def _lados_numerados(self, segmento: SegmentoLogradouroFeature) -> list[Paridade]:
        return [paridade for paridade in Paridade if tem_numeracao(segmento.attributes, paridade)]

    def _vizinhos_com_numeracao(
        self,
        escolhido: SegmentoLogradouroFeature,
        referencia: Paridade,
        consulta: SegmentosNoRaioInput,
    ) -> list[SegmentoLogradouroFeature]:
        # O vizinho que orienta o segmento pode estar fora do raio.
        do_codlog = LogradouroGeocodInput(
            codlog=escolhido.attributes.codlog,
            layer_name=consulta.layer_name,
            output_crs=consulta.crs_metrico,
        )
        segmentos = self._segmentos(do_codlog)
        return [s for s in segmentos if tem_numeracao(s.attributes, referencia)]

    def _ponto_metrico(self, consulta: SegmentosNoRaioInput) -> Point:
        ponto_metrico = reprojetar(consulta.ponto, consulta.crs_ponto, consulta.crs_metrico)
        return para_geos(ponto_metrico, consulta.crs_metrico)  # type: ignore[return-value]

    def _paridade_do_ponto(
        self,
        lados: list[Paridade],
        linha: LineString,
        ponto: Point,
    ) -> Paridade:
        # Pista de avenida: o segmento é de um lado só, e estar mais perto dele já é estar desse lado.
        if len(lados) == 1:
            return lados[0]
        lado = lado_do_ponto(linha, ponto)
        return PARIDADE_POR_LADO[lado]

    def _numero_do_ponto(
        self,
        linha: LineString,
        escolhido: SegmentoLogradouroFeature,
        ponto: Point,
        paridade: Paridade,
    ) -> int:
        inicial = limite_inicial(escolhido.attributes, paridade)
        final = limite_final(escolhido.attributes, paridade)
        fracao = linha.project_normalized(ponto)
        bruto = inicial + fracao * (final - inicial)
        resto = 0 if paridade is Paridade.PAR else 1
        numero = 2 * round((bruto - resto) / 2) + resto
        # A faixa par que começa em 0 não devolve o número 0.
        primeiro = 2 - resto
        piso = max(inicial, primeiro)
        return max(min(numero, final), piso)
