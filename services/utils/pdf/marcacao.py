from abc import ABC, abstractmethod
from collections.abc import Iterator

from services.utils.pdf.folha import Folha
from services.utils.pdf.models import Faixa, Margens, Orientacao, Posicao, TamanhoPagina


class Marca(ABC):
    """O que se pinta em toda página, fora do fluxo do corpo."""

    posicao: Posicao
    altura_mm: float
    # `None` é "a faixa inteira", o que toda marca recebia antes de existir grupo horizontal — o
    # default preserva o comportamento de quem já declara a própria largura como atributo de
    # instância (Caveats da SPEC documentos_oficiais/005).
    largura_mm: float | None = None

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
        margem_vertical_mm: float,
        respiro_mm: float,
        orientacao: Orientacao = Orientacao.RETRATO,
    ) -> None:
        self._marcas = marcas
        self.orientacao = orientacao
        self._margem_lateral_mm = margem_lateral_mm
        # A borda que nem as marcas ocupam: impressora nenhuma imprime até o corte do papel, e sem
        # esta reserva o rodapé sai na aresta da folha.
        self._margem_vertical_mm = margem_vertical_mm
        # A distância entre a última marca e a primeira linha do corpo: sem ela o texto encosta.
        self._respiro_mm = respiro_mm

    def margens(self, tamanho: TamanhoPagina) -> Margens:
        # SOMA, não máximo: duas marcas na mesma posição se empilham, não se sobrepõem. É isto que
        # faz acrescentar uma marca não pedir recálculo de margem em lugar nenhum. FUNDO fica de
        # fora da conta por construção: ela não reserva área, o corpo passa por cima dela.
        return Margens(
            esquerda_mm=self._margem_lateral_mm,
            direita_mm=self._margem_lateral_mm,
            superior_mm=self._margem_vertical_mm
            + self._reservado(Posicao.SUPERIOR)
            + self._respiro_mm,
            inferior_mm=self._margem_vertical_mm
            + self._reservado(Posicao.INFERIOR)
            + self._respiro_mm,
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
        topo = self._margem_vertical_mm
        pe = tamanho.altura_mm - self._margem_vertical_mm
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


class MarcasEmpilhadas(Marca):
    """Marcas uma sob a outra dentro de UMA faixa. Declaradas soltas na `Marcacao`, cada uma
    reserva a sua e some a altura de todas; agrupadas, elas viram uma coluna que pode ficar ao lado
    de outra coisa."""

    def __init__(self, marcas: tuple[Marca, ...], posicao: Posicao) -> None:
        self._marcas = marcas
        # A posição é do GRUPO, não de classe: quem agrupa é que sabe se a coluna é do alto ou do pé,
        # e as marcas agrupadas deixam de responder por si na `Marcacao`.
        self.posicao = posicao
        self.altura_mm = sum(marca.altura_mm for marca in marcas)

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        topo = faixa.topo_mm
        for marca in self._marcas:
            marca(self._faixa_da(faixa, topo, marca), folha)
            topo += marca.altura_mm

    def _faixa_da(self, faixa: Faixa, topo_mm: float, marca: Marca) -> Faixa:
        return faixa.model_copy(update={"topo_mm": topo_mm, "altura_mm": marca.altura_mm})


class MarcasLadoALado(Marca):
    """Marcas ombro a ombro dentro de UMA faixa, na ordem declarada, encostadas no topo dela. O
    espelho horizontal de `MarcasEmpilhadas`: soltas na `Marcacao`, cada uma reservaria a sua faixa
    e o pé comeria a página."""

    def __init__(self, marcas: tuple[Marca, ...], posicao: Posicao, respiro_mm: float) -> None:
        if not marcas:
            raise ValueError("Grupo lado a lado precisa de ao menos uma marca.")
        # Duas marcas elásticas não têm repartição definida: quem sobra é UMA, e a recusa acontece
        # na construção do papel timbrado, não na página impressa.
        elasticas = sum(1 for marca in marcas if marca.largura_mm is None)
        if elasticas > 1:
            raise ValueError(
                f"{elasticas} marcas sem largura declarada no mesmo grupo: no máximo uma recebe a sobra."
            )
        self._marcas = marcas
        self._respiro_mm = respiro_mm
        self.posicao = posicao
        # A MAIS ALTA, não a soma: é isso que faz o grupo custar uma faixa em vez de N.
        self.altura_mm = max(marca.altura_mm for marca in marcas)

    def __call__(self, faixa: Faixa, folha: Folha) -> None:
        esquerda = faixa.esquerda_mm
        for marca, largura in self._repartir(faixa):
            marca(self._faixa_da(faixa, esquerda, largura, marca), folha)
            esquerda += largura + self._respiro_mm

    def _repartir(self, faixa: Faixa) -> tuple[tuple[Marca, float], ...]:
        respiros = self._respiro_mm * (len(self._marcas) - 1)
        declarada = sum(marca.largura_mm or 0.0 for marca in self._marcas)
        sobra = faixa.largura_mm - declarada - respiros
        # Recusar aqui, e não deixar passar: largura negativa sairia como marcas sobrepostas, que é
        # um defeito que só aparece no papel e depois de impresso.
        if sobra < 0:
            raise ValueError(
                f"As marcas do grupo pedem {declarada + respiros:.1f} mm numa faixa de "
                f"{faixa.largura_mm:.1f} mm: faltam {-sobra:.1f} mm."
            )
        return tuple(
            (marca, sobra if marca.largura_mm is None else marca.largura_mm)
            for marca in self._marcas
        )

    def _faixa_da(self, faixa: Faixa, esquerda_mm: float, largura_mm: float, marca: Marca) -> Faixa:
        # A altura é a da MARCA, não a do grupo: o que é mais baixo que o vizinho encosta no topo da
        # faixa, e não flutua no meio dela.
        return faixa.model_copy(
            update={
                "esquerda_mm": esquerda_mm,
                "largura_mm": largura_mm,
                "altura_mm": marca.altura_mm,
            }
        )
