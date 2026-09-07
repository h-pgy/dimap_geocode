from abc import ABC, abstractmethod
from collections.abc import Iterator

from services.utils.pdf.folha import Folha
from services.utils.pdf.models import Faixa, Margens, Orientacao, Posicao, TamanhoPagina


class Marca(ABC):
    """O que se pinta em toda página, fora do fluxo do corpo."""

    posicao: Posicao
    altura_mm: float

    @abstractmethod
    def __call__(self, faixa: Faixa, folha: Folha) -> None: ...


class Marcacao:
    """Callable em duas camadas: o fundo vai ANTES do corpo, as bordas DEPOIS. Marca nova entra na
    tupla e em lugar nenhum mais — nem nas margens, que são derivadas."""

    orientacao: Orientacao

    def __init__(
        self,
        marcas: tuple[Marca, ...],
        margem_lateral_mm: float,
        respiro_mm: float,
        orientacao: Orientacao = Orientacao.RETRATO,
    ) -> None:
        self._marcas = marcas
        self.orientacao = orientacao
        self._margem_lateral_mm = margem_lateral_mm
        # A distância entre a última marca e a primeira linha do corpo: sem ela o texto encosta.
        self._respiro_mm = respiro_mm

    def margens(self, tamanho: TamanhoPagina) -> Margens:
        # SOMA, não máximo: duas marcas na mesma posição se empilham, não se sobrepõem. É isto que
        # faz acrescentar uma marca não pedir recálculo de margem em lugar nenhum. FUNDO fica de
        # fora da conta por construção: ela não reserva área, o corpo passa por cima dela.
        return Margens(
            esquerda_mm=self._margem_lateral_mm,
            direita_mm=self._margem_lateral_mm,
            superior_mm=self._reservado(Posicao.SUPERIOR) + self._respiro_mm,
            inferior_mm=self._reservado(Posicao.INFERIOR) + self._respiro_mm,
        )

    def pintar_fundo(self, folha: Folha) -> None:
        # A faixa da marca de fundo é a folha inteira: ela não disputa área com ninguém.
        inteira = Faixa(
            esquerda_mm=0.0,
            topo_mm=0.0,
            largura_mm=folha.tamanho.largura_mm,
            altura_mm=folha.tamanho.altura_mm,
        )
        for marca in self._marcas:
            if marca.posicao is Posicao.FUNDO:
                marca(inteira, folha)

    def pintar_bordas(self, folha: Folha) -> None:
        for marca, faixa in self._faixas(folha.tamanho):
            marca(faixa, folha)

    def _faixas(self, tamanho: TamanhoPagina) -> Iterator[tuple[Marca, Faixa]]:
        # As de cima descem do topo na ordem declarada; as de baixo sobem do pé. A marca recebe a
        # faixa pronta e nunca calcula posição absoluta — é o que a mantém trocável e reordenável.
        topo = 0.0
        pe = tamanho.altura_mm
        largura = tamanho.largura_mm - 2 * self._margem_lateral_mm
        for marca in self._marcas:
            if marca.posicao is Posicao.SUPERIOR:
                yield marca, Faixa(
                    esquerda_mm=self._margem_lateral_mm,
                    topo_mm=topo,
                    largura_mm=largura,
                    altura_mm=marca.altura_mm,
                )
                topo += marca.altura_mm
            elif marca.posicao is Posicao.INFERIOR:
                pe -= marca.altura_mm
                yield marca, Faixa(
                    esquerda_mm=self._margem_lateral_mm,
                    topo_mm=pe,
                    largura_mm=largura,
                    altura_mm=marca.altura_mm,
                )

    def _reservado(self, posicao: Posicao) -> float:
        return sum(marca.altura_mm for marca in self._marcas if marca.posicao is posicao)
