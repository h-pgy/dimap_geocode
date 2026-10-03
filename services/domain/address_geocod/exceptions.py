class SegmentoNaoEncontradoError(Exception):
    """Nenhum segmento retornado para o codlog informado."""


class NumeracaoNaoEncontradaError(Exception):
    """Há segmentos, mas nenhum cujo intervalo contém o número buscado."""


class NenhumSegmentoNumeradoNoRaioError(Exception):
    """Nenhum segmento com numeração dentro do raio consultado."""
